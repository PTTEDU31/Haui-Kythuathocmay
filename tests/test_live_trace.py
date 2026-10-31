"""Exercise observation against real handlers and a real streaming HTTP connection."""
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import json
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import main
from app.tracing import snapshot

HTTPClient = httpx.Client
QUESTION = 'Quy định học phí năm học 2026–2027 ở đâu?'


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv('STUDENT_TRACE', '1')
    monkeypatch.setattr(main, 'rates', defaultdict(deque))


def events(client, question=QUESTION, use_ai=False):
    response = client.post('/api/chat/trace', json={'question': question, 'use_ai': use_ai})
    assert response.status_code == 200, response.text
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def starts(trace):
    return [event for event in trace if event['event'] == 'start']


def test_trace_is_opt_in_and_normal_chat_keeps_its_contract(client, monkeypatch):
    monkeypatch.delenv('STUDENT_TRACE', raising=False)
    assert client.get('/architecture/live').status_code == 404
    assert client.get('/architecture/assets/live.js').status_code == 404
    assert client.post('/api/chat/trace', json={'question': 'Xin chào'}).status_code == 404
    response = client.post('/api/chat', json={'question': 'Xin chào', 'use_ai': False})
    assert response.status_code == 200 and response.json()['status'] == 'greeting'
    assert 'span_id' not in response.json()


def test_trace_requires_own_visitor_session_and_retains_request_guards(client, enabled):
    client.cookies.clear()
    assert client.post('/api/chat/trace', json={'question': QUESTION}).status_code == 401
    client.get('/api/bootstrap')
    assert client.post('/api/chat/trace', json={'question': QUESTION}, headers={'Origin': 'https://evil.example'}).status_code == 403
    for question in ('', '   ', 'x' * 1501):
        assert client.post('/api/chat/trace', json={'question': question}).status_code == 422
    assert client.get('/architecture/assets/README.md').status_code == 404
    assert client.get('/architecture/assets/live.js').status_code == 200
    page = client.get('/architecture/live')
    assert page.status_code == 200 and "script-src 'self'" in page.headers['Content-Security-Policy']


def test_trace_uses_real_results_sources_scores_and_committed_history(client, enabled):
    client.cookies.clear()
    client.get('/api/bootstrap')
    trace = events(client)
    calls = starts(trace)
    functions = [call['function'] for call in calls]
    assert 'Engine.classify()' in functions
    assert functions.count('Engine.search()') == 2
    assert 'evidence_matches()' in functions
    assert 'Engine.generate()' not in functions
    result = next(e['result'] for e in trace if e['event'] == 'result')
    expected = main.ENGINE.route(QUESTION)
    for key in ('answer', 'status', 'sources', 'classification', 'retrieval_score', 'routing'):
        assert result[key] == expected[key]
    history = client.get('/api/history').json()
    assert [m['role'] for m in history] == ['user', 'assistant']
    assert history[-1]['result'] == result
    assert trace[-1]['event'] == 'done'
    end = {e['span_id']: e for e in trace if e['event'] == 'end'}
    for call in calls:
        assert call['span_id'] in end
        assert call['source']['path'] in ('app/main.py', 'app/engine.py')
        assert call['source']['line'] > 0
        assert end[call['span_id']]['duration_ms'] >= 0
        if call['parent_id']:
            assert any(parent['span_id'] == call['parent_id'] for parent in calls)
    measured = [e['elapsed_ms'] for e in trace if 'elapsed_ms' in e]
    assert measured == sorted(measured)


@pytest.mark.parametrize('question,status', [('Xin chào', 'greeting'),
    ('Dự đoán giá cổ phiếu giúp em', 'out_of_scope'),
    ('Học phí và học bổng có gì mới?', 'clarify')])
def test_early_returns_do_not_invent_unexecuted_steps(client, enabled, question, status):
    client.cookies.clear();client.get('/api/bootstrap')
    trace = events(client, question)
    assert next(e['result']['status'] for e in trace if e['event'] == 'result') == status
    functions = {e['function'] for e in starts(trace)}
    assert 'Engine.route()' in functions
    assert not functions & {'Engine.search()', 'Engine.classify()', 'httpx.Client.post()'}


