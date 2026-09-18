"""
app/schemas/order.py
─────────────────────────────────────────────────────────────
Request and response schemas for order endpoints.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


# ── Order Item schemas ────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal


class OrderItemRead(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal

    model_config = {"from_attributes": True}


# ── Order schemas ─────────────────────────────────────────────

class OrderCreate(BaseModel):
    items: list[OrderItemCreate]


class OrderRead(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    status: str
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    """PATCH /orders/{id} — update order status (admin only)."""
    status: str
