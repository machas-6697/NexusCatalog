"""
app/db/postgres.py
─────────────────────────────────────────────────────────────
Async SQLAlchemy engine + session factory for PostgreSQL.

- AsyncEngine       : long-lived connection pool
- AsyncSessionLocal : session factory used per-request
- Base              : declarative base that all ORM models inherit
- get_db()          : FastAPI dependency — yields a session and
                      commits/rolls back automatically
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ── Engines ───────────────────────────────────────────────────
# 1. Core Transactional Database (tenants, users, orders)
engine = create_async_engine(
    settings.postgres_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

# 2. Compliance & Security Audit Database (audit_logs)
audit_url = settings.postgres_url_audit or settings.postgres_url.replace("/nexuscatalog", "/nexuscatalog_audit")
engine_audit = create_async_engine(
    audit_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

# 3. Warehouse & Inventory Database (warehouses, inventory_batches)
inventory_url = settings.postgres_url_inventory or settings.postgres_url.replace("/nexuscatalog", "/nexuscatalog_inventory")
engine_inventory = create_async_engine(
    inventory_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

# ── Session factories ──────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

AsyncSessionAudit = async_sessionmaker(
    bind=engine_audit,
    class_=AsyncSession,
    expire_on_commit=False,
)

AsyncSessionInventory = async_sessionmaker(
    bind=engine_inventory,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative bases ─────────────────────────────────────────
class Base(DeclarativeBase):
    """Core PostgreSQL models inherit from this base (nexuscatalog)."""
    pass


class BaseAudit(DeclarativeBase):
    """Compliance & Audit models inherit from this base (nexuscatalog_audit)."""
    pass


class BaseInventory(DeclarativeBase):
    """Warehouse & Inventory models inherit from this base (nexuscatalog_inventory)."""
    pass


# ── FastAPI dependencies ──────────────────────────────────────
async def get_db() -> AsyncSession:
    """Yields an async session for the core transactional database."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_audit_db() -> AsyncSession:
    """Yields an async session for the compliance & audit database."""
    async with AsyncSessionAudit() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_inventory_db() -> AsyncSession:
    """Yields an async session for the warehouse & inventory database."""
    async with AsyncSessionInventory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Startup helper ────────────────────────────────────────────
async def create_all_tables() -> None:
    """
    Called once on application startup.
    Creates tables across all 3 PostgreSQL databases:
      - nexuscatalog           : Base.metadata
      - nexuscatalog_audit     : BaseAudit.metadata
      - nexuscatalog_inventory : BaseInventory.metadata
    """
    # Import models so their metadata is registered with the respective declarative base
    import app.models.pg.audit  # noqa: F401
    import app.models.pg.inventory  # noqa: F401
    import app.models.pg.order  # noqa: F401
    import app.models.pg.tenant  # noqa: F401
    import app.models.pg.user  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine_audit.begin() as conn:
        await conn.run_sync(BaseAudit.metadata.create_all)

    async with engine_inventory.begin() as conn:
        await conn.run_sync(BaseInventory.metadata.create_all)


# ── Shutdown helper ───────────────────────────────────────────
async def dispose_engine() -> None:
    """Gracefully closes all pooled connections across all 3 engines."""
    await engine.dispose()
    await engine_audit.dispose()
    await engine_inventory.dispose()
