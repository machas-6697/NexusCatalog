"""
app/core/dependencies.py
─────────────────────────────────────────────────────────────
FastAPI dependency injection functions.

These are passed to route handlers via `Depends(...)` and
provide:
- get_current_user()  : returns the authenticated User ORM object
- require_role()      : factory that raises 403 if role doesn't match
- get_tenant_id()     : extracts tenant_id from request.state (set by middleware)
"""

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.postgres import get_db
from app.models.pg.user import User


# ── Token state accessor ──────────────────────────────────────

def _get_token_state(request: Request) -> dict:
    """
    Retrieves the decoded JWT payload injected by AuthMiddleware.
    Raises 401 if the middleware did not populate request.state.
    """
    token_data = getattr(request.state, "token_data", None)
    if token_data is None:
        raise UnauthorizedError("No valid authentication token found")
    return token_data


# ── Current user dependency ───────────────────────────────────

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the authenticated user from the database.

    Flow:
      1. AuthMiddleware already decoded the JWT → request.state.token_data
      2. This function reads the `sub` (user_id) from that state
      3. Fetches the User row from PostgreSQL
      4. Returns the ORM User object to the route handler
    """
    token_data = _get_token_state(request)
    user_id: str = token_data.get("sub", "")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("User account is deactivated")

    return user


# ── Tenant ID extractor ───────────────────────────────────────

def get_tenant_id(request: Request) -> str:
    """
    Extracts tenant_id from the decoded JWT state.
    Injected into route handlers that need tenant scoping.
    """
    token_data = _get_token_state(request)
    tenant_id = token_data.get("tenant_id")
    if not tenant_id:
        raise UnauthorizedError("Token missing tenant_id claim")
    return tenant_id


# ── RBAC role guard factory ───────────────────────────────────

def require_role(*allowed_roles: str):
    """
    Dependency factory — returns a dependency that raises 403
    if the authenticated user's role is not in `allowed_roles`.

    Usage in a route:
        @router.post("/tenants", dependencies=[Depends(require_role("admin"))])

    Or as a function parameter:
        async def my_route(user: User = Depends(require_role("admin"))):
    """
    async def role_checker(
        user: User = Depends(get_current_user),
    ) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError(
                f"Role '{user.role}' is not permitted. "
                f"Required: {list(allowed_roles)}"
            )
        return user

    return role_checker
