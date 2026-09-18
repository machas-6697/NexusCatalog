# NexusCatalog — Architecture & Concept Reference

This document maps **every major concept** in the NexusCatalog enterprise backend to its **what, why, how, when, and where** in the codebase. Use it as proof that the system implements the full archetype you specified.

**Verification:** Run `python tests/verify_system.py` — 47 automated checks across all subsystems. Manual walkthrough: see [TESTING.md](TESTING.md).

---

## Table of Contents

1. [Archetype & Vision](#1-archetype--vision)
2. [Architecture Overview](#2-architecture-overview)
3. [Core Mechanics](#3-core-mechanics)
4. [Technical Primitives](#4-technical-primitives)
5. [API Concepts](#5-api-concepts)
6. [Stack & Telemetry](#6-stack--telemetry)
7. [The 6 Polyglot Databases](#7-the-6-polyglot-databases)
8. [4-Role RBAC Matrix](#8-4-role-rbac-matrix)
9. [Request Lifecycle (End-to-End)](#9-request-lifecycle-end-to-end)
10. [File Map by Concern](#10-file-map-by-concern)
11. [Security Hardening Applied](#11-security-hardening-applied)
12. [Concept Coverage Checklist](#12-concept-coverage-checklist)

---

## 1. Archetype & Vision

### Enterprise E-Commerce Backend, Identity & Access Engine

| Question | Answer |
|----------|--------|
| **What** | A multi-tenant backend that sells products, processes orders, tracks inventory, captures reviews, ingests telemetry, and maintains a compliance audit trail. |
| **Why** | Real e-commerce platforms need transactional integrity (orders), flexible catalogs (products with arbitrary specs), role separation (admin vs buyer vs auditor), and observability. |
| **How** | FastAPI exposes REST + GraphQL; JWT auth gates every protected route; tenant_id scopes all data access. |
| **When** | On every API call after login — identity is resolved once per request via middleware. |
| **Where** | `app/main.py` (entry), `app/api/v1/*` (REST), `app/graphql/*` (GraphQL), `app/core/*` (auth/RBAC). |

---

## 2. Architecture Overview

### Multi-Tenant, Hybrid-Database, Dual-Interface (REST + GraphQL)

```
Client (Postman / Web / GraphiQL)
        │
        ├─ REST  /api/v1  ──► Full API (10 resource groups)
        ├─ REST  /api/v2  ──► Products only (evolved price format)
        └─ GraphQL /graphql ──► Products + Reviews
                │
                ▼
    RequestNormalizationMiddleware  (X-Request-ID, latency headers)
                │
                ▼
    AuthMiddleware  (OAuth2 Bearer JWT decode → request.state.token_data)
                │
                ▼
    Route handler + Depends(get_current_user | require_role)
                │
        ┌───────┴───────┐
        ▼               ▼
  PostgreSQL (×3)   MongoDB (×3)
```

| Concept | What | Why | How | Where |
|---------|------|-----|-----|-------|
| **Multi-Tenant** | Each customer org (tenant) has isolated data | SaaS platforms serve many companies on one deployment | JWT carries `tenant_id`; every query filters by it | `app/models/pg/tenant.py`, `app/core/dependencies.py` → `get_tenant_id()` |
| **Hybrid-Database** | 3 PostgreSQL + 3 MongoDB databases | Relational for ACID; document for flexible schemas | Separate engines/clients per DB | `app/db/postgres.py`, `app/db/mongo.py` |
| **Dual-Interface** | REST and GraphQL coexist | REST for CRUD tooling; GraphQL for flexible client queries | Both mounted in `app/main.py` | `app/api/`, `app/graphql/schema.py` |
| **REST vs GraphQL** | REST = resource URLs + HTTP verbs; GraphQL = single endpoint + query language | Different client needs | REST covers full API; GraphQL covers catalog + reviews only | See [Section 5](#5-api-concepts) |

---

## 3. Core Mechanics

### Polyglot Persistence

**What:** Six specialized databases, each chosen for its domain.

**Why:** Orders need ACID guarantees; product specs need nested JSON; audit logs need append-only relational rows; events need time-series document storage.

**How:** Three async SQLAlchemy engines + one Motor client with three database handles.

**When:** At startup (`create_all_tables`, `seed_all_databases`) and on every domain-specific route call.

**Where:**

| Database | Engine | Domain | Key Files |
|----------|--------|--------|-----------|
| `nexuscatalog` (PG) | PostgreSQL | Tenants, users, orders | `app/models/pg/`, `app/api/v1/orders.py` |
| `nexuscatalog_audit` (PG) | PostgreSQL | Compliance audit trail | `app/models/pg/audit.py`, `app/api/v1/audit_logs.py` |
| `nexuscatalog_inventory` (PG) | PostgreSQL | Warehouses, stock batches | `app/models/pg/inventory.py`, `app/api/v1/inventory.py` |
| `nexuscatalog` (Mongo) | MongoDB | Product catalog | `app/models/mongo/product.py`, `app/api/v1/products.py` |
| `nexuscatalog_reviews` (Mongo) | MongoDB | Customer reviews | `app/models/mongo/review.py`, `app/api/v1/reviews.py` |
| `nexuscatalog_events` (Mongo) | MongoDB | Clickstream telemetry | `app/models/mongo/event.py`, `app/api/v1/events.py` |

Seeding: `app/db/seed.py` → `seed_all_databases()` (idempotent, runs on startup).

---

### Stateless Authentication

**What:** No server-side sessions. Each request carries a signed JWT.

**Why:** Horizontally scalable APIs don't store session state in memory.

**How:**
1. Login/register returns `access_token` (HS256 JWT).
2. Client sends `Authorization: Bearer <token>`.
3. `AuthMiddleware` decodes JWT → `request.state.token_data`.
4. `get_current_user()` loads the User row from PostgreSQL using `sub` claim.

**When:** Every protected REST route; GraphQL resolvers read the same state.

**Where:**
- Token creation: `app/core/security.py` → `create_token()`
- Middleware: `app/middleware/auth_middleware.py`
- Login/register: `app/api/v1/auth.py`
- Config: `app/config.py` (`jwt_secret`, `jwt_expiry_hours`)

JWT payload claims: `sub` (user_id), `tenant_id`, `role`, `email`, `exp`, `iat`.

---

### Role-Based Access Control (RBAC)

**What:** Four roles with distinct permissions: `admin`, `manager`, `buyer`, `auditor`.

**Why:** Enterprise systems separate operators, catalog managers, customers, and compliance auditors.

**How:** `require_role("admin", "manager")` dependency factory checks `user.role` and raises `403 Forbidden` if not allowed. GraphQL resolvers perform equivalent checks inline.

**When:** On every mutating or sensitive read endpoint.

**Where:**
- Role enum: `app/models/pg/user.py` → `UserRole`
- Guard factory: `app/core/dependencies.py` → `require_role()`
- Per-route enforcement: every file under `app/api/v1/`
- GraphQL: `app/graphql/resolvers.py`

See [Section 8](#8-4-role-rbac-matrix) for the full permission matrix.

---

### Cursor-Based Pagination

**What:** Opaque `next_cursor` tokens instead of `OFFSET/LIMIT` page numbers.

**Why:** Offset pagination degrades on large collections and can skip/duplicate rows when data changes between pages.

**How:**
1. Sort by MongoDB `_id` ascending.
2. Encode last seen `_id` as base64 → `next_cursor`.
3. Next request: decode cursor, add `{"_id": {"$gt": last_id}}` to filter.

**When:** Listing products and reviews.

**Where:**
- REST products: `app/api/v1/products.py`
- REST reviews: `app/api/v1/reviews.py`
- REST v2 products: `app/api/v2/products.py`
- GraphQL: `app/graphql/resolvers.py` → `resolve_products()`
- Response schemas: `app/schemas/product.py` → `PaginatedProductResponse`

---

### Request Normalization

**What:** Every HTTP response gets standardized tracing and security headers.

**Why:** Distributed tracing, latency monitoring, and baseline security headers without per-route boilerplate.

**How:** `RequestNormalizationMiddleware`:
- Accepts or generates `X-Request-ID`
- Measures wall time → `X-Response-Time-Ms`
- Adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`
- Stores `request.state.request_id` for downstream use

**When:** On every HTTP request, before auth middleware.

**Where:** `app/middleware/request_normalization.py`, mounted in `app/main.py`.

---

### Global Exception Handling

**What:** All errors return a consistent JSON envelope.

**Why:** Clients (Postman, frontends) can parse errors uniformly.

**How:** `NexusException` hierarchy + FastAPI exception handlers registered at startup.

**When:** On any raised application error, validation failure, or unhandled exception.

**Where:** `app/core/exceptions.py`, registered in `app/main.py`.

Error shape:
```json
{
  "status": "error",
  "code": 404,
  "message": "Product not found",
  "detail": ""
}
```

| Code | Exception Class | Meaning |
|------|-----------------|---------|
| 400 | `BadRequestError` | Invalid input |
| 401 | `UnauthorizedError` | Missing/invalid JWT |
| 403 | `ForbiddenError` | Insufficient role |
| 404 | `NotFoundError` | Resource not found |
| 409 | `ConflictError` | Duplicate resource |
| 422 | Pydantic validation | Schema validation failed |
| 500 | Unhandled | Internal error (detail hidden in production) |

---

## 4. Technical Primitives

### ACID Transactions (Relational)

**What:** Order creation writes `Order` + multiple `OrderItem` rows atomically.

**Why:** Partial orders (header without line items) would corrupt financial data.

**How:** Single SQLAlchemy async session; `get_db()` commits on success, rolls back on exception.

**When:** `POST /api/v1/orders`.

**Where:** `app/api/v1/orders.py` → `create_order()`, models in `app/models/pg/order.py`.

---

### Dynamic Schema Flexibility (Document)

**What:** MongoDB products store arbitrary `attributes` dict (e.g. `{cpu_cores: 64, gpu: "H100"}`).

**Why:** Product catalogs vary — laptops need RAM specs, clothing needs sizes; a rigid SQL schema can't cover all.

**How:** Pydantic `ProductCreate` accepts `attributes: dict`; stored as BSON subdocument.

**When:** Product create/update via REST or GraphQL.

**Where:** `app/models/mongo/product.py`, `app/api/v1/products.py`.

Reviews and events use the same pattern: `pros`/`cons` arrays, `metadata`/`properties` dicts.

---

### Decorators

**What:** Cross-cutting Python decorators for audit logging and timing.

**Why:** Avoid duplicating compliance logging in every route handler.

**How:**
- `@audit_action(action="CREATE", resource="product")` — writes to `nexuscatalog_audit` on completion
- `@timed_metric(name="...")` — logs execution duration

**When:** Applied to route handlers (available for use; wire to routes as needed).

**Where:** `app/core/decorators.py`

---

### Middleware Routing

**What:** ASGI middleware chain processes requests before route handlers.

**Why:** Auth, tracing, and CORS are cross-cutting — belong outside business logic.

**How:** Starlette `BaseHTTPMiddleware` subclasses; added in order in `app/main.py`:
1. CORS
2. RequestNormalizationMiddleware
3. AuthMiddleware

**When:** Every HTTP request.

**Where:** `app/middleware/`, `app/main.py`.

---

## 5. API Concepts

### OAuth 2.0 & Access Tokens

**What:** OAuth2 **Bearer token** scheme (Resource Owner Password flow for demo).

**Why:** Industry-standard authorization header format.

**How:** FastAPI OpenAPI declares `Bearer` security; middleware extracts `Authorization: Bearer <token>`.

**When:** After login/register; on every protected call.

**Where:** `app/middleware/auth_middleware.py`, Swagger at `/docs`.

Note: This is OAuth2-style Bearer tokens with JWT payloads, not a full OAuth2 authorization-server implementation.

---

### Authorization

**What:** After authentication (who you are), authorization decides what you can do.

**Why:** Buyers shouldn't create tenants; auditors shouldn't mutate orders.

**How:** `require_role()` on routes; inline role checks in GraphQL resolvers.

**Where:** `app/core/dependencies.py`, per-route in `app/api/v1/*`.

---

### REST vs GraphQL

| Aspect | REST | GraphQL |
|--------|------|---------|
| **Endpoints** | Many URLs (`/api/v1/products`, `/orders`, …) | One URL (`/graphql`) |
| **Operations** | GET, POST, PATCH, DELETE | `query` and `mutation` in JSON body |
| **Coverage** | Full API (auth, tenants, orders, audit, inventory, reviews, events) | Products + reviews only |
| **Versioning** | `/api/v1`, `/api/v2` | Single schema |
| **Docs** | Swagger `/docs` | GraphiQL `/graphql` |
| **Auth** | Middleware + Depends | Same JWT via HTTP Headers panel |

**Why both:** REST integrates with standard HTTP tools; GraphQL lets clients fetch exactly the fields they need for catalog UIs.

**Where:** REST → `app/api/`; GraphQL → `app/graphql/schema.py`.

GraphQL still uses HTTP POST — seeing GET/POST on REST does not conflict with GraphQL.

---

### OpenAPI

**What:** Machine-readable API specification auto-generated from FastAPI route definitions.

**Why:** Powers Swagger UI; enables client code generation.

**How:** FastAPI introspects route decorators, Pydantic schemas, and response models.

**When:** Available at runtime.

**Where:** `GET /openapi.json`, interactive UI at `/docs` and `/redoc`.

---

### API Versioning

**What:** URL-path versioning (`/api/v1`, `/api/v2`).

**Why:** Evolve response shapes without breaking existing clients.

**How:** v2 products return `price` as string `"99.99"` instead of float `99.99`; same MongoDB data, different serialization layer.

**When:** Clients choose version by URL prefix.

**Where:**
- v1 router: `app/api/v1/router.py`
- v2 router: `app/api/v2/router.py` (products read-only)
- v2 schema: `app/schemas/product.py` → `ProductReadV2`

---

### Endpoint Pagination

**What:** Cursor-based pagination on list endpoints (products, reviews).

**Why:** Stable performance on large catalogs.

**How:** Query params `?limit=20&cursor=<base64>` → response includes `next_cursor`.

**Where:** See [Cursor-Based Pagination](#cursor-based-pagination) above.

---

### Error Handling

**What:** Structured error responses for all failure modes.

**Why:** Predictable client error handling.

**Where:** `app/core/exceptions.py` — see [Global Exception Handling](#global-exception-handling).

---

## 6. Stack & Telemetry

| Technology | Role | Where |
|------------|------|-------|
| **Python 3.12** | Runtime | `requirements.txt` |
| **FastAPI** | ASGI web framework | `app/main.py` |
| **Strawberry GraphQL** | GraphQL schema + GraphiQL | `app/graphql/` |
| **PostgreSQL + asyncpg** | 3 relational databases | `app/db/postgres.py` |
| **MongoDB + Motor** | 3 document databases | `app/db/mongo.py` |
| **JWT (PyJWT)** | Stateless tokens | `app/core/security.py` |
| **bcrypt** | Password hashing | `app/core/security.py` |
| **Pydantic Settings** | Config from `.env` | `app/config.py` |
| **Swagger UI** | REST documentation | `/docs` (auto) |
| **Prometheus Instrumentator** | HTTP metrics | `app/main.py` → `/metrics` |
| **Grafana** | Dashboards (external) | Docker `MACHAGRAFANA` port 2500 |
| **Docker** | Infrastructure containers | PostgreSQL, MongoDB, Prometheus, Grafana |

### Prometheus Instrumentation

**What:** Exposes request counts, durations, and process metrics.

**Why:** Production observability and SLA monitoring.

**How:** `prometheus_fastapi_instrumentator.Instrumentator().instrument(app).expose(app, endpoint="/metrics")`.

**When:** Continuously while app runs.

**Where:** `app/main.py` line ~143; scraped by Prometheus container on port 9000.

---

## 7. The 6 Polyglot Databases

| # | Name | Type | Tables/Collections | Seeded Data |
|---|------|------|-------------------|-------------|
| 1 | `nexuscatalog` | PostgreSQL | tenants, users, orders, order_items | Demo Corp + 3 tenants, 4-role users, sample orders |
| 2 | `nexuscatalog_audit` | PostgreSQL | audit_logs | Security/compliance events |
| 3 | `nexuscatalog_inventory` | PostgreSQL | warehouses, inventory_batches | Regional hubs, SKU batches |
| 4 | `nexuscatalog` | MongoDB | products | Catalog with dynamic attributes |
| 5 | `nexuscatalog_reviews` | MongoDB | reviews | Ratings, pros/cons, metadata |
| 6 | `nexuscatalog_events` | MongoDB | events | page_view, checkout_start, etc. |

Startup creates PG tables (`create_all_tables`) and seeds all six (`seed_all_databases`) idempotently.

---

## 8. 4-Role RBAC Matrix

Enforced in REST via `require_role()` and in GraphQL via resolver checks.

| Resource / Action | Admin | Manager | Buyer | Auditor |
|:---|:---:|:---:|:---:|:---:|
| Auth & Profile | Yes | Yes | Yes | Yes |
| Tenant CRUD | Full | Blocked | Blocked | Blocked |
| Create/Edit Products | Yes | Yes | Blocked | Blocked |
| Place Orders | Yes | Yes | Yes | **Blocked** |
| View Own Orders | Yes | Yes | Yes | Yes |
| View All Tenant Orders | Yes | Yes | Blocked | Read-only |
| Update Order Status | Yes | Yes | Blocked | Blocked |
| Audit Logs | Read | Blocked | Blocked | Read |
| Warehouses | Full CRUD | Read | Blocked | Read |
| Stock Batches | Yes | Yes | Blocked | Read |
| Submit Reviews | Yes | Yes | Yes | Blocked |
| Ingest Events | Yes | Yes | Yes | **Blocked** |
| Query Events | Yes | Read | Blocked | Read |

Demo credentials (seeded): see README → Auto-Seeded Demo Credentials.

---

## 9. Request Lifecycle (End-to-End)

Example: **Buyer places an order**

1. **Client** → `POST /api/v1/orders` with `Authorization: Bearer <jwt>` and order JSON body.
2. **CORS middleware** → passes through (or handles preflight).
3. **RequestNormalizationMiddleware** → assigns `X-Request-ID`, starts timer.
4. **AuthMiddleware** → decodes JWT, sets `request.state.token_data = {sub, tenant_id, role, email}`.
5. **FastAPI routing** → matches `create_order` in `app/api/v1/orders.py`.
6. **Dependencies** → `require_role("admin","manager","buyer")` passes; `get_tenant_id()` extracts tenant; `get_db()` opens PG session.
7. **Handler** → creates `Order` + `OrderItem` rows, calculates total, commits.
8. **Response** → `201` with `OrderRead` JSON; middleware adds `X-Request-ID`, `X-Response-Time-Ms`.
9. **Prometheus** → increments `http_requests_total`, records duration histogram.

---

## 10. File Map by Concern

```
NexusCatalog/
├── app/
│   ├── main.py              Entry point, middleware, routers, metrics
│   ├── config.py            Pydantic Settings (.env)
│   ├── core/
│   │   ├── security.py      JWT + bcrypt
│   │   ├── dependencies.py  get_current_user, require_role, get_tenant_id
│   │   ├── exceptions.py    NexusException + global handlers
│   │   └── decorators.py    @audit_action, @timed_metric
│   ├── middleware/
│   │   ├── auth_middleware.py       OAuth2 Bearer JWT
│   │   └── request_normalization.py Tracing + security headers
│   ├── db/
│   │   ├── postgres.py      3 async PG engines
│   │   ├── mongo.py         3 MongoDB handles
│   │   └── seed.py          6-database idempotent seeding
│   ├── models/
│   │   ├── pg/              SQLAlchemy ORM (tenant, user, order, audit, inventory)
│   │   └── mongo/           Pydantic documents (product, review, event)
│   ├── schemas/             REST request/response DTOs
│   ├── api/
│   │   ├── v1/              Full REST surface (10 modules)
│   │   └── v2/              Products with string price
│   └── graphql/
│       ├── schema.py        Query + Mutation roots
│       ├── types.py         Strawberry types
│       └── resolvers.py     Tenant-scoped logic + RBAC
├── tests/
│   └── verify_system.py     47-check enterprise verification suite
├── Details.md               This document
├── TESTING.md               Manual testing guide
├── README.md                Quick start + RBAC matrix
└── requirements.txt         Python dependencies
```

---

## 11. Security Hardening Applied

| Issue | Fix | File |
|-------|-----|------|
| Admin self-registration via public `/register` | Registration restricted to `buyer` role only | `app/api/v1/auth.py` |
| Login timing side-channel | Always run bcrypt compare (dummy hash when user missing) | `app/api/v1/auth.py`, `app/core/security.py` |
| Internal error leakage (500) | Hide exception detail when `APP_ENV != development` | `app/core/exceptions.py` |
| JWT error detail leakage | Generic message in production | `app/middleware/auth_middleware.py` |
| CORS misconfiguration (`*` + credentials) | `allow_credentials=False` with wildcard origins | `app/main.py` |
| Weak/missing password policy | Minimum 8 characters on registration | `app/schemas/auth.py` |
| Email missing from JWT (GraphQL reviews) | `email` claim added to token payload | `app/core/security.py` |
| Auditor placing orders / ingesting events | RBAC guards on `POST /orders` and `POST /events` | `app/api/v1/orders.py`, `app/api/v1/events.py` |
| Secrets in repo | `.gitignore` excludes `.env`; `.env.example` uses placeholders | `.gitignore`, `.env.example` |

---

## 12. Concept Coverage Checklist

Use this to confirm every concept you specified is implemented:

| Concept | Implemented | Proof |
|---------|:-----------:|-------|
| Enterprise E-Commerce Backend | ✅ | Orders, products, inventory, reviews |
| Identity & Access Engine | ✅ | JWT auth, 4-role RBAC, `/users/me` |
| Multi-Tenant | ✅ | `tenant_id` on all models + JWT claim |
| Hybrid-Database | ✅ | 3 PG + 3 Mongo |
| Dual-Interface (REST + GraphQL) | ✅ | `/api/v1`, `/api/v2`, `/graphql` |
| Polyglot Persistence | ✅ | 6 databases, domain-matched engines |
| Stateless Authentication | ✅ | JWT, no server sessions |
| RBAC | ✅ | `require_role()`, 4 roles, matrix in README |
| Cursor-Based Pagination | ✅ | Products + reviews, base64 cursors |
| Request Normalization | ✅ | `RequestNormalizationMiddleware` |
| Global Exception Handling | ✅ | `NexusException` + handlers |
| ACID Transactions | ✅ | Order + OrderItems single commit |
| Dynamic Schema Flexibility | ✅ | MongoDB `attributes`, `properties` |
| Decorators | ✅ | `@audit_action`, `@timed_metric` |
| Middleware Routing | ✅ | CORS → Normalization → Auth chain |
| OAuth 2.0 Bearer | ✅ | `Authorization: Bearer` extraction |
| Access Tokens | ✅ | JWT `access_token` on login/register |
| Authorization | ✅ | Role guards on every sensitive route |
| REST vs GraphQL | ✅ | Both mounted; different coverage |
| OpenAPI | ✅ | `/openapi.json`, `/docs` |
| API Versioning | ✅ | v1 full, v2 product price format |
| Endpoint Pagination | ✅ | Cursor params on list endpoints |
| Error Handling | ✅ | Consistent JSON error envelope |
| Python / FastAPI | ✅ | `app/main.py`, async throughout |
| PostgreSQL | ✅ | 3 relational databases |
| MongoDB | ✅ | 3 document databases |
| JWT | ✅ | PyJWT HS256 |
| Swagger UI | ✅ | `/docs` |
| Prometheus | ✅ | `/metrics` |
| Grafana | ✅ | Docker container, README setup |
| Dockerized Infrastructure | ✅ | MACHAPOSTGRES, MACHAMONGO, etc. |

**Automated proof:** `python tests/verify_system.py` → `ALL 47 VERIFICATION CHECKS PASSED`

**Manual proof:** Follow [TESTING.md](TESTING.md) phases 1–12.

---

*NexusCatalog v2.0.0 — Enterprise Multi-Tenant E-Commerce Backend*
