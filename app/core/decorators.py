"""
app/core/decorators.py
─────────────────────────────────────────────────────────────
Custom Python Decorators implementing cross-cutting concerns.

Keywords implemented:
- Technical Primitives: Decorators
- Stack & Telemetry: Structured audit logging and execution timing
- Architecture: Multi-Tenant security tracking
"""

import functools
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import Request
from sqlalchemy import insert

from app.db.postgres import AsyncSessionAudit
from app.models.pg.audit import AuditLog

logger = logging.getLogger("nexuscatalog.decorators")


def audit_action(action: str, resource: str):
    """
    Decorator that automatically writes an immutable record to the
    `nexuscatalog_audit` PostgreSQL database upon route completion.
    Extracts tenant_id, actor_id, and actor_role from the request state.

    Usage:
        @router.post("/products")
        @audit_action(action="CREATE", resource="product")
        async def create_product(...):
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Locate Request object from args or kwargs
            request: Request | None = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            tenant_id = "unknown"
            actor_id = "system"
            actor_role = "anonymous"
            client_ip = "127.0.0.1"

            if request is not None:
                token_data = getattr(request.state, "token_data", {}) or {}
                tenant_id = token_data.get("tenant_id", "unknown")
                actor_id = token_data.get("sub", "system")
                actor_role = token_data.get("role", "anonymous")
                if request.client:
                    client_ip = request.client.host

            status = "SUCCESS"
            status_code = 200
            error_msg = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                status = "FAILED"
                status_code = getattr(exc, "status_code", 500)
                error_msg = str(exc)
                raise
            finally:
                try:
                    async with AsyncSessionAudit() as audit_session:
                        log_entry = AuditLog(
                            id=str(uuid.uuid4()),
                            tenant_id=tenant_id,
                            actor_id=actor_id,
                            actor_role=actor_role,
                            action=action,
                            resource=resource,
                            status=status,
                            status_code=status_code,
                            ip_address=client_ip,
                            details={"error": error_msg} if error_msg else {},
                            created_at=datetime.now(timezone.utc),
                        )
                        audit_session.add(log_entry)
                        await audit_session.commit()
                except Exception as audit_err:
                    logger.warning(f"Failed to persist audit log: {audit_err}")

        return wrapper
    return decorator


def timed_metric(name: str):
    """
    Decorator that logs and measures execution duration for high-value operations.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.debug(f"[METRIC] {name} executed in {duration_ms:.2f}ms")
        return wrapper
    return decorator
