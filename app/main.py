"""
app/main.py
─────────────────────────────────────────────────────────────
NexusCatalog FastAPI application entry point.

Startup sequence:
  1. Create PostgreSQL tables (idempotent — skips existing)
  2. Seed demo tenant + admin + buyer users (if not already present)
  3. Mount AuthMiddleware (intercepts all requests)
  4. Register global exception handlers
  5. Mount REST routers (v1 + v2)
  6. Mount GraphQL router at /graphql
  7. Mount Prometheus /metrics instrumentation

Run with:
  uvicorn app.main:app --reload --port 8000
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select

from app.api.v1.router import v1_router
from app.api.v2.router import v2_router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.security import hash_password
from app.db.seed import seed_all_databases
from app.db.mongo import close_mongo, get_mongo_client, get_mongo_db, get_reviews_db, get_events_db
from app.db.postgres import create_all_tables, dispose_engine
from app.graphql.schema import graphql_app
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.request_normalization import RequestNormalizationMiddleware

# ── Imports needed for SQLAlchemy to discover all models ─────
from app.models.pg import tenant, user, order, audit, inventory  # noqa: F401


# ── Lifespan (startup + shutdown) ─────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ───────────────────────────────────────────────
    print("[NexusCatalog] Starting up...")

    # 1. Ensure PostgreSQL tables exist across all 3 databases
    try:
        await create_all_tables()
        print("[OK] PostgreSQL tables ready across all 3 databases (nexuscatalog, nexuscatalog_audit, nexuscatalog_inventory)")
    except Exception as exc:
        print("\n" + "=" * 65)
        print("[ERROR] Failed to connect to PostgreSQL at port 5400!")
        print(f"Details: {exc}")
        print("Run: docker start MACHAPOSTGRES")
        print("=" * 65 + "\n")
        raise exc

    # 2. Seed demo data across all 6 polyglot databases
    try:
        await seed_all_databases()
        print("[OK] All 6 Polyglot Databases seeded with demo records")
    except Exception as exc:
        print(f"[WARN] Database seeding note: {exc}")

    # 3. Warm up MongoDB connections across all 3 databases
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        # Touch all 3 DBs
        await get_mongo_db().command("ping")
        await get_reviews_db().command("ping")
        await get_events_db().command("ping")
        print("[OK] MongoDB connections established across 3 databases (nexuscatalog, nexuscatalog_reviews, nexuscatalog_events)")
    except Exception as exc:
        print("\n" + "=" * 65)
        print("[ERROR] Failed to connect to MongoDB at port 27000!")
        print(f"Details: {exc}")
        print("Run: docker start MACHAMONGO")
        print("=" * 65 + "\n")
        raise exc

    print(f"[OK] App running at http://localhost:{settings.app_port}")
    print(f"[>>] Swagger UI  -> http://localhost:{settings.app_port}/docs")
    print(f"[>>] GraphQL     -> http://localhost:{settings.app_port}/graphql")
    print(f"[>>] Metrics     -> http://localhost:{settings.app_port}/metrics")

    yield  # App is now running and serving requests

    # ── SHUTDOWN ──────────────────────────────────────────────
    print("[NexusCatalog] Shutting down...")
    await dispose_engine()
    await close_mongo()
    print("[OK] Database connections closed")


# ── FastAPI application ───────────────────────────────────────

app = FastAPI(
    title="NexusCatalog API",
    description=(
        "Enterprise E-Commerce Backend & Identity & Access Engine. "
        "Multi-Tenant, Hybrid-Database (6 Polyglot Databases: 3 PostgreSQL + 3 MongoDB). "
        "Dual-Interface (REST v1/v2 + Strawberry GraphQL) with 4-Role RBAC (Admin, Manager, Buyer, Auditor). "
        "Prometheus Telemetry, Request Normalization, and Global Exception Handling."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Normalization & Tracing Middleware ────────────────
app.add_middleware(RequestNormalizationMiddleware)

# ── Auth middleware (Stateless JWT RBAC) ──────────────────────
app.add_middleware(AuthMiddleware)

# ── Global exception handlers ─────────────────────────────────
register_exception_handlers(app)

# ── REST routers ──────────────────────────────────────────────
app.include_router(v1_router)
app.include_router(v2_router)

# ── GraphQL ───────────────────────────────────────────────────
app.include_router(graphql_app, prefix="/graphql")

# ── Prometheus metrics ────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# ── Health check ──────────────────────────────────────────────
@app.get("/", tags=["Health"], summary="Health check")
async def health_check():
    return {
        "status": "ok",
        "service": "NexusCatalog API",
        "version": "2.0.0",
        "docs": "/docs",
        "graphql": "/graphql",
        "metrics": "/metrics",
    }
