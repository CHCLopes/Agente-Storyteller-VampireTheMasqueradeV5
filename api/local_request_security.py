"""Browser boundary for the approved single-operator, loopback deployment.

Not user authentication. Native callers on the same machine remain trusted.
The launcher must still bind its listener to loopback; headers cannot prove it.
Never derive an allowed origin from Forwarded/X-Forwarded-* request headers.
"""
from urllib.parse import urlsplit

from starlette.responses import PlainTextResponse


def _local_authority(value: str) -> bool:
    try:
        parsed = urlsplit('http://' + value)
        return (parsed.hostname in {'127.0.0.1', 'localhost', '::1'}
            and parsed.username is None and parsed.password is None
            and not parsed.path and not parsed.query and not parsed.fragment
            and (parsed.port is None or 1 <= parsed.port <= 65535)
            and value == value.strip() and not any(c.isspace() for c in value))
    except (ValueError, UnicodeError):
        return False


def _local_origin(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in {'http', 'https'} and _local_authority(parsed.netloc)
            and not parsed.path and not parsed.query and not parsed.fragment)
    except (ValueError, UnicodeError):
        return False


class LocalRequestBoundary:
    def __init__(self, app, *, frontend_origins=()):
        self.app = app
        self.frontend_origins = frozenset(
            origin for origin in frontend_origins if _local_origin(origin))

    async def __call__(self, scope, receive, send):
        if scope['type'] not in {'http', 'websocket'}:
            return await self.app(scope, receive, send)
        hosts, origins, fetch_sites = [], [], []
        for name, raw in scope.get('headers', ()):
            name = name.lower()
            if name in {b'host', b'origin', b'sec-fetch-site'}:
                value = raw.decode('latin-1')
                {b'host': hosts, b'origin': origins, b'sec-fetch-site': fetch_sites}[name].append(value)
        allowed = len(hosts) == 1 and _local_authority(hosts[0]) and len(origins) <= 1
        if allowed and origins:
            scheme = 'https' if scope.get('scheme') in {'https', 'wss'} else 'http'
            allowed = (_local_origin(origins[0]) and
                origins[0] in self.frontend_origins | {f'{scheme}://{hosts[0]}'})
        elif allowed and 'cross-site' in fetch_sites:
            allowed = False
        if allowed:
            return await self.app(scope, receive, send)
        if scope['type'] == 'websocket':
            return await send({'type': 'websocket.close', 'code': 1008})
        return await PlainTextResponse('Local request rejected', status_code=403)(scope, receive, send)
