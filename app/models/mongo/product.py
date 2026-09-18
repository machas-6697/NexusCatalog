"""
app/models/mongo/product.py
─────────────────────────────────────────────────────────────
Pydantic model representing a MongoDB Product document.

MongoDB stores products as flexible BSON documents, so Pydantic
is used for validation and serialization rather than SQLAlchemy.

The `attributes` field accepts any dict — this is the key
advantage of MongoDB: adding new product attributes (colour,
size, weight, material) requires no schema migration.

MongoDB _id is stored as a string alias `id` in API responses.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ProductDocument(BaseModel):
    """
    Represents a product document as stored in MongoDB.
    Used for reading from the collection.
    """
    id: str = Field(..., alias="_id")
    tenant_id: str
    name: str
    description: str
    price: float
    stock: int
    category: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class ProductCreate(BaseModel):
    """Payload accepted when creating a new product."""
    name: str
    description: str
    price: float
    stock: int = 0
    category: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    """All fields optional — PATCH semantics."""
    name: str | None = None
    description: str | None = None
    price: float | None = None
    stock: int | None = None
    category: str | None = None
    attributes: dict[str, Any] | None = None


def new_product_doc(
    tenant_id: str,
    product_id: str,
    data: ProductCreate,
) -> dict:
    """
    Builds a raw MongoDB document dict ready for insertion.
    `_id` is set explicitly so we control the format.
    """
    now = datetime.now(timezone.utc)
    return {
        "_id": product_id,
        "tenant_id": tenant_id,
        "name": data.name,
        "description": data.description,
        "price": data.price,
        "stock": data.stock,
        "category": data.category,
        "attributes": data.attributes,
        "created_at": now,
        "updated_at": now,
    }
