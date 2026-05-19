import importlib
import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path
import types as _types

def _import_live_requests():
    """Import the real requests package while avoiding this mock module."""
    current_dir = Path(__file__).resolve().parent
    search_paths = []
    for path_entry in sys.path:
        try:
            if Path(path_entry).resolve() == current_dir:
                continue
        except Exception:
            pass
        search_paths.append(path_entry)

    spec = importlib.machinery.PathFinder.find_spec('requests', search_paths)
    if spec is None or spec.loader is None:
        return None, None

    existing_requests = sys.modules.get('requests')
    existing_requests_adapters = sys.modules.get('requests.adapters')

    module = importlib.util.module_from_spec(spec)

    try:
        sys.modules['requests'] = module
        spec.loader.exec_module(module)
        adapters = importlib.import_module('requests.adapters')
    except Exception:
        if existing_requests is not None:
            sys.modules['requests'] = existing_requests
        else:
            sys.modules.pop('requests', None)

        if existing_requests_adapters is not None:
            sys.modules['requests.adapters'] = existing_requests_adapters
        else:
            sys.modules.pop('requests.adapters', None)
        return None, None

    if existing_requests is not None:
        sys.modules['requests'] = existing_requests
    else:
        sys.modules.pop('requests', None)

    if existing_requests_adapters is not None:
        sys.modules['requests.adapters'] = existing_requests_adapters
    else:
        sys.modules.pop('requests.adapters', None)

    return module, adapters


_live_requests, _live_requests_adapters = _import_live_requests()
_use_live:bool = False
_live_exceptions = getattr(_live_requests, 'exceptions', None) if _live_requests is not None else None

if _live_exceptions is not None and hasattr(_live_exceptions, 'RequestException') and hasattr(_live_exceptions, 'HTTPError'):
    class _LiveMockRequestException(_live_exceptions.RequestException):
        pass

    class _LiveMockHTTPError(_live_exceptions.HTTPError):
        pass

    MockRequestException = _LiveMockRequestException
    MockHTTPError = _LiveMockHTTPError
    TimeoutBase = getattr(_live_exceptions, 'Timeout', _LiveMockRequestException)
else:
    class MockRequestException(Exception):
        pass

    class MockHTTPError(MockRequestException):
        pass

    TimeoutBase = MockRequestException


class MockResponse:
    def __init__(self, status_code:int = 200, content:bytes|str = b'', json_data = None, reason:str = 'OK',
                 headers:dict|None = None, url:str = '') -> None:
        self.status_code = status_code
        self.reason = reason
        self.headers = headers or {}
        self.url = url
        self._json_data = json_data

        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        elif isinstance(content, (bytes, bytearray, memoryview)):
            content_bytes = bytes(content)
        else:
            content_bytes = str(content).encode('utf-8')

        if json_data is not None and content_bytes == b'':
            content_bytes = json.dumps(json_data).encode('utf-8')

        self.content = content_bytes
        self.text = content_bytes.decode('utf-8', errors='replace')

    def json(self):
        if self._json_data is not None:
            return self._json_data
        if not self.content:
            return {}
        return json.loads(self.content)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise MockHTTPError(f'{self.status_code} {self.reason}')

    def iter_content(self, chunk_size: int = 1):
        if chunk_size <= 0:
            chunk_size = 1
        for index in range(0, len(self.content), chunk_size):
            yield self.content[index:index + chunk_size]


