"""Observe real chat calls for their own visitor; no persisted or replayed traces."""
import asyncio
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading

from fastapi import HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
from .tracing import record_call

DOCS = Path(__file__).resolve().parents[1] / 'docs' / 'architecture'
SLOTS = threading.BoundedSemaphore(4)
_workers = set()
_observer_lock = threading.Lock()
_observers = {}


class Subscription:
    """A bounded, disposable queue owned by one observer's event loop."""
    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue(maxsize=256)
        self.closed = False

    def offer(self, event):
        if self.closed:
            return
        if self.queue.full():
            while not self.queue.empty():
                self.queue.get_nowait()
            self.closed = True
            self.queue.put_nowait({'event': 'observer_overflow'})
        else:
            self.queue.put_nowait(event)

    def send(self, event):
        if not self.closed:
            try:
                self.loop.call_soon_threadsafe(self.offer, event)
            except RuntimeError:
                # A vanished observer must never fail an ordinary chat request.
                self.closed = True


def subscribe(sid):
    with _observer_lock:
        if sum(map(len, _observers.values())) >= 32 or len(_observers.get(sid, ())) >= 4:
            raise HTTPException(429, 'Quá nhiều trang trace đang mở. Hãy đóng bớt tab rồi thử lại.')
        subscription = Subscription()
        _observers.setdefault(sid, set()).add(subscription)
    return subscription


def unsubscribe(sid, subscription):
    subscription.closed = True
    with _observer_lock:
        listeners = _observers.get(sid)
        if listeners is not None:
            listeners.discard(subscription)
            if not listeners:
                _observers.pop(sid, None)


def observe_chat(function):
    """Keep /api/chat's JSON/error/cookie contract while observing subscribed sessions."""
    @wraps(function)
    def observe(body, request, response):
        if os.getenv('STUDENT_TRACE') != '1' or request.url.path != '/api/chat':
            return function(body, request, response)
        raw = request.cookies.get('haui_visitor', '')
        sid = hashlib.sha256(raw.encode()).hexdigest() if raw else ''
        with _observer_lock:
            listeners = tuple(s for s in _observers.get(sid, ()) if not s.closed)
        if not listeners:
            return function(body, request, response)
        trace_id = secrets.token_hex(12)

        def emit(event):
            envelope = {**event, 'trace_id': trace_id}
            for listener in listeners:
                listener.send(envelope)

        emit({'event': 'trace', 'mode': 'live', 'origin': 'web-chat', 'question': body.question})
        try:
            result = record_call(emit, function, body, request, response)
            emit({'event': 'result', 'result': result})
            return result
        except HTTPException as error:
            emit({'event': 'request_error', 'status_code': error.status_code, 'detail': error.detail})
            raise
        except Exception as error:
            emit({'event': 'request_error', 'status_code': 500, 'detail': type(error).__name__})
            raise
        finally:
            emit({'event': 'done'})
    return observe


def require_enabled():
    if os.getenv('STUDENT_TRACE') != '1':
        raise HTTPException(404, 'Chế độ trace chưa bật. Khởi chạy với STUDENT_TRACE=1.')


def install_live_trace(app, chat_model, chat_handler, database):
    def own_session(request):
        raw = request.cookies.get('haui_visitor', '')
        sid = hashlib.sha256(raw.encode()).hexdigest() if raw else ''
        with sqlite3.connect(database) as connection:
            found = connection.execute('SELECT id FROM sessions WHERE id=?', (sid,)).fetchone()
        if not found:
            raise HTTPException(401, 'Hãy tải /api/bootstrap để tạo phiên trước khi trace.')
        return sid

    @app.get('/architecture/live', include_in_schema=False)
    def live_page():
        require_enabled()
        return FileResponse(DOCS / 'live.html', headers={'Cache-Control': 'no-store'})

    @app.get('/architecture/assets/{name}', include_in_schema=False)
    def live_asset(name: str):
        require_enabled()
        if name not in {'live.js', 'live.css', 'live-diagram.css'}:
            raise HTTPException(404)
        return FileResponse(DOCS / name, headers={'Cache-Control': 'no-cache'})

    @app.get('/api/chat/trace/events', include_in_schema=False)
    @app.post('/api/chat/trace/events', include_in_schema=False)
    async def observe_events(request: Request):
        require_enabled()
        sid = await run_in_threadpool(own_session, request)
        subscription = subscribe(sid)

        async def stream():
            try:
                yield '{"event":"observer_ready"}\n'
                while True:
                    try:
                        event = await asyncio.wait_for(subscription.queue.get(), timeout=10)
                    except asyncio.TimeoutError:
                        yield '{"event":"heartbeat"}\n'
                        continue
                    yield json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n'
                    if event['event'] == 'observer_overflow':
                        break
            finally:
                unsubscribe(sid, subscription)

        return StreamingResponse(stream(), media_type='application/x-ndjson',
                                 headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

    @app.post('/api/chat/trace', include_in_schema=False)
    async def trace_chat(body: chat_model, request: Request):
        require_enabled()
        # bootstrap() establishes the ordinary visitor cookie. Never expose another session.
        await run_in_threadpool(own_session, request)
        if not body.question.strip():
            raise HTTPException(422, 'Bạn hãy nhập một câu hỏi có nội dung.')
        if not SLOTS.acquire(blocking=False):
            raise HTTPException(429, 'Đã có 4 lượt trace đang chạy. Hãy thử lại sau.')
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue(maxsize=256)
        closed = threading.Event()
        trace_id = secrets.token_hex(12)

        def enqueue(event):
            if not closed.is_set():
                queue.put_nowait(event)

        def emit(event):
            if not closed.is_set():
                loop.call_soon_threadsafe(enqueue, event)

        def execute():
            try:
                result = record_call(emit, chat_handler, body, request, Response())
                emit({'event': 'result', 'result': result})
            except HTTPException as error:
                emit({'event': 'request_error', 'status_code': error.status_code, 'detail': error.detail})
            except Exception as error:
                emit({'event': 'request_error', 'status_code': 500, 'detail': type(error).__name__})
            finally:
                emit({'event': 'done'})
                SLOTS.release()

        async def stream():
            # Own the worker before yielding so immediate disconnect cannot strand a slot.
            worker = asyncio.create_task(run_in_threadpool(execute))
            _workers.add(worker)
            worker.add_done_callback(_workers.discard)
            try:
                yield json.dumps({'event': 'trace', 'trace_id': trace_id, 'mode': 'live'}) + '\n'
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=10)
                    except asyncio.TimeoutError:
                        yield '{"event":"heartbeat"}\n'
                        continue
                    yield json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n'
                    if event['event'] == 'done':
                        break
            finally:
                # Disconnect ends observation. The normal handler still finishes its DB transaction.
                closed.set()

        return StreamingResponse(stream(), media_type='application/x-ndjson',
                                 headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})
