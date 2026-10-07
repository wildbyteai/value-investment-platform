"""Domain errors: services raise these, the HTTP layer turns them into responses.

Services must not import FastAPI. Each error carries the HTTP status it maps to,
so existing API behaviour (status code + ``{"detail": ...}`` body) is unchanged.
"""
from __future__ import annotations


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class Forbidden(DomainError):
    """The caller or mode is not allowed to do this."""
    status_code = 403


class NotFound(DomainError):
    """The object does not exist in the caller's workspace or mode."""
    status_code = 404


class Conflict(DomainError):
    """State changed or a precondition is not met; retrying later may succeed."""
    status_code = 409


class Invalid(DomainError):
    """The request itself is invalid."""
    status_code = 422


def install(app) -> None:
    """Register the JSON handler on a FastAPI app."""
    from fastapi.responses import JSONResponse

    @app.exception_handler(DomainError)
    async def _domain_error(_request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})
