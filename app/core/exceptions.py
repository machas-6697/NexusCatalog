"""
app/core/exceptions.py
─────────────────────────────────────────────────────────────
Custom exception classes and global exception handlers.

All unhandled errors are caught here and converted into a
consistent JSON error envelope:

    {
        "status": "error",
        "code":   404,
        "message": "Resource not found",
        "detail":  "..."
    }
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings


# ── Custom exception base ─────────────────────────────────────

class NexusException(Exception):
    """Base class for all application-level exceptions."""

    def __init__(self, status_code: int, message: str, detail: str = ""):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundError(NexusException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"{resource} not found",
        )


class UnauthorizedError(NexusException):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Unauthorized",
            detail=detail,
        )


class ForbiddenError(NexusException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Forbidden",
            detail=detail,
        )


class ConflictError(NexusException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            message=f"{resource} already exists",
        )


class BadRequestError(NexusException):
    def __init__(self, detail: str = "Invalid request"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Bad Request",
            detail=detail,
        )


# ── Error response builder ────────────────────────────────────

def _error_response(status_code: int, message: str, detail: str = "") -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "code": status_code,
            "message": message,
            "detail": detail,
        },
    )


# ── Handler registration ──────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """
    Attaches all global exception handlers to the FastAPI app.
    Call this once in main.py during app construction.
    """

    @app.exception_handler(NexusException)
    async def nexus_exception_handler(
        request: Request, exc: NexusException
    ) -> JSONResponse:
        return _error_response(exc.status_code, exc.message, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Flatten Pydantic validation errors into readable strings
        errors = "; ".join(
            f"{' -> '.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Validation failed",
            detail=errors,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        detail = str(exc) if settings.app_env == "development" else ""
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error",
            detail=detail,
        )
