"""
app/api/v1/router.py
─────────────────────────────────────────────────────────────
Aggregates all v1 sub-routers under the /api/v1 prefix.
Imported once in main.py and mounted to the FastAPI app.
"""

from fastapi import APIRouter

from app.api.v1 import (
    audit_logs,
    auth,
    events,
    inventory,
    orders,
    products,
    reviews,
    tenants,
    users,
)

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth.router)
v1_router.include_router(users.router)
v1_router.include_router(tenants.router)
v1_router.include_router(products.router)
v1_router.include_router(orders.router)
v1_router.include_router(audit_logs.router)
v1_router.include_router(inventory.router)
v1_router.include_router(reviews.router)
v1_router.include_router(events.router)
