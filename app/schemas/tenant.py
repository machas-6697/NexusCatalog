"""
app/schemas/tenant.py
─────────────────────────────────────────────────────────────
Request and response schemas for tenant endpoints.
"""

from datetime import datetime

from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str


class TenantRead(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
