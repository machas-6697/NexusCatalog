"""
REST API package — versioned HTTP endpoints (v1 full surface, v2 evolved products).
"""

from app.api.v1.router import v1_router
from app.api.v2.router import v2_router

__all__ = ["v1_router", "v2_router"]
