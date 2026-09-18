"""
app/api/v2/router.py
─────────────────────────────────────────────────────────────
Aggregates all v2 sub-routers under the /api/v2 prefix.
"""

from fastapi import APIRouter

from app.api.v2 import products

v2_router = APIRouter(prefix="/api/v2")

v2_router.include_router(products.router)
