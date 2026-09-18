"""
app/api/v1/tenants.py
─────────────────────────────────────────────────────────────
Tenant management endpoints — admin only.

GET    /api/v1/tenants          →  List all tenants
POST   /api/v1/tenants          →  Create a new tenant
GET    /api/v1/tenants/{id}     →  Get tenant by ID
PATCH  /api/v1/tenants/{id}     →  Update tenant name
DELETE /api/v1/tenants/{id}     →  Delete tenant (cascades users/orders)
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.core.exceptions import ConflictError, NotFoundError
from app.db.postgres import get_db
from app.models.pg.tenant import Tenant
from app.models.pg.user import User
from app.schemas.tenant import TenantCreate, TenantRead, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get(
    "",
    response_model=list[TenantRead],
    summary="List all tenants",
    description="Returns all tenants. Admin access required.",
)
async def list_tenants(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[TenantRead]:
    result = await db.execute(select(Tenant).order_by(Tenant.created_at))
    tenants = result.scalars().all()
    return [TenantRead.model_validate(t) for t in tenants]


@router.post(
    "",
    response_model=TenantRead,
    status_code=201,
    summary="Create a tenant",
    description="Creates a new tenant. Admin access required.",
)
async def create_tenant(
    body: TenantCreate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> TenantRead:
    # ── Check name uniqueness ─────────────────────────────────
    result = await db.execute(select(Tenant).where(Tenant.name == body.name))
    if result.scalar_one_or_none():
        raise ConflictError("Tenant name")

    tenant = Tenant(id=str(uuid.uuid4()), name=body.name)
    db.add(tenant)
    await db.flush()
    return TenantRead.model_validate(tenant)


@router.get(
    "/{tenant_id}",
    response_model=TenantRead,
    summary="Get tenant by ID",
)
async def get_tenant(
    tenant_id: str,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> TenantRead:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise NotFoundError("Tenant")
    return TenantRead.model_validate(tenant)


@router.patch(
    "/{tenant_id}",
    response_model=TenantRead,
    summary="Update tenant name",
)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> TenantRead:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise NotFoundError("Tenant")

    if body.name:
        # Check uniqueness of new name
        dup = await db.execute(
            select(Tenant).where(Tenant.name == body.name, Tenant.id != tenant_id)
        )
        if dup.scalar_one_or_none():
            raise ConflictError("Tenant name")
        tenant.name = body.name

    db.add(tenant)
    await db.flush()
    return TenantRead.model_validate(tenant)


@router.delete(
    "/{tenant_id}",
    status_code=204,
    summary="Delete tenant",
    description="Deletes tenant and cascades deletion to all associated users and orders.",
)
async def delete_tenant(
    tenant_id: str,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise NotFoundError("Tenant")
    await db.delete(tenant)
    await db.flush()