def test_stream_errors_are_terminal_and_do_not_write_history(client, enabled, monkeypatch):
    client.cookies.clear();client.get('/api/bootstrap')
    def deny(*args, **kwargs):
        raise HTTPException(429, 'rate limited')
    monkeypatch.setattr(main, 'limit', deny)
    trace = events(client, 'Xin chào')
    assert any(e['event'] == 'request_error' and e['status_code'] == 429 for e in trace)
    assert trace[-1]['event'] == 'done'
    assert client.get('/api/history').json() == []


@pytest.fixture
def live_server(enabled):
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(main.app, log_level='error', access_log=False))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert thread.is_alive() and time.monotonic() < deadline
        time.sleep(.01)
    try:
        yield f'http://127.0.0.1:{listener.getsockname()[1]}'
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        assert not thread.is_alive()


def test_provider_start_is_streamed_before_provider_finishes(live_server, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    secret = 'runtime-trace-secret-must-never-leak'
    answer = 'Bạn hãy mở văn bản chính thức và đối chiếu đúng chương trình học. Mình chưa có dữ liệu để tính học phí cá nhân của bạn.'
    class Provider:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            entered.set()
            assert release.wait(8)
            return httpx.Response(200, request=httpx.Request('POST', 'http://provider'),
                                  json={'message': {'content': json.dumps({'answer': answer, 'supported': True})}})
    monkeypatch.setattr(main, 'read_settings', lambda: {'enabled': True, 'provider': 'ollama', 'model': 'test', 'api_key': secret})
    monkeypatch.setattr('app.engine.httpx.Client', lambda *a, **k: Provider())
    observed = []
    try:
        with HTTPClient(base_url=live_server, timeout=10) as client:
            client.get('/api/bootstrap')
            with client.stream('POST', '/api/chat/trace', json={'question': QUESTION, 'use_ai': True}) as response:
                assert response.headers['x-accel-buffering'] == 'no'
                for line in response.iter_lines():
                    event = json.loads(line);observed.append(event)
                    if event.get('function') == 'httpx.Client.post()':
                        assert event['event'] == 'start'
                        assert entered.wait(2) and not release.is_set()
                        assert not any(e['event'] == 'result' for e in observed)
                        assert client.get('/api/health').status_code == 200
                        release.set()
            assert release.is_set(), 'Provider start was buffered until completion'
            result = next(e['result'] for e in observed if e['event'] == 'result')
            assert result['generation']['used'] is True and result['answer'] == answer
            assert secret not in json.dumps(observed)
    finally:
        release.set()


def test_concurrent_streams_do_not_mix_sessions(live_server):
    questions = ('Xin chào', 'Dự đoán giá cổ phiếu giúp em')
    def run(question):
        with HTTPClient(base_url=live_server, timeout=10) as client:
            client.get('/api/bootstrap')
            trace = events(client, question)
            return trace, client.get('/api/history').json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, questions))
    for index, (trace, history) in enumerate(results):
        chat = next(c for c in starts(trace) if c['function'] == 'chat()')
        assert chat['input']['body']['question'] == questions[index]
        assert history[0]['content'] == questions[index] and len(history) == 2
        assert questions[1-index] not in json.dumps([e.get('input') for e in trace], ensure_ascii=False)
    assert results[0][0][0]['trace_id'] != results[1][0][0]['trace_id']


def test_bounded_preview_redacts_credentials_and_marks_omissions():
    value = snapshot({'api_key': 'secret', 'nested': {'Authorization': 'Bearer secret'}, 'rows': list(range(20)), 'text': 'x' * 12001})
    assert 'secret' not in json.dumps(value)
    assert value['rows'][-1] == {'_omitted_items': 12}
    assert value['text'].endswith('[rút gọn]')


def test_trace_provider_failure_keeps_the_real_faq_fallback(client, enabled, monkeypatch):
    class Unavailable:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            raise httpx.ConnectError('private provider URL must not be exposed')
    monkeypatch.setattr(main, 'read_settings', lambda: {'enabled': True, 'provider': 'ollama', 'model': 'test'})
    monkeypatch.setattr('app.engine.httpx.Client', lambda *a, **k: Unavailable())
    client.cookies.clear();client.get('/api/bootstrap')
    trace = events(client, use_ai=True)
    result = next(e['result'] for e in trace if e['event'] == 'result')
    assert result['generation']['reason'] == 'provider_unavailable'
    assert result['answer'] == main.ENGINE.route(QUESTION)['answer']
    provider = next(e for e in starts(trace) if e['node'] == 'llm')
    assert any(e['event'] == 'error' and e['span_id'] == provider['span_id'] for e in trace)
    assert 'private provider URL' not in json.dumps(trace)
    assert not main.ENGINE.generator_lock.locked()


