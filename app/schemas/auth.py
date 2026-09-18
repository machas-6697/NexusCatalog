"""
app/schemas/auth.py
─────────────────────────────────────────────────────────────
Request and response schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = "buyer"          # Public registration — only buyer is accepted


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int              # Seconds until expiry
    role: str
    tenant_id: str
    user_id: str
