# NexusCatalog Enterprise Engine (v2.0.0)

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Strawberry GraphQL](https://img.shields.io/badge/GraphQL-Strawberry-e535ab.svg)](https://strawberry.rocks)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-AsyncPG%20%283%20DBs%29-336791.svg)](https://www.postgresql.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor%20%283%20DBs%29-47A248.svg)](https://www.mongodb.com/)
[![Tests](https://img.shields.io/badge/Verification-47%2F47%20Passed-brightgreen.svg)](tests/verify_system.py)

Multi-Tenant E-Commerce Backend & Identity Access Engine built with **FastAPI**, **Strawberry GraphQL**, and a **6-Database Polyglot Persistence Architecture**.

---

## Architecture Overview

NexusCatalog delivers a multi-tenant, e-commerce platform featuring:
- **Dual-Interface API**: First-class REST (`/api/v1`, `/api/v2`) and interactive Strawberry GraphQL (`/graphql`).
- **6-Database Polyglot Persistence**: 3 isolated PostgreSQL relational databases + 3 MongoDB document databases.
- **4-Role Access Control (RBAC)**: Fine-grained authorization enforcing roles: `admin`, `manager`, `buyer`, and `auditor`.
- **Stateless JWT Authentication**: OAuth2 Bearer scheme with automatic tenant scoping and context injection.
- **Request Normalization & Tracing**: Correlation ID tracking (`X-Request-ID`), header sanitization, and sub-millisecond latency monitoring (`X-Process-Time-Ms`).
- **Enterprise Decorators**: `@audit_action` for automated compliance logging and `@measure_latency` for real-time profiling.
- **Cursor-Based Pagination**: Stable, performant cursor pagination preventing offset drift across large catalogs.
- **Real-Time Telemetry**: Prometheus metric instrumentation (`/metrics`) and Grafana analytics dashboards.

```
                            ┌─────────────────────────────────────────┐
                            │          Client Applications            │
                            │   (Postman, Web Apps, GraphQL IDE)      │
                            └────────────────────┬────────────────────┘
                                                 │
                               ┌─────────────────┴─────────────────┐
                               ▼                                   ▼
                    REST API (/api/v1, /api/v2)           GraphQL (/graphql)
                               │                                   │
                               └─────────────────┬─────────────────┘
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │    Request Normalization Middleware     │
                            │   (X-Request-ID, Latency Profiler)      │
                            └────────────────────┬────────────────────┘
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │     Stateless JWT Auth & 4-Role RBAC    │
                            │  [Admin]    [Manager]  [Buyer] [Auditor]│
                            └────────────────────┬────────────────────┘
                                                 │
            ┌────────────────────────────────────┴────────────────────────────────────┐
            ▼                                                                         ▼
┌──────────────────────────────────────┐                  ┌──────────────────────────────────────┐
│       PostgreSQL (3 Relational DBs)  │                  │        MongoDB (3 Document DBs)      │
├──────────────────────────────────────┤                  ├──────────────────────────────────────┤
│ 1. nexuscatalog                      │                  │ 1. nexuscatalog                      │
│    • Tenants, Users, Orders, Items   │                  │    • Products, Dynamic BSON Specs    │
│ 2. nexuscatalog_audit                │                  │ 2. nexuscatalog_reviews              │
│    • Compliance logs, Security trail │                  │    • Customer Ratings, Pros & Cons   │
│ 3. nexuscatalog_inventory            │                  │ 3. nexuscatalog_events               │
│    • Warehouses, SKU Batches, Stock  │                  │    • Telemetry, Clickstream Events   │
└──────────────────────────────────────┘                  └──────────────────────────────────────┘
```

---

## The 6 Polyglot Databases

NexusCatalog utilizes polyglot persistence to match each domain with the ideal database engine:

| Database Name | Engine | Schema Type | Domain & Responsibility |
|:---|:---|:---|:---|
| **`nexuscatalog`** | PostgreSQL | Relational (ACID) | Core enterprise entities: Tenants, User accounts, Orders, Order Items, and transactional state. |
| **`nexuscatalog_audit`** | PostgreSQL | Relational (Append-only) | Immutable regulatory and compliance audit trail: user actions, target resources, timestamps, and IP addresses. |
| **`nexuscatalog_inventory`**| PostgreSQL | Relational (ACID) | Multi-warehouse inventory: Regional logistics hubs, stock batches, SKU tracking, and reorder levels. |
| **`nexuscatalog`** | MongoDB | Document (Polymorphic) | Dynamic product catalog: Arbitrary nested attributes, tech specs, categories, and cursor-paginated indexes. |
| **`nexuscatalog_reviews`** | MongoDB | Document (Flexible) | Verified customer feedback: 1–5 star ratings, sentiment flags, verified purchase tags, and dynamic pros/cons arrays. |
| **`nexuscatalog_events`** | MongoDB | Document (Time-series) | Real-time clickstream telemetry: `page_view`, `product_view`, `checkout_start`, metadata payloads, and user sessions. |

---

## 4-Role RBAC Authorization Matrix

Permissions are strictly validated across both REST dependencies (`require_role`) and GraphQL resolvers:

| Resource / Action | Admin | Manager | Buyer | Auditor |
|:---|:---:|:---:|:---:|:---:|
| **Authentication & Profile (`/auth`, `/users/me`)** | Yes | Yes | Yes | Yes |
| **Tenant Management (`/api/v1/tenants`)** | Full CRUD | Blocked (403) | Blocked (403) | Blocked (403) |
| **Create / Edit Products (REST & GraphQL)** | Yes | Yes | Blocked (403) | Blocked (403) |
| **Place Orders (`POST /api/v1/orders`)** | Yes | Yes | Yes | Blocked (403) |
| **View Own Orders (`GET /api/v1/orders/mine`)** | Yes | Yes | Yes | Yes |
| **Inspect All Tenant Orders (`GET /api/v1/orders`)** | Yes | Yes | Blocked (403) | Yes (Read-Only) |
| **Update Order Status (`PATCH /api/v1/orders/{id}`)** | Yes | Yes | Blocked (403) | Blocked (403) |
| **Compliance Audit Trail (`/api/v1/audit-logs`)** | Full Read | Blocked (403) | Blocked (403) | Full Read |
| **Warehouse Management (`/inventory/warehouses`)** | Full CRUD | Read-Only | Blocked (403) | Read-Only |
| **Stock Batch Restocking (`/inventory/batches`)** | Yes | Yes | Blocked (403) | Read-Only |
| **Submit Product Review (`POST /api/v1/reviews`)** | Yes | Yes | Yes | Blocked (403) |
| **Ingest Telemetry Events (`POST /api/v1/events`)** | Yes | Yes | Yes | Blocked (403) |
| **Query Telemetry Events (`GET /api/v1/events`)** | Yes | Read-Only | Blocked (403) | Full Read |

---

## Auto-Seeded Demo Credentials

On startup, NexusCatalog seeds demo records across **all 6 databases**, including active accounts for all 4 roles:

| Role | Email | Password | Primary Purpose |
|:---|:---|:---|:---|
| **Admin** | `admin@nexuscatalog.io` | `Admin@1234` | Full system governance, tenant management, warehouse creation |
| **Manager** | `manager@nexuscatalog.io` | `Manager@1234` | Catalog authoring, inventory restocking, order fulfillment |
| **Buyer** | `buyer@nexuscatalog.io` | `Buyer@1234` | Catalog browsing, purchasing (ACID orders), product reviews |
| **Auditor** | `auditor@nexuscatalog.io` | `Auditor@1234` | Compliance inspection, audit log verification, telemetry analysis |

---

## Quick Start & Installation

### 1. Verify Prerequisites (Docker Containers)

Ensure Docker containers are running:
```powershell
docker start MACHAPOSTGRES MACHAMONGO MACHAREDIS MACHAPROMETHEUS MACHAGRAFANA
```

Verify status:
```powershell
docker ps
```

### 2. One-Time PostgreSQL Database Initialization

PostgreSQL requires creating the 3 distinct relational databases. Run this **once**:

```powershell
docker exec -it MACHAPOSTGRES psql -U postgres -c "CREATE DATABASE nexuscatalog;"
docker exec -it MACHAPOSTGRES psql -U postgres -c "CREATE DATABASE nexuscatalog_audit;"
docker exec -it MACHAPOSTGRES psql -U postgres -c "CREATE DATABASE nexuscatalog_inventory;"
```

> **Note:** MongoDB automatically creates its 3 databases (`nexuscatalog`, `nexuscatalog_reviews`, `nexuscatalog_events`) on first document insertion.

### 3. Install Dependencies

```powershell
cd c:\MY-SPACE\NexusCatalog
pip install -r requirements.txt
```

### 4. Run the Server

```powershell
uvicorn app.main:app --reload --port 8000
```

On startup, NexusCatalog will:
1. Initialize tables across all 3 PostgreSQL databases (`nexuscatalog`, `nexuscatalog_audit`, `nexuscatalog_inventory`).
2. Establish connections to all 3 MongoDB databases.
3. Automatically seed demo data across all 6 databases.
4. Mount Request Normalization, RBAC Auth middleware, REST v1/v2 routers, Strawberry GraphQL, and Prometheus metrics.

---

## Interactive Interfaces

| Interface | URL | Purpose |
|:---|:---|:---|
| **Swagger UI** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive REST API explorer with OpenAPI 3.1 schema. |
| **ReDoc** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Clean, searchable REST API documentation. |
| **Strawberry GraphQL IDE** | [http://localhost:8000/graphql](http://localhost:8000/graphql) | Interactive GraphiQL playground for queries & mutations. |
| **Prometheus Telemetry** | [http://localhost:8000/metrics](http://localhost:8000/metrics) | Live Prometheus metrics endpoint (scraped every 5s). |
| **Grafana Dashboard** | [http://localhost:2500](http://localhost:2500) | Observability dashboards (`admin` / `grafdok697!`). |

---

## Complete API Route Reference

### 1. Authentication (`/api/v1/auth`) — Public
- `POST /api/v1/auth/register`: Register new user (returns JWT).
- `POST /api/v1/auth/login`: Authenticate credentials (returns JWT + role).

### 2. User Profiles (`/api/v1/users`) — Authenticated
- `GET /api/v1/users/me`: Return current user profile, assigned role, and tenant ID.
- `PATCH /api/v1/users/me`: Update email or password.

### 3. Multi-Tenant Engine (`/api/v1/tenants`) — Admin Only
- `GET /api/v1/tenants`: List all tenants.
- `POST /api/v1/tenants`: Create new isolated tenant.
- `GET /api/v1/tenants/{id}`: Retrieve tenant details.
- `PATCH /api/v1/tenants/{id}`: Update tenant configuration.
- `DELETE /api/v1/tenants/{id}`: Delete tenant and cascading users.

### 4. MongoDB Product Catalog (`/api/v1/products` & `/api/v2/products`)
- `GET /api/v1/products`: Cursor-paginated catalog (`?limit=10&cursor=...&category=...`).
- `POST /api/v1/products`: Create product with arbitrary BSON specs (*Admin / Manager*).
- `GET /api/v1/products/{id}`: Get single product with full specs.
- `PATCH /api/v1/products/{id}`: Partial update (*Admin / Manager*).
- `DELETE /api/v1/products/{id}`: Remove product (*Admin / Manager*).
- `GET /api/v2/products`: REST v2 backward-compatible catalog (prices translated to decimal strings e.g. `"479.99"`).

### 5. PostgreSQL ACID Orders (`/api/v1/orders`)
- `POST /api/v1/orders`: Place transactional multi-item order (*Buyer / Manager / Admin*).
- `GET /api/v1/orders/mine`: List personal orders.
- `GET /api/v1/orders`: List all tenant orders (*Admin / Manager / Auditor*).
- `GET /api/v1/orders/{id}`: Retrieve order details.
- `PATCH /api/v1/orders/{id}`: Transition status: `pending` → `confirmed` → `shipped` → `delivered` (*Admin / Manager*).

### 6. Compliance Audit Trail (`/api/v1/audit-logs`) — PG DB 2
- `GET /api/v1/audit-logs`: Inspect immutable audit records (*Admin / Auditor*).
- `GET /api/v1/audit-logs/actions`: List unique audit actions.

### 7. Warehouses & Inventory (`/api/v1/inventory`) — PG DB 3
- `GET /api/v1/inventory/warehouses`: List regional distribution warehouses.
- `POST /api/v1/inventory/warehouses`: Provision new warehouse (*Admin*).
- `GET /api/v1/inventory/batches`: Query SKU batches across warehouses.
- `POST /api/v1/inventory/batches`: Restock inventory batch (*Admin / Manager*).

### 8. Product Reviews & Sentiment (`/api/v1/reviews`) — Mongo DB 2
- `GET /api/v1/reviews`: List reviews for product with aggregate rating metrics.
- `POST /api/v1/reviews`: Submit verified review with dynamic pros/cons (*Buyer / Manager / Admin*).

### 9. Real-Time Telemetry Events (`/api/v1/events`) — Mongo DB 3
- `POST /api/v1/events`: Ingest clickstream/audit telemetry event (*Buyer / Manager / Admin*).
- `GET /api/v1/events`: Inspect events by event type and user (*Admin / Manager / Auditor*).

### 10. Strawberry GraphQL (`/graphql`)
Send `POST /graphql` with `Authorization: Bearer <token>`:

```graphql
# Query products with filters and cursor pagination
query {
  products(filters: { limit: 5, category: "electronics" }) {
    items {
      id
      name
      price
      category
      specs
    }
    total
    nextCursor
  }
}

# Query product reviews
query {
  reviews(productId: "<product-id>") {
    id
    rating
    title
    comment
    pros
    cons
  }
}

# Mutation: Create product (Admin / Manager only)
mutation {
  createProduct(input: {
    name: "Enterprise Edge Gateway"
    description: "Multi-gigabit edge router"
    price: 899.99
    stock: 25
    category: "networking"
    specs: "{\"throughput\": \"10Gbps\", \"ports\": 8}"
  }) {
    id
    name
    price
  }
}
```

---

## Testing & Quality Assurance

NexusCatalog comes complete with:
1. **Automated Verification Suite**: Full 14-point, 47-assertion enterprise test suite covering all 6 databases, 4 RBAC roles, REST v1/v2, and GraphQL:
   ```powershell
   python tests/verify_system.py
   ```
2. **Postman Collection & Environment**: Ready-to-import files for testing in the Postman desktop application or web runner:
   - Collection: [`NexusCatalog.postman_collection.json`](NexusCatalog.postman_collection.json)
   - Environment: [`NexusCatalog.postman_environment.json`](NexusCatalog.postman_environment.json)
   - Auto-generator script: [`generate_postman.py`](generate_postman.py)
3. **Comprehensive Testing Guide**: For step-by-step instructions on running manual and automated tests across Postman and GraphiQL, see [TESTING.md](TESTING.md).
4. **Architecture & Concept Reference**: For intense detail on every concept (multi-tenant, polyglot persistence, RBAC, REST vs GraphQL, telemetry, and proof of coverage), see [Details.md](Details.md).
