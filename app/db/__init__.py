"""
Database access layer — PostgreSQL (3 engines) and MongoDB (3 databases).
"""

from app.db.mongo import (
    close_mongo,
    get_collection,
    get_events_collection,
    get_events_db,
    get_mongo_client,
    get_mongo_db,
    get_reviews_collection,
    get_reviews_db,
)
from app.db.postgres import (
    AsyncSessionAudit,
    AsyncSessionInventory,
    AsyncSessionLocal,
    Base,
    BaseAudit,
    BaseInventory,
    create_all_tables,
    dispose_engine,
    get_audit_db,
    get_db,
    get_inventory_db,
)
from app.db.seed import seed_all_databases

__all__ = [
    "AsyncSessionAudit",
    "AsyncSessionInventory",
    "AsyncSessionLocal",
    "Base",
    "BaseAudit",
    "BaseInventory",
    "close_mongo",
    "create_all_tables",
    "dispose_engine",
    "get_audit_db",
    "get_collection",
    "get_db",
    "get_events_collection",
    "get_events_db",
    "get_inventory_db",
    "get_mongo_client",
    "get_mongo_db",
    "get_reviews_collection",
    "get_reviews_db",
    "seed_all_databases",
]
