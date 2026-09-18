"""
app/models/pg/inventory.py
─────────────────────────────────────────────────────────────
SQLAlchemy ORM models for `warehouses` and `inventory_batches`
in the `nexuscatalog_inventory` database.

Keywords implemented:
- Archetype: Enterprise Warehouse & Inventory Engine
- Technical Primitives: ACID Transactions, Relational Foreign Keys
- Multi-Tenant: tenant_id scoped inventory
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import BaseInventory


class Warehouse(BaseInventory):
    """Physical or regional fulfillment center."""
    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_code: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    batches: Mapped[list["InventoryBatch"]] = relationship(
        "InventoryBatch", back_populates="warehouse", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Warehouse id={self.id!r} name={self.name!r} code={self.location_code!r}>"


class InventoryBatch(BaseInventory):
    """
    ACID stock batch tracking for a product SKU within a warehouse.
    Participates in atomic transaction reservations.
    """
    __tablename__ = "inventory_batches"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    warehouse_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    restock_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="batches")

    def __repr__(self) -> str:
        return (
            f"<InventoryBatch sku={self.sku!r} qty={self.quantity} "
            f"reserved={self.reserved_quantity}>"
        )
