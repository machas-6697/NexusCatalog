"""
app/models/pg/audit.py
─────────────────────────────────────────────────────────────
SQLAlchemy ORM model for `audit_logs` in the `nexuscatalog_audit` database.

Keywords implemented:
- Archetype: Enterprise Compliance & Audit Engine
- Technical Primitives: Relational ACID storage, Immutable Audit Trail
- Multi-Tenant: tenant_id scoped logging
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import BaseAudit


class AuditLog(BaseAudit):
    """
    Tamper-evident audit ledger tracking all critical mutations,
    security checks, authentication events, and administrative actions.
    Stored in a dedicated PostgreSQL database: `nexuscatalog_audit`.
    """
    __tablename__ = "audit_logs"

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
    actor_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    actor_role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    resource: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="SUCCESS",
    )
    status_code: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=200,
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=True,
        default="127.0.0.1",
    )
    details: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id!r} action={self.action!r} actor={self.actor_id!r}>"
