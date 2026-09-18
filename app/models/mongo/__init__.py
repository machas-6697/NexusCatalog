"""
app/models/mongo/__init__.py
─────────────────────────────────────────────────────────────
Exports MongoDB catalog models and document helper functions.
"""

from app.models.mongo.product import (
    ProductCreate,
    ProductDocument,
    ProductUpdate,
    new_product_doc,
)
from app.models.mongo.review import ReviewCreate, ReviewDocument, ReviewResponse
from app.models.mongo.event import EventCreate, EventDocument, EventResponse

__all__ = [
    "ProductDocument",
    "ProductCreate",
    "ProductUpdate",
    "new_product_doc",
    "ReviewDocument",
    "ReviewCreate",
    "ReviewResponse",
    "EventDocument",
    "EventCreate",
    "EventResponse",
]
