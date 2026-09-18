"""
REST API v1 — full enterprise surface (auth, tenants, products, orders, audit, inventory, reviews, events).
"""

from app.api.v1.router import v1_router

__all__ = ["v1_router"]
