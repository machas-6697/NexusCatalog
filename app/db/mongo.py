"""
app/db/mongo.py
─────────────────────────────────────────────────────────────
Motor async MongoDB client for NexusCatalog.

- get_mongo_client() : returns the shared Motor client
- get_mongo_db()     : returns the `nexuscatalog` database handle
- get_collection()   : convenience helper to fetch a named collection
- close_mongo()      : graceful shutdown
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.config import settings

# ── Shared client (module-level singleton) ────────────────────
_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    """Returns the shared Motor client, creating it if not yet initialised."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_url)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Returns the core catalog MongoDB database handle (nexuscatalog)."""
    return get_mongo_client()[settings.mongo_db_name]


def get_reviews_db() -> AsyncIOMotorDatabase:
    """Returns the customer reviews & ratings database handle (nexuscatalog_reviews)."""
    return get_mongo_client()[settings.mongo_db_reviews]


def get_events_db() -> AsyncIOMotorDatabase:
    """Returns the clickstream & telemetry events database handle (nexuscatalog_events)."""
    return get_mongo_client()[settings.mongo_db_events]


def get_collection(name: str) -> AsyncIOMotorCollection:
    """Convenience helper to fetch a collection from the core catalog database."""
    return get_mongo_db()[name]


def get_reviews_collection(name: str = "reviews") -> AsyncIOMotorCollection:
    """Convenience helper to fetch the reviews collection from nexuscatalog_reviews."""
    return get_reviews_db()[name]


def get_events_collection(name: str = "events") -> AsyncIOMotorCollection:
    """Convenience helper to fetch the events collection from nexuscatalog_events."""
    return get_events_db()[name]


async def close_mongo() -> None:
    """Closes the Motor client connection pool on app shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
