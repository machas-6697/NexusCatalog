# NexusCatalog — Complete Testing & Validation Manual

> **Welcome!** If you are new to API testing, Postman, or GraphQL, this guide is written specifically for you.  
> We explain **every concept, every click, and every request step-by-step** so you can test, judge, and prove that the entire 6-database, 4-role enterprise system works with 100% guarantee.

---

## Table of Contents

1. [Understanding the System (The Big Picture)](#1-understanding-the-system-the-big-picture)
2. [Prerequisites & Getting Started](#2-prerequisites--getting-started)
3. [Testing with Postman (Step-by-Step for Beginners)](#3-testing-with-postman-step-by-step-for-beginners)
   - [Step 1: Download & Open Postman](#step-1-download--open-postman)
   - [Step 2: Import the Collection & Environment](#step-2-import-the-collection--environment)
   - [Step 3: Select the Active Environment](#step-3-select-the-active-environment)
   - [Step 4: How Automatic Token Injection Works](#step-4-how-automatic-token-injection-works)
   - [Step 5: Executing the 11 Test Folders in Order](#step-5-executing-the-11-test-folders-in-order)
   - [Step 6: One-Click Automated Run (Collection Runner)](#step-6-one-click-automated-run-collection-runner)
4. [Testing with Strawberry GraphQL Playground](#4-testing-with-strawberry-graphql-playground)
   - [What is GraphQL vs REST?](#what-is-graphql-vs-rest)
   - [Opening the GraphiQL Interactive IDE](#opening-the-graphiql-interactive-ide)
   - [Adding the Authorization Header](#adding-the-authorization-header)
   - [Executing Queries (Products & Reviews)](#executing-queries-products--reviews)
   - [Executing Mutations & Testing RBAC Protection](#executing-mutations--testing-rbac-protection)
5. [The 4-Role Access Control (RBAC) Test Matrix](#5-the-4-role-access-control-rbac-test-matrix)
6. [The 6 Polyglot Databases Verification](#6-the-6-polyglot-databases-verification)
7. [Running the 14-Point Automated Verification Suite](#7-running-the-14-point-automated-verification-suite)
8. [Troubleshooting & Common Questions](#8-troubleshooting--common-questions)

---

## 1. Understanding the System (The Big Picture)

NexusCatalog is an enterprise polyglot platform featuring:
- **Dual Interfaces**: 
  - **REST API** (`http://localhost:8000/api/v1` and `/api/v2`): Standard HTTP URLs with verbs (`GET`, `POST`, `PATCH`, `DELETE`).
  - **GraphQL** (`http://localhost:8000/graphql`): A single endpoint where clients ask for *only* the fields they need.
- **6 Independent Databases**:
  1. `nexuscatalog` (PostgreSQL): Core business transactions, multi-tenancy, users, and ACID orders.
  2. `nexuscatalog_audit` (PostgreSQL): Compliance audit logs recording security and administrative actions.
  3. `nexuscatalog_inventory` (PostgreSQL): Warehouses, SKU batches, and stock management.
  4. `nexuscatalog` (MongoDB): Product catalog supporting polymorphic nested specifications.
  5. `nexuscatalog_reviews` (MongoDB): Customer reviews, star ratings, and dynamic pros/cons.
  6. `nexuscatalog_events` (MongoDB): Real-time clickstream telemetry and analytics events.
- **4 Distinct Roles**:
  - **Admin**: System governance, tenant creation, and full oversight.
  - **Manager**: Catalog management, warehouse restocking, order fulfillment.
  - **Buyer**: Catalog browsing, order placement, submitting product reviews.
  - **Auditor**: Compliance inspection, audit log reading, telemetry review (strictly read-only on sensitive data).

---

## 2. Prerequisites & Getting Started

### 2.1 Start Docker Containers
Before running the app, ensure your database containers are running:
```powershell
docker start MACHAPOSTGRES MACHAMONGO MACHAREDIS MACHAPROMETHEUS MACHAGRAFANA
```

Verify that they are up:
```powershell
docker ps
```
You should see `MACHAPOSTGRES` on port `5400` and `MACHAMONGO` on port `27000`.

### 2.2 Start the FastAPI Application
In your terminal (inside `c:\MY-SPACE\NexusCatalog`):
```powershell
uvicorn app.main:app --reload --port 8000
```

You should see this startup confirmation:
```
[NexusCatalog] Starting up...
[OK] PostgreSQL tables ready across all 3 databases (nexuscatalog, nexuscatalog_audit, nexuscatalog_inventory)
[OK] All 6 Polyglot Databases seeded with demo records
[OK] MongoDB connections established across 3 databases (nexuscatalog, nexuscatalog_reviews, nexuscatalog_events)
[OK] App running at http://localhost:8000
[>>] Swagger UI  -> http://localhost:8000/docs
[>>] GraphQL     -> http://localhost:8000/graphql
[>>] Metrics     -> http://localhost:8000/metrics
```

### 2.3 Auto-Seeded Demo Accounts
On startup, demo records and accounts are automatically seeded:

| Role | Email | Password |
|:---|:---|:---|
| **Admin** | `admin@nexuscatalog.io` | `Admin@1234` |
| **Manager** | `manager@nexuscatalog.io` | `Manager@1234` |
| **Buyer** | `buyer@nexuscatalog.io` | `Buyer@1234` |
| **Auditor** | `auditor@nexuscatalog.io` | `Auditor@1234` |

---

## 3. Testing with Postman (Step-by-Step for Beginners)

Postman is a desktop and web application designed to send HTTP requests to servers and check responses.

### Step 1: Download & Open Postman
- Download free from [https://www.postman.com/downloads/](https://www.postman.com/downloads/) or use the web agent.
- Open Postman on your machine.

### Step 2: Import the Collection & Environment
NexusCatalog provides ready-to-use Postman files in the repository root:
1. In Postman, look at the top left sidebar and click the **"Import"** button.
2. Drag and drop (or browse and select) these **two files**:
   - `c:\MY-SPACE\NexusCatalog\NexusCatalog.postman_collection.json`
   - `c:\MY-SPACE\NexusCatalog\NexusCatalog.postman_environment.json`
3. Click **Import**.
4. You will now see:
   - Under **Collections**: `NexusCatalog Enterprise Test Suite (4 Roles & 6 Databases)`.
   - Under **Environments**: `NexusCatalog Enterprise Environment`.

### Step 3: Select the Active Environment
> **CRITICAL STEP**: If you skip this, requests will fail with `{{baseUrl}} unresolved`.
1. In the **top-right corner** of Postman, look for the environment dropdown (it usually defaults to `No Environment`).
2. Click the dropdown and select: **`NexusCatalog Enterprise Environment`**.
3. Now all variables like `{{baseUrl}}`, `{{adminEmail}}`, and dynamic tokens are active!

### Step 4: How Automatic Token Injection Works
You do **not** need to manually copy and paste authentication tokens!
- When you run any login request (e.g. `1. Admin Login`), Postman executes a built-in test script:
  ```javascript
  var j = pm.response.json();
  pm.environment.set("adminToken", j.access_token);
  ```
- This automatically saves `adminToken`, `managerToken`, `buyerToken`, and `auditorToken` into your environment.
- Subsequent requests automatically send `Authorization: Bearer {{adminToken}}`, `{{managerToken}}`, etc.

### Step 5: Executing the 11 Test Folders in Order

Click into the collection and expand the folders. Execute the requests in order:

#### Folder 01: Health & Discovery
1. **Health Check (`GET /`)**: Click **Send**.
   - Expected status: `200 OK`.
   - Response: `{"status": "ok", "service": "NexusCatalog API", "version": "2.0.0", ...}`.
2. **OpenAPI Specification (`GET /openapi.json`)**: Click **Send**.
   - Expected status: `200 OK`.
   - Verifies all 6-database endpoints are registered in the OpenAPI schema.

#### Folder 02: Authentication (4 Roles)
1. **1. Admin Login**: Click **Send**.
   - Status: `200 OK`. Returns `access_token` with `role: "admin"`. Automatically saves `adminToken`.
2. **2. Manager Login**: Click **Send**.
   - Status: `200 OK`. Returns `access_token` with `role: "manager"`. Automatically saves `managerToken`.
3. **3. Buyer Login**: Click **Send**.
   - Status: `200 OK`. Returns `access_token` with `role: "buyer"`. Automatically saves `buyerToken`.
4. **4. Auditor Login**: Click **Send**.
   - Status: `200 OK`. Returns `access_token` with `role: "auditor"`. Automatically saves `auditorToken`.
5. **Negative Test: Invalid Password**: Click **Send**.
   - Status: `401 Unauthorized`. Verifies unauthorized users cannot enter.

#### Folder 03: Multi-Tenant & RBAC
1. **Admin: List Tenants**: Status `200 OK`. Lists tenant `Demo Corp`. Automatically saves `tenantId`.
2. **Negative Test: Buyer List Tenants**: Status `403 Forbidden`. Confirms buyers cannot inspect tenants.
3. **Negative Test: Manager Create Tenant**: Status `403 Forbidden`. Confirms only admins can create tenants.

#### Folder 04: MongoDB Catalog (REST v1 & v2)
1. **Manager: Create Product with Dynamic Specs**: Status `201 Created`.
   - Sends dynamic nested specifications (`cpu`, `cores`, `power`).
   - Automatically saves `productId`.
2. **Buyer: List Products (Cursor Pagination)**: Status `200 OK`.
   - Demonstrates stable cursor-based pagination and returns `next_cursor`.
3. **REST v2: Product List**: Status `200 OK`.
   - Confirms backward compatibility: price is returned as string decimal (e.g. `"479.99"`).

#### Folder 05: PostgreSQL ACID Orders (PG DB 1)
1. **Buyer: Create ACID Order**: Status `201 Created`.
   - Transacts multi-item order in PostgreSQL with ACID isolation.
   - Automatically saves `orderId`.
2. **Manager: Update Order Status**: Status `200 OK`.
   - Transitions order status to `confirmed`.
3. **Auditor: Inspect All Tenant Orders**: Status `200 OK`.
   - Auditor reviews orders across the entire tenant.

#### Folder 06: PostgreSQL Audit Logs (PG DB 2)
1. **Auditor: List Audit Trail**: Status `200 OK`.
   - Reads from PostgreSQL `nexuscatalog_audit` database.
2. **Negative Test: Buyer Access Audit Logs**: Status `403 Forbidden`.
   - Guarantees regular buyers cannot access compliance security trails.

#### Folder 07: PostgreSQL Inventory & Warehouses (PG DB 3)
1. **Admin: Create Warehouse**: Status `201 Created`.
   - Provisions warehouse in PostgreSQL `nexuscatalog_inventory` database.
   - Automatically saves `warehouseId`.
2. **Manager: Restock Stock Batch**: Status `201 Created`.
   - Restocks SKU batch with quantity, cost price, and expiry date.
3. **Auditor: Inspect Warehouse Batches**: Status `200 OK`.
   - Read-only inspection of stock levels.

#### Folder 08: MongoDB Product Reviews (Mongo DB 2)
1. **Buyer: Submit Product Review**: Status `201 Created`.
   - Inserts review into MongoDB `nexuscatalog_reviews` database with rating and pros/cons.
2. **Negative Test: Auditor Submit Review**: Status `403 Forbidden`.
   - Enforces read-only permissions for Auditor.
3. **Public: Read Product Reviews**: Status `200 OK`.
   - Anyone can read product ratings and sentiment.

#### Folder 09: MongoDB Telemetry Events (Mongo DB 3)
1. **Buyer: Send Telemetry Event**: Status `201 Created`.
   - Records `checkout_start` clickstream event into MongoDB `nexuscatalog_events`.
2. **Auditor: List Telemetry Events**: Status `200 OK`.
   - Inspects telemetry streams for analytics and compliance.

#### Folder 10: Strawberry GraphQL Interface
1. **GraphQL Query: products**: Status `200 OK`.
   - Queries MongoDB product catalog via GraphQL.
2. **GraphQL Mutation: Manager createProduct**: Status `200 OK`.
   - Creates a product via GraphQL as Manager.
3. **Negative Test: Buyer createProduct in GraphQL**: Status `200 OK` (GraphQL error).
   - Returns GraphQL error with `message: "Forbidden"`. Guarantees RBAC enforcement in GraphQL!

#### Folder 11: Telemetry & Prometheus
1. **Prometheus Metrics (`GET /metrics`)**: Status `200 OK`.
   - Returns live Prometheus metrics tracking HTTP request counts and execution durations.

---

### Step 6: One-Click Automated Run (Collection Runner)
You can test the entire backend in 5 seconds with zero manual typing:
1. In Postman, click on the collection name: **`NexusCatalog Enterprise Test Suite (4 Roles & 6 Databases)`**.
2. In the right pane, click the blue **"Run"** button.
3. Make sure the Environment selected is **`NexusCatalog Enterprise Environment`**.
4. Click **"Run NexusCatalog Enterprise Test Suite"**.
5. Watch every request execute green (`200 OK`, `201 Created`, expected `403 Forbidden`, etc.).
6. **Result:** All tests pass 100%!

---

## 4. Testing with Strawberry GraphQL Playground

Strawberry GraphQL includes an interactive browser-based IDE (GraphiQL) hosted directly by the application.

### What is GraphQL vs REST?
- In **REST**, each entity has its own URL (`/products`, `/orders`, `/reviews`), and the server decides which fields to return.
- In **GraphQL**, there is **one endpoint** (`POST /graphql`). You submit a query declaring exactly what fields you want, and the server returns that exact JSON structure.

### Opening the GraphiQL Interactive IDE
1. Open your web browser (Chrome, Edge, Firefox).
2. Navigate to: **[http://localhost:8000/graphql](http://localhost:8000/graphql)**.
3. You will see the GraphiQL interface with a query editor on the left and a response pane on the right.

### Adding the Authorization Header
NexusCatalog protects GraphQL queries and mutations with the same JWT authentication as REST.
1. At the bottom of the GraphiQL screen, click on the **"Headers"** tab.
2. First, get a JWT token by logging in (either from Postman or by sending `POST /api/v1/auth/login`).
3. In the Headers tab, enter:
   ```json
   {
     "Authorization": "Bearer <paste_your_jwt_token_here>"
   }
   ```
*(Replace `<paste_your_jwt_token_here>` with the actual `access_token` from Admin, Manager, or Buyer).*

### Executing Queries (Products & Reviews)

#### 1. Query Products with Specs & Cursor Pagination
Paste the following in the left editor and click the pink **"Play" (Execute)** button:

```graphql
query GetProductCatalog {
  products(filters: { limit: 5 }) {
    total
    nextCursor
    items {
      id
      name
      price
      category
      stock
      specs
    }
  }
}
```

**Expected Response**:
```json
{
  "data": {
    "products": {
      "total": 3,
      "nextCursor": null,
      "items": [
        {
          "id": "5453ecfb-...",
          "name": "Cloud Enterprise Router",
          "price": 1299.99,
          "category": "networking",
          "stock": 45,
          "specs": "{\"throughput\": \"10Gbps\", \"ports\": 8}"
        }
      ]
    }
  }
}
```

#### 2. Query Reviews for a Product
```graphql
query GetProductReviews {
  reviews(productId: "5453ecfb-81e7-4819-b51b-e1dbcd10e2e6") {
    id
    rating
    title
    comment
    pros
    cons
  }
}
```

### Executing Mutations & Testing RBAC Protection

#### 1. Success as Manager or Admin
Ensure your `Authorization` header contains an **Admin** or **Manager** token. Run:

```graphql
mutation CreateNewProduct {
  createProduct(input: {
    name: "Enterprise Edge Gateway"
    description: "Ultra-low latency edge router"
    price: 899.99
    stock: 25
    category: "networking"
    specs: "{\"throughput\": \"40Gbps\", \"latency\": \"<1ms\"}"
  }) {
    id
    name
    price
    category
  }
}
```

**Expected Result**:
```json
{
  "data": {
    "createProduct": {
      "id": "...",
      "name": "Enterprise Edge Gateway",
      "price": 899.99,
      "category": "networking"
    }
  }
}
```

#### 2. Negative Test: RBAC Rejection as Buyer
Change your `Authorization` header to a **Buyer** token and run the exact same `createProduct` mutation above.

**Expected Result**:
```json
{
  "data": null,
  "errors": [
    {
      "message": "Forbidden",
      "path": ["createProduct"]
    }
  ]
}
```
This proves that role-based permissions are enforced inside GraphQL resolvers.

---

## 5. The 4-Role Access Control (RBAC) Test Matrix

Here is how you can verify each role's authorization boundary:

| Feature | Admin | Manager | Buyer | Auditor |
|:---|:---|:---|:---|:---|
| **View own profile (`/users/me`)** | Allowed (200) | Allowed (200) | Allowed (200) | Allowed (200) |
| **Manage Tenants (`/tenants`)** | Allowed (200/201) | Blocked (403) | Blocked (403) | Blocked (403) |
| **Create Products (REST / GraphQL)** | Allowed (201) | Allowed (201) | Blocked (403) | Blocked (403) |
| **Place Orders (`POST /orders`)** | Allowed (201) | Allowed (201) | Allowed (201) | Blocked (403) |
| **Inspect All Orders (`GET /orders`)** | Allowed (200) | Allowed (200) | Blocked (403) | Allowed (200) |
| **Change Order Status (`PATCH /orders/{id}`)** | Allowed (200) | Allowed (200) | Blocked (403) | Blocked (403) |
| **Read Audit Logs (`/audit-logs`)** | Allowed (200) | Blocked (403) | Blocked (403) | Allowed (200) |
| **Create Warehouses (`/inventory/warehouses`)** | Allowed (201) | Blocked (403) | Blocked (403) | Blocked (403) |
| **Restock Batches (`/inventory/batches`)** | Allowed (201) | Allowed (201) | Blocked (403) | Blocked (403) |
| **Inspect Batches (`GET /inventory/batches`)** | Allowed (200) | Allowed (200) | Blocked (403) | Allowed (200) |
| **Submit Reviews (`POST /reviews`)** | Allowed (201) | Allowed (201) | Allowed (201) | Blocked (403) |
| **Ingest Telemetry (`POST /events`)** | Allowed (201) | Allowed (201) | Allowed (201) | Blocked (403) |
| **Query Telemetry (`GET /events`)** | Allowed (200) | Allowed (200) | Blocked (403) | Allowed (200) |

---

## 6. The 6 Polyglot Databases Verification

You can inspect the databases directly to verify data persistence:

### PostgreSQL Databases (3 DBs)
Run these commands inside the `MACHAPOSTGRES` container:

```powershell
# 1. Inspect Core Transactional DB (tenants, users, orders)
docker exec -it MACHAPOSTGRES psql -U postgres -d nexuscatalog -c "SELECT email, role FROM users;"
docker exec -it MACHAPOSTGRES psql -U postgres -d nexuscatalog -c "SELECT id, total, status FROM orders;"

# 2. Inspect Audit DB (compliance security logs)
docker exec -it MACHAPOSTGRES psql -U postgres -d nexuscatalog_audit -c "SELECT user_email, action, status_code FROM audit_logs LIMIT 5;"

# 3. Inspect Inventory DB (warehouses and SKU batches)
docker exec -it MACHAPOSTGRES psql -U postgres -d nexuscatalog_inventory -c "SELECT name, code FROM warehouses;"
docker exec -it MACHAPOSTGRES psql -U postgres -d nexuscatalog_inventory -c "SELECT sku, quantity, status FROM inventory_batches LIMIT 5;"
```

### MongoDB Databases (3 DBs)
Run these commands inside the `MACHAMONGO` container:

```powershell
# 1. Inspect Product Catalog DB
docker exec -it MACHAMONGO mongosh --quiet --eval "use nexuscatalog; db.products.find({}, {name: 1, price: 1, specs: 1}).limit(3);"

# 2. Inspect Reviews DB
docker exec -it MACHAMONGO mongosh --quiet --eval "use nexuscatalog_reviews; db.reviews.find({}, {rating: 1, title: 1, pros: 1}).limit(3);"

# 3. Inspect Events & Telemetry DB
docker exec -it MACHAMONGO mongosh --quiet --eval "use nexuscatalog_events; db.events.find({}, {event_type: 1, timestamp: 1}).limit(3);"
```

---

## 7. Running the 14-Point Automated Verification Suite

NexusCatalog includes an automated test script that executes **14 test suites and 47 assertions** covering all endpoints, RBAC permissions, and database operations.

Run it anytime in your terminal:
```powershell
python tests/verify_system.py
```

### Expected Output
```
======================================================================
NexusCatalog -- Enterprise 4-Role & 6-Database Verification Suite
======================================================================
[NexusCatalog] Starting up...
[OK] PostgreSQL tables ready across all 3 databases (nexuscatalog, nexuscatalog_audit, nexuscatalog_inventory)
[OK] All 6 Polyglot Databases seeded with demo records
[OK] MongoDB connections established across 3 databases (nexuscatalog, nexuscatalog_reviews, nexuscatalog_events)
[OK] App running at http://localhost:8000

[1/14] Verifying Health & API Documentation...
  [OK] GET / (Health Check) - OK
  [OK] GET /openapi.json (OpenAPI 3.1 Schema with 6-DB paths) - OK

[2/14] Verifying 4-Role Public Auth & JWT Issuance...
  [OK] POST /api/v1/auth/login (Admin) - Token Issued
  [OK] POST /api/v1/auth/login (Manager) - Token Issued
  [OK] POST /api/v1/auth/login (Buyer) - Token Issued
  [OK] POST /api/v1/auth/login (Auditor) - Token Issued
  [OK] POST /api/v1/auth/login (Invalid password) - Correctly rejected with 401
  [OK] POST /api/v1/auth/register (Duplicate email) - Correctly rejected with 409

[3/14] Verifying Request Normalization & Tracing Middleware...
  [OK] Request Normalization active (X-Request-ID: 31fe9016..., Latency: 13.35ms)
  [OK] Missing Token - Correctly rejected with 401

[4/14] Verifying 4-Role Identity Profiles (/users/me)...
  [OK] Verified all 4 distinct roles: admin, manager, buyer, auditor

[5/14] Verifying Multi-Tenant Isolation & Role Guards...
  [OK] Buyer blocked from listing tenants (403)
  [OK] Manager blocked from creating tenants (403)
  [OK] Auditor blocked from creating tenants (403)
  [OK] Admin created new tenant

[6/14] Verifying MongoDB Product Catalog (REST v1)...
  [OK] Buyer blocked from creating product (403)
  [OK] Auditor blocked from creating product (403)
  [OK] Manager created product with dynamic BSON specs
  [OK] Cursor pagination page 1 returned next_cursor
  [OK] Cursor pagination page 2 successfully advanced

[7/14] Verifying REST v2 Backward-Compatible Translation...
  [OK] REST v2 translated float price to string decimal: '479.99'

[8/14] Verifying PostgreSQL ACID Orders (PG Database 1)...
  [OK] Buyer placed ACID order Total: $2500.0
  [OK] Buyer viewed own orders at /api/v1/orders/mine
  [OK] Buyer blocked from /api/v1/orders (403)
  [OK] Manager viewed all tenant orders (200)
  [OK] Auditor viewed all tenant orders for compliance inspection (200)
  [OK] Manager transitioned order status to 'confirmed'
  [OK] Auditor blocked from modifying order status (403)

[9/14] Verifying Audit Logs (PG Database 2: nexuscatalog_audit)...
  [OK] Buyer blocked from compliance audit logs (403)
  [OK] Manager blocked from compliance audit logs (403)
  [OK] Auditor listed audit records from nexuscatalog_audit
  [OK] Admin listed audit records from nexuscatalog_audit

[10/14] Verifying Warehouses & Inventory (PG Database 3: nexuscatalog_inventory)...
  [OK] Buyer blocked from warehouse inventory (403)
  [OK] Admin created warehouse
  [OK] Manager created stock batch in nexuscatalog_inventory
  [OK] Auditor inspected inventory stock batches

[11/14] Verifying Product Reviews (Mongo Database 2: nexuscatalog_reviews)...
  [OK] Buyer submitted product review to nexuscatalog_reviews (Rating: 5/5)
  [OK] Auditor blocked from mutating review (403 Read-Only)
  [OK] Retrieved review(s) with dynamic pros/cons

[12/14] Verifying Telemetry & Events (Mongo Database 3: nexuscatalog_events)...
  [OK] Ingested clickstream event into nexuscatalog_events (Type: checkout_start)
  [OK] Auditor retrieved telemetry events from nexuscatalog_events

[13/14] Verifying Strawberry GraphQL Interface (/graphql)...
  [OK] GET /graphql - GraphiQL Interactive IDE served (200 OK)
  [OK] GraphQL Query 'products' - Returned items
  [OK] GraphQL Mutation 'createProduct' as Manager - Created product
  [OK] GraphQL Mutation 'createProduct' as Buyer - Forbidden RBAC error raised
  [OK] GraphQL Query 'reviews' - Fetched reviews successfully

[14/14] Verifying Prometheus Telemetry (/metrics)...
  [OK] GET /metrics - Telemetry active, HTTP requests instrumented

======================================================================
ALL 47 VERIFICATION CHECKS PASSED WITH ZERO ERRORS!
======================================================================
```

---

## 8. Troubleshooting & Common Questions

| Symptom | Cause | Solution |
|:---|:---|:---|
| `ConnectionRefusedError: [WinError 1225]` | PostgreSQL or MongoDB Docker container is stopped. | Run `docker start MACHAPOSTGRES MACHAMONGO`. |
| Postman shows `{{baseUrl}} unresolved` | You did not select the Environment. | In the top-right corner of Postman, select `NexusCatalog Enterprise Environment`. |
| Postman shows `401 Unauthorized` on protected requests | You haven't run a Login request yet. | Run `1. Admin Login` or `2. Manager Login` in Folder 02 first so Postman can save the token. |
| GraphQL says `"Authentication required"` | Missing `Authorization` header in GraphiQL. | Expand the **Headers** tab at the bottom of GraphiQL and add `{"Authorization": "Bearer <token>"}`. |
| GraphQL says `"Forbidden"` | You attempted a mutation with insufficient permissions (e.g. Buyer creating a product). | Log in as Manager (`Manager@1234`) or Admin (`Admin@1234`) to perform product mutations. |
| Port 8000 already in use | An existing Uvicorn server is running. | Close the other terminal or run `kill` on the process using port 8000. |

---

## Summary Guarantee

The NexusCatalog enterprise system is verified and production-ready:
1. **4 Roles** (`Admin`, `Manager`, `Buyer`, `Auditor`) are strictly enforced via RBAC dependencies and GraphQL resolvers.
2. **6 Polyglot Databases** (3 PostgreSQL + 3 MongoDB) are fully operational and seeded with realistic demo records.
3. **Dual Interfaces** (REST v1/v2 + Strawberry GraphQL) operate simultaneously over the shared data layer.
4. **Automated & Manual Tooling**: Postman collection/environment JSON files and the 47-point verification suite guarantee correct, end-to-end functionality.
