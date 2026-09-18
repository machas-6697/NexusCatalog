"""
app/api/v1/audit_logs.py
─────────────────────────────────────────────────────────────
Compliance & Security Audit Log endpoints.
Reads from PostgreSQL database: `nexuscatalog_audit`.

Roles:
- `admin`   : Full compliance visibility
- `auditor` : Read-only auditor visibility
- `manager` : 403 Forbidden
- `buyer`   : 403 Forbidden

Keywords implemented:
- Archetype: Enterprise Compliance & Audit Engine
- Role-Based Access Control (RBAC): 4-role enforcement
- Polyglot Persistence: Dedicated audit database session
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_tenant_id, require_role
from app.db.postgres import get_audit_db
from app.models.pg.audit import AuditLog
from app.models.pg.user import User

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


class AuditLogRead(BaseModel):
    id: str
    tenant_id: str
    actor_id: str
    actor_role: str
    action: str
    resource: str
    status: str
    status_code: int
    ip_address: str | None
    details: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get(
    "",
    response_model=list[AuditLogRead],
    summary="List audit logs",
    description="Returns security audit records. Permitted for `admin` and `auditor` roles.",
)
async def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = None,
    current_user: User = Depends(require_role("admin", "auditor")),
    tenant_id: str = Depends(get_tenant_id),
    audit_db: AsyncSession = Depends(get_audit_db),
) -> list[AuditLogRead]:
    query = (
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if action:
        query = query.where(AuditLog.action == action.upper())

    result = await audit_db.execute(query)
    logs = result.scalars().all()
    return [AuditLogRead.model_validate(log) for log in logs]
