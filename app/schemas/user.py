"""
app/schemas/user.py
─────────────────────────────────────────────────────────────
Request and response schemas for user endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: str
    tenant_id: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """PATCH /users/me — all fields optional."""
    email: EmailStr | None = None
    password: str | None = None
