"""
app/api/v1/auth.py
─────────────────────────────────────────────────────────────
Authentication endpoints — public routes (no Bearer required).

POST /api/v1/auth/register  →  Create user + issue JWT
POST /api/v1/auth/login     →  Validate credentials + issue JWT
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    _DUMMY_PASSWORD_HASH,
    create_token,
    hash_password,
    verify_password,
)
from app.db.postgres import get_db
from app.models.pg.tenant import Tenant
from app.models.pg.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    summary="Register a new user",
    description=(
        "Creates a new user account under the default 'Demo Corp' tenant "
        "and returns a signed JWT access token immediately."
    ),
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # ── Public registration is buyer-only (prevents privilege escalation) ──
    if body.role != "buyer":
        from app.core.exceptions import BadRequestError
        raise BadRequestError(
            "Public registration only supports the 'buyer' role. "
            "Contact an administrator to provision other roles."
        )

    # ── Check email uniqueness ────────────────────────────────
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise ConflictError("Email")

    # ── Resolve default tenant (Demo Corp) ────────────────────
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.name == "Demo Corp")
    )
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise UnauthorizedError("Default tenant not found. Ensure seed data ran correctly.")

    # ── Create user ───────────────────────────────────────────
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.flush()   # Flush to get the generated ID before commit

    # ── Issue token ───────────────────────────────────────────
    token, expires_in = create_token(user.id, tenant.id, user.role, user.email)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        role=user.role,
        tenant_id=tenant.id,
        user_id=user.id,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="Validates credentials and returns a signed JWT access token.",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # ── Fetch user ────────────────────────────────────────────
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Constant-time path: always run bcrypt compare even when user is missing
    stored_hash = user.hashed_password if user is not None else _DUMMY_PASSWORD_HASH
    if not verify_password(body.password, stored_hash):
        raise UnauthorizedError("Invalid email or password")
    if user is None:
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("Account is deactivated")

    # ── Issue token ───────────────────────────────────────────
    token, expires_in = create_token(user.id, user.tenant_id, user.role, user.email)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        role=user.role,
        tenant_id=user.tenant_id,
        user_id=user.id,
    )