class MockSession:
    _instance = None

    # Singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, '_initialized'): return

        self.calls = []
        self.queued_responses = {'get': {}, 'post': {}, 'put': {}, 'patch': {}, 'delete': {},
                                 'head': {}, 'options': {}}
        self.sticky_responses = {'get': {}, 'post': {}, 'put': {}, 'patch': {}, 'delete': {},
                                 'head': {}, 'options': {}}

        # Session attributes matching requests.Session
        self.headers = {}
        self.cookies = {}
        self.params = {}
        self.auth = None
        self.proxies = {}
        self.hooks = {}
        self.verify = True
        self.cert = None
        self.timeout = None
        self.trust_env = True

        self._initialized = True

    def _mock_request(self, method: str, url: str, **kwargs) -> MockResponse:
        call = {'method': method, 'url': url, **kwargs}
        self.calls.append(call)

        response:MockResponse|None = None
        if url in self.queued_responses[method] and len(self.queued_responses[method][url]) > 0:
            response = self.queued_responses[method][url].pop(0)
        if response == None and 'any' in self.queued_responses[method] and len(self.queued_responses[method]['any']) > 0:
            response = self.queued_responses[method]['any'].pop(0)
        if response == None and url in self.sticky_responses[method]:
            response = self.sticky_responses[method][url]
        if response == None and 'any' in self.sticky_responses[method]:
            response = self.sticky_responses[method]['any']
        if response == None:
            print(f"No response for {method.upper()} {url}, returning 404")
            response = MockResponse(status_code=404, reason='Not Found')
        response.url = url
        return response

    def get(self, url: str, **kwargs):
        return self._mock_request('get', url, **kwargs)

    def post(self, url: str, **kwargs):
        return self._mock_request('post', url, **kwargs)

    def put(self, url: str, **kwargs):
        return self._mock_request('put', url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self._mock_request('patch', url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self._mock_request('delete', url, **kwargs)

    def head(self, url: str, **kwargs):
        return self._mock_request('head', url, **kwargs)

    def options(self, url: str, **kwargs):
        return self._mock_request('options', url, **kwargs)

    def close(self) -> None:
        return None

    def mount(self, *args, **kwargs) -> None:
        return None
_mock_requests = MockSession()
_live_session = None

def RequestsSession():
    """Factory function: returns either a live or mock requests.Session.

    Returns the appropriate session object (mock or live) directly, ensuring
    that all session attributes like headers, cookies, params, etc. work
    correctly on the returned object.
    """
    global _live_session
    if not _use_live or _live_requests is None:
        return _mock_requests

    if _live_session is None:
        _live_session = _live_requests.Session()
    return _live_session

def _request(method: str, url: str, **kwargs):
    """ Call the appropriate live or mock request method """
    if not _use_live or _live_requests is None:
        return getattr(_mock_requests, method)(url, **kwargs)
    return getattr(_live_requests, method)(url, **kwargs)


def queue_response(method:str, response: MockResponse, url:str|None = None, sticky:bool = False) -> None:
    """ Enable queuing a mock response. It can be one-time (sticky=False) or sticky (sticky=True), for a specific URL or any URL (url=None). """
    if url is None: url = 'any'
    if sticky:
        _mock_requests.sticky_responses[method.lower()][url] = response
    elif url not in _mock_requests.queued_responses[method.lower()]:
        _mock_requests.queued_responses[method.lower()][url] = [response]
    else:
        _mock_requests.queued_responses[method.lower()][url].append(response)

def live_requests(set:bool|None = None) -> bool:
    """ Configure whether to use live requests or the mock. If set is None, returns the current state. """
    global _use_live
    if set != None:
        _use_live = set
    if set != None and not _use_live:
        _mock_requests.calls.clear()
        for responses in _mock_requests.queued_responses.values():
            responses.clear()

    return _use_live

_request_attrs = {
    'Response': MockResponse,
    'Session': RequestsSession,
    'RequestException': (_live_exceptions.RequestException if _live_exceptions is not None and hasattr(_live_exceptions, 'RequestException') else MockRequestException),
    'HTTPError': (_live_exceptions.HTTPError if _live_exceptions is not None and hasattr(_live_exceptions, 'HTTPError') else MockHTTPError),
    'Timeout': TimeoutBase,
    'queue_response': queue_response,
    'calls': _mock_requests.calls,
    'queued_responses': _mock_requests.queued_responses,
    'codes': (_live_requests.codes if _live_requests is not None else _types.SimpleNamespace(ok=200)),
    'utils': (_live_requests.utils if _live_requests is not None else _types.SimpleNamespace(requote_uri=lambda value: value)),
    'exceptions': (_live_exceptions if _live_exceptions is not None else _types.SimpleNamespace(
        RequestException=MockRequestException,
        HTTPError=MockHTTPError,
        Timeout=MockRequestException,
    )),
    'get': lambda url, **kwargs: _request('get', url, **kwargs),
    'post': lambda url, **kwargs: _request('post', url, **kwargs),
    'put': lambda url, **kwargs: _request('put', url, **kwargs),
    'patch': lambda url, **kwargs: _request('patch', url, **kwargs),
    'delete': lambda url, **kwargs: _request('delete', url, **kwargs),
    'head': lambda url, **kwargs: _request('head', url, **kwargs),
    'options': lambda url, **kwargs: _request('options', url, **kwargs),
}
for _name, _value in _request_attrs.items():
    setattr(sys.modules[__name__], _name, _value)

if _live_requests_adapters is None:
    _requests_adapters = _types.ModuleType('requests.adapters')
    setattr(_requests_adapters, 'HTTPAdapter', type('HTTPAdapter', (), {}))
else:
    _requests_adapters = _live_requests_adapters

# Ensure imports of both "tests.edmc.requests" and "requests" share this module instance.
sys.modules['requests'] = sys.modules[__name__]
sys.modules['requests.adapters'] = _requests_adapters
