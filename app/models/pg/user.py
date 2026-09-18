"""
app/models/pg/user.py
─────────────────────────────────────────────────────────────
SQLAlchemy ORM model for the `users` table.

Each user belongs to exactly one tenant and carries one of
four roles: admin, manager, buyer, or auditor. The password is stored as a
bcrypt hash — never in plaintext.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base

if TYPE_CHECKING:
    from app.models.pg.order import Order
    from app.models.pg.tenant import Tenant


class UserRole(str, Enum):
    """
    Enterprise Role-Based Access Control (RBAC) definitions.
    - ADMIN   : Full tenant management, user management, and all CRUD.
    - MANAGER : Catalog & inventory updates, order status management.
    - BUYER   : Catalog browsing, ordering, own profile & order history.
    - AUDITOR : Compliance and analytics read-only access (no mutations).
    """
    ADMIN = "admin"
    MANAGER = "manager"
    BUYER = "buyer"
    AUDITOR = "auditor"

    @classmethod
    def all_roles(cls) -> list[str]:
        return [r.value for r in cls]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="buyer",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")  # noqa: F821
    orders: Mapped[list["Order"]] = relationship(  # noqa: F821
        "Order", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r} role={self.role!r}>"
