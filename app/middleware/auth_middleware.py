"""
app/middleware/auth_middleware.py
─────────────────────────────────────────────────────────────
OAuth2 Bearer token extraction + JWT validation middleware.

This middleware runs on EVERY incoming request before it
reaches any route handler. It:

  1. Reads the `Authorization: Bearer <token>` header
  2. Decodes and validates the JWT signature + expiry
  3. Injects the decoded payload into `request.state.token_data`

Routes that do NOT require authentication (public routes) are
on the SKIP_AUTH_PATHS list — the middleware passes through
those requests without checking for a token.

Protected routes use `get_current_user` (in dependencies.py)
which reads from `request.state.token_data`. If the middleware
didn't populate that state, the dependency raises 401.
"""

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_token
from app.config import settings

# ── Public routes — no token required ────────────────────────
SKIP_AUTH_PATHS: set[str] = {
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/metrics",
    "/graphql",    # GraphQL auth is handled per-resolver
    "/",
}


def _is_public(path: str) -> bool:
    """Returns True if the path is on the public allowlist."""
    if path in SKIP_AUTH_PATHS:
        return True
    # Allow all /docs sub-paths (Swagger static assets)
    if path.startswith("/docs/") or path.startswith("/redoc/"):
        return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Starlette BaseHTTPMiddleware that validates JWT Bearer tokens.

    On success  → populates request.state.token_data with the decoded payload
    On failure  → returns a 401 JSON response immediately (request never
                  reaches the route handler)
    On public   → passes through without token check
    """

    async def dispatch(self, request: Request, call_next):
        auth_header: str | None = request.headers.get("Authorization")
        token: str | None = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if token:
            # ── Decode + validate JWT ─────────────────────────────
            try:
                payload = decode_token(token)
                request.state.token_data = payload
            except jwt.ExpiredSignatureError:
                return JSONResponse(
                    status_code=401,
                    content={
                        "status": "error",
                        "code": 401,
                        "message": "Unauthorized",
                        "detail": "Token has expired. Please log in again.",
                    },
                )
            except jwt.InvalidTokenError as exc:
                detail = (
                    f"Invalid token: {exc}"
                    if settings.app_env == "development"
                    else "Invalid or malformed token."
                )
                return JSONResponse(
                    status_code=401,
                    content={
                        "status": "error",
                        "code": 401,
                        "message": "Unauthorized",
                        "detail": detail,
                    },
                )
        elif not _is_public(request.url.path):
            # ── Protected route with missing or invalid header ────
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": 401,
                    "message": "Unauthorized",
                    "detail": "Missing or malformed Authorization header. "
                              "Expected: 'Bearer <token>'",
                },
            )

        return await call_next(request)