def test_simultaneous_trace_limit_does_not_block_normal_health(live_server, monkeypatch):
    all_entered = threading.Barrier(5)
    release = threading.Event()
    route = main.ENGINE.route
    def blocked(*args, **kwargs):
        all_entered.wait(timeout=8)
        assert release.wait(8)
        return route(*args, **kwargs)
    monkeypatch.setattr(main.ENGINE, 'route', blocked)
    def run(index):
        with HTTPClient(base_url=live_server, timeout=12) as client:
            client.get('/api/bootstrap')
            return events(client, 'Xin chào')
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run, index) for index in range(4)]
        try:
            all_entered.wait(timeout=8)
            with HTTPClient(base_url=live_server, timeout=10) as client:
                client.get('/api/bootstrap')
                assert client.post('/api/chat/trace', json={'question': 'Xin chào'}).status_code == 429
                assert client.get('/api/health').status_code == 200
        finally:
            release.set()
        assert all(future.result()[-1]['event'] == 'done' for future in futures)


def test_disconnect_stops_observation_but_handler_finishes_transaction(live_server, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    route = main.ENGINE.route
    def blocked(*args, **kwargs):
        entered.set()
        assert release.wait(8)
        return route(*args, **kwargs)
    monkeypatch.setattr(main.ENGINE, 'route', blocked)
    try:
        with HTTPClient(base_url=live_server, timeout=10) as client:
            client.get('/api/bootstrap')
            with client.stream('POST', '/api/chat/trace', json={'question': 'Xin chào', 'use_ai': False}) as response:
                for line in response.iter_lines():
                    if json.loads(line)['event'] == 'start':
                        assert entered.wait(2)
                        break
            release.set()
            deadline = time.monotonic() + 5
            while True:
                history = client.get('/api/history').json()
                if len(history) == 2:
                    break
                assert time.monotonic() < deadline
                time.sleep(.01)
            assert history[-1]['result']['status'] == 'greeting'
    finally:
        release.set()


def read_observed_trace(lines):
    trace = []
    for line in lines:
        if not line:
            continue
        event = json.loads(line)
        if event['event'] == 'heartbeat':
            continue
        trace.append(event)
        if event['event'] == 'done':
            return trace
    pytest.fail('Observer ended before a real chat completed')


def test_web_observer_requires_enabled_flag_and_own_valid_cookie(client, enabled, monkeypatch):
    client.cookies.clear()
    assert client.get('/api/chat/trace/events').status_code == 401
    client.cookies.set('haui_visitor', 'not-a-registered-session')
    assert client.get('/api/chat/trace/events').status_code == 401
    client.cookies.clear()
    monkeypatch.delenv('STUDENT_TRACE')
    assert client.get('/api/chat/trace/events').status_code == 404
    assert client.get('/api/bootstrap').json()['trace_enabled'] is False
    assert client.post('/api/chat', json={'question': 'Xin chào', 'use_ai': False}).status_code == 200


def test_normal_chat_without_observer_never_starts_recorder(client, enabled, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Ordinary chat with no observer must not start recording')
    monkeypatch.setattr('app.live_trace.record_call', forbidden)
    client.cookies.clear()
    response = client.post('/api/chat', json={'question': 'Xin chào', 'use_ai': False})
    assert response.status_code == 200 and response.json()['status'] == 'greeting'
    assert client.cookies.get('haui_visitor')


def test_web_chat_streams_before_provider_completes_and_matches_json(live_server, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    answer = 'Bạn hãy mở văn bản chính thức và đối chiếu đúng chương trình học. Mình chưa có dữ liệu để tính học phí cá nhân của bạn.'
    class Provider:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            entered.set()
            assert release.wait(8)
            return httpx.Response(200, request=httpx.Request('POST', 'http://provider'),
                                  json={'message': {'content': json.dumps({'answer': answer, 'supported': True})}})
    monkeypatch.setattr(main, 'read_settings', lambda: {'enabled': True, 'provider': 'ollama', 'model': 'test'})
    monkeypatch.setattr('app.engine.httpx.Client', lambda *a, **k: Provider())
    try:
        with HTTPClient(base_url=live_server, timeout=10) as client, ThreadPoolExecutor(max_workers=1) as pool:
            assert client.get('/api/bootstrap').json()['trace_enabled'] is True
            with client.stream('GET', '/api/chat/trace/events') as observer:
                assert observer.status_code == 200 and observer.headers['x-accel-buffering'] == 'no'
                lines = observer.iter_lines()
                assert json.loads(next(lines)) == {'event': 'observer_ready'}
                future = pool.submit(client.post, '/api/chat', json={'question': QUESTION, 'use_ai': True})
                trace = []
                for line in lines:
                    event = json.loads(line);trace.append(event)
                    if event.get('function') == 'httpx.Client.post()':
                        assert entered.wait(2) and not future.done() and not release.is_set()
                        assert client.get('/api/health').status_code == 200
                        release.set()
                    if event['event'] == 'done':
                        break
                response = future.result(timeout=5)
                assert response.status_code == 200
                result = next(e['result'] for e in trace if e['event'] == 'result')
                assert response.json() == result
                assert result['generation']['used'] and result['answer'] == answer
                assert len(client.get('/api/history').json()) == 2
                assert len({e['trace_id'] for e in trace}) == 1
                assert trace[0]['origin'] == 'web-chat' and trace[-1]['event'] == 'done'
                assert next(e for e in starts(trace) if e['function'] == 'chat()')['input']['body']['question'] == QUESTION
    finally:
        release.set()


def test_web_observer_isolates_sessions_and_supports_repeated_questions(live_server):
    with HTTPClient(base_url=live_server, timeout=5) as own, HTTPClient(base_url=live_server, timeout=5) as other:
        own.get('/api/bootstrap');other.get('/api/bootstrap')
        with own.stream('GET', '/api/chat/trace/events') as observer:
            lines = observer.iter_lines();assert json.loads(next(lines))['event'] == 'observer_ready'
            assert other.post('/api/chat', json={'question': 'Dự đoán giá cổ phiếu giúp em', 'use_ai': False}).status_code == 200
            traces = []
            for question in ('Xin chào', QUESTION):
                response = own.post('/api/chat', json={'question': question, 'use_ai': False})
                trace = read_observed_trace(lines);traces.append(trace)
                assert trace[0]['question'] == question
                assert next(e['result'] for e in trace if e['event'] == 'result') == response.json()
                assert 'Dự đoán giá cổ phiếu giúp em' not in json.dumps(trace, ensure_ascii=False)
            assert traces[0][0]['trace_id'] != traces[1][0]['trace_id']
            assert len(own.get('/api/history').json()) == 4
            assert len(other.get('/api/history').json()) == 2


def test_web_observer_fanout_limit_cleanup_and_no_replay(live_server):
    from contextlib import ExitStack
    from app.live_trace import _observers, _observer_lock
    with HTTPClient(base_url=live_server, timeout=5) as client:
        client.get('/api/bootstrap')
        client.post('/api/chat', json={'question': QUESTION, 'use_ai': False})
        sid = main.digest(client.cookies.get('haui_visitor'))
        with ExitStack() as stack:
            streams = [stack.enter_context(client.stream('GET', '/api/chat/trace/events')) for _ in range(4)]
            readers = [s.iter_lines() for s in streams]
            for lines in readers:
                assert json.loads(next(lines))['event'] == 'observer_ready'
            assert client.get('/api/chat/trace/events').status_code == 429
            response = client.post('/api/chat', json={'question': 'Xin chào', 'use_ai': False})
            traces = [read_observed_trace(lines) for lines in readers]
            assert all(t[0]['question'] == 'Xin chào' for t in traces), 'Old questions must not be replayed'
            assert len({t[0]['trace_id'] for t in traces}) == 1
            assert all(next(e['result'] for e in t if e['event'] == 'result') == response.json() for t in traces)
        deadline = time.monotonic() + 3
        while True:
            with _observer_lock:
                active = sid in _observers
            if not active: break
            assert time.monotonic() < deadline
            time.sleep(.01)


def test_web_chat_keeps_real_http_error_and_observer_gets_terminal_event(live_server, monkeypatch):
    def deny(*args, **kwargs): raise HTTPException(429, 'rate limited')
    monkeypatch.setattr(main, 'limit', deny)
    with HTTPClient(base_url=live_server, timeout=5) as client:
        client.get('/api/bootstrap')
        with client.stream('GET', '/api/chat/trace/events') as observer:
            lines=observer.iter_lines();assert json.loads(next(lines))['event']=='observer_ready'
            response=client.post('/api/chat', json={'question':'Xin chào','use_ai':False})
            assert response.status_code==429 and response.json()['detail']=='rate limited'
            trace=read_observed_trace(lines)
            assert any(e['event']=='request_error' and e['status_code']==429 for e in trace)
            assert client.get('/api/history').json()==[]


def test_web_observer_disconnect_does_not_cancel_real_chat(live_server, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    route=main.ENGINE.route
    def blocked(*args, **kwargs):
        entered.set();assert release.wait(8)
        return route(*args, **kwargs)
    monkeypatch.setattr(main.ENGINE, 'route', blocked)
    try:
        with HTTPClient(base_url=live_server, timeout=10) as client, ThreadPoolExecutor(max_workers=1) as pool:
            client.get('/api/bootstrap')
            with client.stream('GET', '/api/chat/trace/events') as observer:
                lines=observer.iter_lines();assert json.loads(next(lines))['event']=='observer_ready'
                future=pool.submit(client.post,'/api/chat',json={'question':'Xin chào','use_ai':False})
                assert entered.wait(2)
                assert json.loads(next(lines))['event']=='trace'
            release.set()
            assert future.result(timeout=5).status_code==200
            assert len(client.get('/api/history').json())==2
    finally:
        release.set()


def test_slow_or_closed_observer_is_bounded_and_cannot_fail_chat():
    import asyncio
    from app.live_trace import Subscription
    async def check():
        subscription=Subscription()
        for index in range(300): subscription.offer({'event':'start','span_id':str(index)})
        assert subscription.closed and subscription.queue.qsize()==1
        assert (await subscription.queue.get())['event']=='observer_overflow'
    asyncio.run(check())
    async def make(): return Subscription()
    closed=asyncio.run(make())
    closed.send({'event':'trace'})  # Event loop was closed: discard, never raise into /api/chat.
    assert closed.closed


@pytest.mark.parametrize('method', ['GET', 'POST'])
def test_web_observer_ready_does_not_wait_for_a_chat(live_server, method):
    with HTTPClient(base_url=live_server, timeout=3) as client:
        client.get('/api/bootstrap')
        with client.stream(method, '/api/chat/trace/events') as observer:
            assert observer.status_code == 200
            lines=observer.iter_lines()
            assert json.loads(next(lines))=={'event':'observer_ready'}
            response=client.post('/api/chat',json={'question':'Xin chào','use_ai':False})
            trace=read_observed_trace(lines)
            assert next(e['result'] for e in trace if e['event']=='result')==response.json()


def test_post_observer_retains_origin_and_session_guards(client, enabled, monkeypatch):
    client.cookies.clear()
    assert client.post('/api/chat/trace/events').status_code==401
    client.get('/api/bootstrap')
    assert client.post('/api/chat/trace/events',headers={'Origin':'https://evil.example'}).status_code==403
    monkeypatch.delenv('STUDENT_TRACE')
    assert client.post('/api/chat/trace/events').status_code==404

def test_trace_explains_tfidf_and_both_classifiers(client, enabled):
    client.get('/api/bootstrap')
    trace = events(client)
    names = [e['function'] for e in starts(trace)]
    assert any('TF-IDF từ' in n for n in names) and any('cosine' in n for n in names)
    assert any('LinearSVC' in n for n in names) and any('MLPClassifier' in n for n in names)
    tfidf = next(e for e in trace if e['event'] == 'end' and 'top_terms' in (e.get('output') or {}))
    assert {'tf', 'idf', 'weight_l2'} <= tfidf['output']['top_terms'][0].keys()
