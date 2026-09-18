"""
Core cross-cutting concerns: security, dependencies, exceptions, decorators.
"""

from app.core.dependencies import get_current_user, get_tenant_id, require_role
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NexusException,
    NotFoundError,
    UnauthorizedError,
    register_exception_handlers,
)
from app.core.security import create_token, decode_token, hash_password, verify_password

__all__ = [
    "BadRequestError",
    "ConflictError",
    "ForbiddenError",
    "NexusException",
    "NotFoundError",
    "UnauthorizedError",
    "create_token",
    "decode_token",
    "get_current_user",
    "get_tenant_id",
    "hash_password",
    "register_exception_handlers",
    "require_role",
    "verify_password",
]
