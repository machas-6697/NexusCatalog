"""
app/api/v1/users.py
─────────────────────────────────────────────────────────────
User profile endpoints — authenticated, tenant-scoped.

GET   /api/v1/users/me   →  Return own profile
PATCH /api/v1/users/me   →  Update own email or password
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.db.postgres import get_db
from app.models.pg.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get my profile",
    description="Returns the authenticated user's profile details.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update my profile",
    description="Partially update email and/or password. All fields optional.",
)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    # ── Check new email uniqueness ────────────────────────────
    if body.email and body.email != current_user.email:
        result = await db.execute(
            select(User).where(User.email == body.email)
        )
        if result.scalar_one_or_none():
            raise ConflictError("Email")
        current_user.email = body.email

    if body.password:
        current_user.hashed_password = hash_password(body.password)

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)
