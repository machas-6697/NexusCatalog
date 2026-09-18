"""
Domain models — PostgreSQL ORM (app.models.pg) and MongoDB documents (app.models.mongo).
"""

from app.models.mongo import (
    EventCreate,
    EventDocument,
    EventResponse,
    ProductCreate,
    ProductDocument,
    ProductUpdate,
    ReviewCreate,
    ReviewDocument,
    ReviewResponse,
    new_product_doc,
)
from app.models.pg import (
    AuditLog,
    InventoryBatch,
    Order,
    OrderItem,
    Tenant,
    User,
    UserRole,
    Warehouse,
)

__all__ = [
    "AuditLog",
    "EventCreate",
    "EventDocument",
    "EventResponse",
    "InventoryBatch",
    "Order",
    "OrderItem",
    "ProductCreate",
    "ProductDocument",
    "ProductUpdate",
    "ReviewCreate",
    "ReviewDocument",
    "ReviewResponse",
    "Tenant",
    "User",
    "UserRole",
    "Warehouse",
    "new_product_doc",
]
