"""Request-local, opt-in observation. Never installs a global profiler or stores traces."""
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import hashlib
import inspect
from pathlib import Path
import time

PROJECT = Path(__file__).resolve().parents[1]
_current = ContextVar('student_trace', default=None)
PRIVATE = {'api_key', 'authorization', 'cookie', 'password', 'token', 'session_id',
           'sid', 'salt', 'hash', 'base_url', 'evidence'}


def snapshot(value, depth=0):
    """Bounded previews; credentials, private evidence and arbitrary objects are omitted."""
    if depth > 7:
        return '[rút gọn: độ sâu]'
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= 12000 else value[:12000] + '… [rút gọn]'
    if hasattr(value, 'model_dump'):
        return snapshot(value.model_dump(), depth + 1)
    if isinstance(value, dict):
        out = {str(k): '[không thu thập]' if str(k).lower() in PRIVATE else snapshot(v, depth + 1)
               for k, v in list(value.items())[:40]}
        if len(value) > 40:
            out['_omitted_keys'] = len(value) - 40
        return out
    if isinstance(value, (tuple, list)):
        out = [snapshot(v, depth + 1) for v in value[:8]]
        if len(value) > 8:
            out.append({'_omitted_items': len(value) - 8})
        return out
    return '[không thu thập đối tượng ' + type(value).__name__ + ']'


def source_ref(function):
    function = inspect.unwrap(function)
    lines, start = inspect.getsourcelines(function)
    return {'path': str(Path(inspect.getfile(function)).relative_to(PROJECT)),
            'line': start, 'end_line': start + len(lines) - 1,
            'sha256': hashlib.sha256(''.join(lines).encode()).hexdigest(),
            'code': ''.join(lines)}


class Recorder:
    def __init__(self, emit):
        self.emit = emit
        self.started = time.perf_counter()
        self.sequence = 0
        self.stack = []

    def send(self, event, **fields):
        self.sequence += 1
        self.emit({'event': event, 'seq': self.sequence,
                   'at': datetime.now(timezone.utc).isoformat(),
                   'elapsed_ms': round((time.perf_counter() - self.started) * 1000, 3), **fields})


class span:
    def __init__(self, node, function, input_value, source=None):
        self.recorder = _current.get()
        self.node, self.function, self.input = node, function, input_value
        self.output = None
        self.source = source
        if self.recorder and source is None:
            frame = inspect.currentframe().f_back
            self.source = {'path': str(Path(frame.f_code.co_filename).relative_to(PROJECT)),
                           'line': frame.f_lineno, 'end_line': frame.f_lineno}
            del frame

    def __enter__(self):
        r = self.recorder
        if r:
            self.started = time.perf_counter()
            self.id = str(r.sequence + 1)
            self.parent = r.stack[-1] if r.stack else None
            r.send('start', span_id=self.id, parent_id=self.parent, node=self.node,
                   function=self.function, input=snapshot(self.input), source=self.source)
            r.stack.append(self.id)
        return self

    def __exit__(self, kind, error, traceback):
        r = self.recorder
        if r:
            r.stack.pop()
            fields = {'span_id': self.id, 'duration_ms': round((time.perf_counter() - self.started) * 1000, 3)}
            if error:
                fields['error'] = {'type': kind.__name__, 'status_code': getattr(error, 'status_code', None)}
            else:
                fields['output'] = snapshot(self.output)
            r.send('error' if error else 'end', **fields)
        return False


def traced(node, fields):
    def decorate(function):
        signature = inspect.signature(function)
        @wraps(function)
        def observe(*args, **kwargs):
            if _current.get() is None:
                return function(*args, **kwargs)
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            values = {key: bound.arguments[key] for key in fields if key in bound.arguments}
            with span(node, function.__qualname__ + '()', values, source_ref(function)) as event:
                result = function(*args, **kwargs)
                event.output = result
                return result
        return observe
    return decorate


def record_call(emit, function, *args):
    token = _current.set(Recorder(emit))
    try:
        return function(*args)
    finally:
        _current.reset(token)
