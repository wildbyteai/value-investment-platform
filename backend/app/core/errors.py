"""Errors: services raise domain errors, the HTTP layer turns every error into one shape.

Every non-2xx API response has the body::

    {"error": {"code": "not_found", "message": "人能读懂的一句话", "details": [...]},
     "detail": "同 message（为兼容旧前端保留）",
     "request_id": "与响应头 X-Request-Id 相同"}

Services must not import FastAPI.
"""
from __future__ import annotations


class DomainError(Exception):
    status_code = 400
    code = 'bad_request'

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class Forbidden(DomainError):
    """The caller or mode is not allowed to do this."""
    status_code = 403
    code = 'forbidden'


class NotFound(DomainError):
    """The object does not exist in the caller's workspace or mode."""
    status_code = 404
    code = 'not_found'


class Conflict(DomainError):
    """State changed or a precondition is not met; retrying later may succeed."""
    status_code = 409
    code = 'conflict'


class Invalid(DomainError):
    """The request itself is invalid."""
    status_code = 422
    code = 'invalid'


class NotImplementedYet(DomainError):
    """The route is part of the published contract but its PR has not landed yet (ADR 0016)."""
    status_code = 501
    code = 'not_implemented'


CODES = {400: 'bad_request', 401: 'unauthorized', 403: 'forbidden', 404: 'not_found', 405: 'method_not_allowed',
         409: 'conflict', 413: 'too_large', 422: 'invalid', 429: 'rate_limited', 500: 'internal', 501: 'not_implemented', 503: 'unavailable'}


def body(status: int, message, request_id: str | None = None, code: str | None = None, details=None) -> dict:
    if not isinstance(message, str):
        details = message if details is None else details
        message = '请求未完成，请检查输入后重试'
    out = {'error': {'code': code or CODES.get(status, 'error'), 'message': message}, 'detail': message}
    if details:
        out['error']['details'] = details
    if request_id:
        out['request_id'] = request_id
    return out


def _field(loc) -> str:
    parts = [str(p) for p in loc if p not in ('body', 'query', 'path', 'header')]
    return '.'.join(parts) or '输入'


def install(app) -> None:
    """Register the JSON handlers on a FastAPI app."""
    import logging

    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    log = logging.getLogger('app.errors')

    def rid(request):
        return getattr(request.state, 'request_id', None)

    @app.exception_handler(DomainError)
    async def _domain_error(request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content=body(exc.status_code, exc.detail, rid(request), exc.code))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=body(exc.status_code, exc.detail, rid(request)),
                            headers=getattr(exc, 'headers', None))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request, exc: RequestValidationError):
        details = [{'field': _field(e.get('loc', ())), 'message': e.get('msg', '')} for e in exc.errors()]
        message = '；'.join(f"{d['field']}：{d['message']}" for d in details) or '输入不正确'
        return JSONResponse(status_code=422, content=body(422, message, rid(request), 'invalid', details))

    @app.exception_handler(Exception)
    async def _unexpected(request, exc: Exception):
        log.exception('unhandled error request_id=%s path=%s', rid(request), request.url.path)
        return JSONResponse(status_code=500, content=body(500, '服务出错了，请稍后重试；如果一直出错，把请求编号发给管理员', rid(request)))
