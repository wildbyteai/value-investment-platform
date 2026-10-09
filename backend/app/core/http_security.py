"""HTTP hardening: request ids, security headers, a CSRF guard for cookie sessions, no caching of API data."""
import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.core.errors import body

access_log = logging.getLogger('app.access')
REQUEST_ID = 'X-Request-Id'
_SAFE_ID = re.compile(r'^[A-Za-z0-9._\-]{8,64}$')

CSRF_HEADER = 'x-requested-with'
CSRF_VALUE = 'vip'
UNSAFE = {'POST', 'PUT', 'PATCH', 'DELETE'}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self'; font-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; "
       "frame-ancestors 'none'")


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        s = get_settings()
        path = request.url.path
        incoming = request.headers.get(REQUEST_ID, '')
        request.state.request_id = rid = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex
        started = time.perf_counter()
        # Browsers only add a custom header to same-origin requests (there is no CORS config), so a
        # forged cross-site form or fetch carrying the session cookie is rejected here.
        if s.auth_mode != 'dev' and request.method in UNSAFE and path.startswith('/api/') \
                and request.headers.get(CSRF_HEADER, '').lower() != CSRF_VALUE:
            return JSONResponse(body(403, '缺少请求来源校验头', rid, 'csrf'), status_code=403, headers={REQUEST_ID: rid})
        response = await call_next(request)
        h = response.headers
        h[REQUEST_ID] = rid
        if path.startswith('/api/'):
            access_log.info('%s %s %s %.0fms rid=%s', request.method, path, response.status_code,
                            (time.perf_counter() - started) * 1000, rid)
        h.setdefault('X-Content-Type-Options', 'nosniff')
        h.setdefault('X-Frame-Options', 'DENY')
        h.setdefault('Referrer-Policy', 'no-referrer')
        h.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        h.setdefault('Content-Security-Policy', CSP)
        h.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        if s.cookie_secure:
            h.setdefault('Strict-Transport-Security', 'max-age=31536000')
        if path.startswith('/api/'):
            h['Cache-Control'] = 'no-store'
        elif path in ('/', '/index.html'):
            h['Cache-Control'] = 'no-cache'
        return response
