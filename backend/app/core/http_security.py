"""HTTP hardening: security headers, a CSRF guard for cookie sessions, no caching of API data."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings

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
        # Browsers only add a custom header to same-origin requests (there is no CORS config), so a
        # forged cross-site form or fetch carrying the session cookie is rejected here.
        if s.auth_mode != 'dev' and request.method in UNSAFE and path.startswith('/api/') \
                and request.headers.get(CSRF_HEADER, '').lower() != CSRF_VALUE:
            return JSONResponse({'detail': '缺少请求来源校验头'}, status_code=403)
        response = await call_next(request)
        h = response.headers
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
