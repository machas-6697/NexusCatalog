"""
app/api/v1/inventory.py
─────────────────────────────────────────────────────────────
Warehouse & Stock Batch Inventory endpoints.
Reads/writes PostgreSQL database: `nexuscatalog_inventory`.

Roles:
- `admin`   : Full inventory & warehouse CRUD
- `manager` : Create/update inventory batches & view warehouses
- `auditor` : Read-only stock audit
- `buyer`   : 403 Forbidden

Keywords implemented:
- Archetype: Enterprise Warehouse & Inventory Engine
- Technical Primitives: Relational ACID Transactions
- Multi-Tenant: tenant_id scoped warehouses and batches
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_tenant_id, require_role
from app.core.exceptions import NotFoundError
from app.db.postgres import get_inventory_db
from app.models.pg.inventory import InventoryBatch, Warehouse
from app.models.pg.user import User

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ── Pydantic Schemas ──────────────────────────────────────────

class WarehouseCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    location_code: str = Field(..., min_length=2, max_length=50)


class WarehouseRead(BaseModel):
    id: str
    tenant_id: str
    name: str
    location_code: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchCreate(BaseModel):
    warehouse_id: str
    product_id: str
    sku: str
    quantity: int = Field(..., ge=0)
    reserved_quantity: int = Field(default=0, ge=0)


class BatchRead(BaseModel):
    id: str
    warehouse_id: str
    product_id: str
    sku: str
    quantity: int
    reserved_quantity: int
    restock_date: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Warehouse Endpoints ───────────────────────────────────────

@router.get(
    "/warehouses",
    response_model=list[WarehouseRead],
    summary="List warehouses",
    description="Returns warehouses for tenant. Permitted for admin, manager, auditor.",
)
async def list_warehouses(
    current_user: User = Depends(require_role("admin", "manager", "auditor")),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_inventory_db),
) -> list[WarehouseRead]:
    result = await db.execute(
        select(Warehouse)
        .where(Warehouse.tenant_id == tenant_id)
        .order_by(Warehouse.created_at)
    )
    warehouses = result.scalars().all()
    return [WarehouseRead.model_validate(w) for w in warehouses]


@router.post(
    "/warehouses",
    response_model=WarehouseRead,
    status_code=201,
    summary="Create a warehouse",
    description="Provisions a new fulfillment center. Permitted for admin only.",
)
async def create_warehouse(
    body: WarehouseCreate,
    current_user: User = Depends(require_role("admin")),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_inventory_db),
) -> WarehouseRead:
    warehouse = Warehouse(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=body.name,
        location_code=body.location_code,
        is_active=True,
    )
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return WarehouseRead.model_validate(warehouse)


# ── Inventory Batch Endpoints ─────────────────────────────────

@router.get(
    "/batches",
    response_model=list[BatchRead],
    summary="List inventory batches",
    description="Returns inventory batches. Permitted for admin, manager, auditor.",
)
async def list_batches(
    product_id: str | None = None,
    warehouse_id: str | None = None,
    current_user: User = Depends(require_role("admin", "manager", "auditor")),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_inventory_db),
) -> list[BatchRead]:
    query = (
        select(InventoryBatch)
        .join(Warehouse, InventoryBatch.warehouse_id == Warehouse.id)
        .where(Warehouse.tenant_id == tenant_id)
        .order_by(InventoryBatch.updated_at.desc())
    )
    if product_id:
        query = query.where(InventoryBatch.product_id == product_id)
    if warehouse_id:
        query = query.where(InventoryBatch.warehouse_id == warehouse_id)

    result = await db.execute(query)
    batches = result.scalars().all()
    return [BatchRead.model_validate(b) for b in batches]


@router.post(
    "/batches",
    response_model=BatchRead,
    status_code=201,
    summary="Restock or create inventory batch",
    description="Provisions stock batch in warehouse. Permitted for admin and manager.",
)
async def create_batch(
    body: BatchCreate,
    current_user: User = Depends(require_role("admin", "manager")),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_inventory_db),
) -> BatchRead:
    # Verify warehouse belongs to tenant
    res = await db.execute(
        select(Warehouse).where(
            Warehouse.id == body.warehouse_id,
            Warehouse.tenant_id == tenant_id,
        )
    )
    if not res.scalar_one_or_none():
        raise NotFoundError("Warehouse")

    batch = InventoryBatch(
        id=str(uuid.uuid4()),
        warehouse_id=body.warehouse_id,
        product_id=body.product_id,
        sku=body.sku,
        quantity=body.quantity,
        reserved_quantity=body.reserved_quantity,
        restock_date=datetime.now(timezone.utc),
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return BatchRead.model_validate(batch)
