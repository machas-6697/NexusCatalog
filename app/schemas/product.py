"""
app/schemas/product.py
─────────────────────────────────────────────────────────────
Request and response schemas for product endpoints (REST layer).
MongoDB-backed product schemas with cursor-based pagination.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProductRead(BaseModel):
    """Serialized product returned in REST v1 responses."""
    id: str
    tenant_id: str
    name: str
    description: str
    price: float
    stock: int
    category: str
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PaginatedProductResponse(BaseModel):
    """
    Wraps a page of products with cursor-based pagination metadata.

    next_cursor: opaque string the client passes as ?cursor= on the
                 next request. None means there are no more pages.
    """
    items: list[ProductRead]
    total: int
    next_cursor: str | None = None


# ── v2 schema (evolved) ───────────────────────────────────────

class ProductReadV2(BaseModel):
    """
    v2 schema: price is returned as a formatted decimal string
    instead of a raw float, and the response is always paginated.
    """
    id: str
    tenant_id: str
    name: str
    description: str
    price: str              # "99.99" instead of 99.99
    stock: int
    category: str
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PaginatedProductResponseV2(BaseModel):
    items: list[ProductReadV2]
    total: int
    next_cursor: str | None = None
