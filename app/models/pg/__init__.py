"""
app/models/pg/__init__.py
─────────────────────────────────────────────────────────────
Exports all PostgreSQL SQLAlchemy ORM models so that importing
this package registers all models with SQLAlchemy's Base metadata.
"""

from app.models.pg.tenant import Tenant
from app.models.pg.user import User, UserRole
from app.models.pg.order import Order, OrderItem
from app.models.pg.audit import AuditLog
from app.models.pg.inventory import Warehouse, InventoryBatch

__all__ = [
    "Tenant",
    "User",
    "UserRole",
    "Order",
    "OrderItem",
    "AuditLog",
    "Warehouse",
    "InventoryBatch",
]
