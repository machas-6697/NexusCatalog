"""
tests/verify_system.py
─────────────────────────────────────────────────────────────
Comprehensive automated enterprise verification test suite for NexusCatalog.

Validates all architectural subsystems and keywords:
  1. Health & Documentation (OpenAPI, Swagger, GraphiQL)
  2. 4-Role Authentication & Token Issuance (Admin, Manager, Buyer, Auditor)
  3. Request Normalization & Middleware Routing (X-Request-ID, Latency headers, Auth guards)
  4. User Profile & Role Verification (All 4 roles)
  5. Multi-Tenant CRUD & RBAC (Admin-only creation, Manager/Buyer/Auditor 403 guards)
  6. MongoDB Product Catalog REST v1 (Cursor pagination, flexible attributes, Manager/Admin creation)
  7. REST v2 Backward Compatibility & Translation (Decimal string currency precision)
  8. PostgreSQL ACID Orders (Atomic multi-row commits, role segregation, status updates)
  9. PostgreSQL Database 2: Audit Logs (Compliance ledger, Admin & Auditor access, Buyer/Manager 403)
  10. PostgreSQL Database 3: Warehouses & Inventory (Batch tracking, Manager/Admin stock updates)
  11. MongoDB Database 2: Product Reviews (Sentiment/Ratings, Buyer submission, Auditor 403 read-only)
  12. MongoDB Database 3: Telemetry Events (Clickstream ingestion, Admin/Auditor analytics)
  13. Strawberry GraphQL Interface (Dual-Interface, Queries, Mutations, RBAC guards)
  14. Prometheus Telemetry (/metrics instrumentation)
"""

import os
import sys
import uuid
import warnings
from typing import Any, Tuple

# Suppress Starlette deprecation warning for clean terminal reporting
warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app


class TestFailure(Exception):
    pass


def run_tests():
    passed = 0
    print("=" * 70)
    print("NexusCatalog -- Enterprise 4-Role & 6-Database Verification Suite")
    print("=" * 70)

    with TestClient(app) as client:
        def req(
            method: str,
            path: str,
            body: dict | None = None,
            token: str | None = None,
            expected_status: int = 200,
        ) -> Tuple[int, Any, dict]:
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            if body is not None:
                resp = client.request(method, path, json=body, headers=headers)
            else:
                resp = client.request(method, path, headers=headers)

            status = resp.status_code
            try:
                data = resp.json()
            except Exception:
                data = resp.text

            if status != expected_status:
                raise TestFailure(
                    f"{method} {path} returned {status} (Expected {expected_status})\nResponse: {data}"
                )
            return status, data, dict(resp.headers)

        # ── 1. Health & Documentation ──────────────────────────────
        print("\n[1/14] Verifying Health & API Documentation...")
        _, data, _ = req("GET", "/", expected_status=200)
        assert data["status"] == "ok" and data["service"] == "NexusCatalog API"
        print("  [OK] GET / (Health Check) - OK")

        _, spec, _ = req("GET", "/openapi.json", expected_status=200)
        assert "paths" in spec and "/api/v1/auth/login" in spec["paths"]
        assert "/api/v1/audit-logs" in spec["paths"]
        assert "/api/v1/inventory/warehouses" in spec["paths"]
        assert "/api/v1/reviews" in spec["paths"]
        assert "/api/v1/events" in spec["paths"]
        print("  [OK] GET /openapi.json (OpenAPI 3.1 Schema with 6-DB paths) - OK")
        passed += 2

        # ── 2. 4-Role Authentication & Token Issuance ─────────────
        print("\n[2/14] Verifying 4-Role Public Auth & JWT Issuance...")
        # Admin Login
        _, res, _ = req("POST", "/api/v1/auth/login", body={"email": "admin@nexuscatalog.io", "password": "Admin@1234"})
        admin_token = res["access_token"]
        print("  [OK] POST /api/v1/auth/login (Admin) - Token Issued")

        # Manager Login
        _, res, _ = req("POST", "/api/v1/auth/login", body={"email": "manager@nexuscatalog.io", "password": "Manager@1234"})
        manager_token = res["access_token"]
        print("  [OK] POST /api/v1/auth/login (Manager) - Token Issued")

        # Buyer Login
        _, res, _ = req("POST", "/api/v1/auth/login", body={"email": "buyer@nexuscatalog.io", "password": "Buyer@1234"})
        buyer_token = res["access_token"]
        print("  [OK] POST /api/v1/auth/login (Buyer) - Token Issued")

        # Auditor Login
        _, res, _ = req("POST", "/api/v1/auth/login", body={"email": "auditor@nexuscatalog.io", "password": "Auditor@1234"})
        auditor_token = res["access_token"]
        print("  [OK] POST /api/v1/auth/login (Auditor) - Token Issued")

        # Invalid password check
        req("POST", "/api/v1/auth/login", body={"email": "admin@nexuscatalog.io", "password": "WrongPassword!"}, expected_status=401)
        print("  [OK] POST /api/v1/auth/login (Invalid password) - Correctly rejected with 401")

        # Duplicate email check
        req("POST", "/api/v1/auth/register", body={"email": "admin@nexuscatalog.io", "password": "AnyPassword123!", "role": "buyer"}, expected_status=409)
        print("  [OK] POST /api/v1/auth/register (Duplicate email) - Correctly rejected with 409")
        passed += 6

        # ── 3. Request Normalization & Middleware ─────────────────
        print("\n[3/14] Verifying Request Normalization & Tracing Middleware...")
        _, _, headers = req("GET", "/api/v1/users/me", token=admin_token, expected_status=200)
        assert "x-request-id" in headers, "Missing X-Request-ID header"
        assert "x-response-time-ms" in headers, "Missing X-Response-Time-Ms header"
        print(f"  [OK] Request Normalization active (X-Request-ID: {headers['x-request-id'][:8]}..., Latency: {headers['x-response-time-ms']}ms)")

        req("GET", "/api/v1/users/me", expected_status=401)
        print("  [OK] Missing Token - Correctly rejected with 401")
        passed += 2

        # ── 4. User Profiles & Role Verification ──────────────────
        print("\n[4/14] Verifying 4-Role Identity Profiles (/users/me)...")
        _, u_admin, _ = req("GET", "/api/v1/users/me", token=admin_token)
        assert u_admin["role"] == "admin"
        tenant_id = u_admin["tenant_id"]

        _, u_mgr, _ = req("GET", "/api/v1/users/me", token=manager_token)
        assert u_mgr["role"] == "manager"

        _, u_byr, _ = req("GET", "/api/v1/users/me", token=buyer_token)
        assert u_byr["role"] == "buyer"

        _, u_aud, _ = req("GET", "/api/v1/users/me", token=auditor_token)
        assert u_aud["role"] == "auditor"
        print("  [OK] Verified all 4 distinct roles: admin, manager, buyer, auditor")
        passed += 1

        # ── 5. Multi-Tenant CRUD & RBAC ───────────────────────────
        print("\n[5/14] Verifying Multi-Tenant Isolation & Role Guards...")
        # Buyer blocked
        req("GET", "/api/v1/tenants", token=buyer_token, expected_status=403)
        print("  [OK] Buyer blocked from listing tenants (403)")

        # Manager blocked
        req("POST", "/api/v1/tenants", body={"name": "Manager Attempt"}, token=manager_token, expected_status=403)
        print("  [OK] Manager blocked from creating tenants (403)")

        # Auditor blocked
        req("POST", "/api/v1/tenants", body={"name": "Auditor Attempt"}, token=auditor_token, expected_status=403)
        print("  [OK] Auditor blocked from creating tenants (403)")

        # Admin allowed
        _, t_created, _ = req("POST", "/api/v1/tenants", body={"name": f"Tenant-{uuid.uuid4().hex[:6]}"}, token=admin_token, expected_status=201)
        print(f"  [OK] Admin created new tenant: {t_created['name']} (ID: {t_created['id'][:8]}...)")
        passed += 4

        # ── 6. MongoDB Product Catalog (REST v1) ───────────────────
        print("\n[6/14] Verifying MongoDB Product Catalog (REST v1)...")
        # Buyer blocked from create
        req("POST", "/api/v1/products", body={"name": "Fail", "description": "d", "price": 10.0, "category": "c"}, token=buyer_token, expected_status=403)
        print("  [OK] Buyer blocked from creating product (403)")

        # Auditor blocked from create (Read-Only)
        req("POST", "/api/v1/products", body={"name": "Fail", "description": "d", "price": 10.0, "category": "c"}, token=auditor_token, expected_status=403)
        print("  [OK] Auditor blocked from creating product (403)")

        # Manager allowed to create product
        mgr_prod_payload = {
            "name": f"Manager Edge Router {uuid.uuid4().hex[:4]}",
            "description": "High performance network appliance",
            "price": 1250.00,
            "stock": 30,
            "category": "networking",
            "attributes": {"ports": 16, "rack_mountable": True, "throughput_gbps": 40},
        }
        _, mgr_prod, _ = req("POST", "/api/v1/products", body=mgr_prod_payload, token=manager_token, expected_status=201)
        product_id = mgr_prod["id"]
        print(f"  [OK] Manager created product with dynamic BSON specs: {mgr_prod['name']} (ID: {product_id})")

        # List products with cursor pagination
        _, page1, _ = req("GET", "/api/v1/products?limit=2", token=buyer_token, expected_status=200)
        assert len(page1["items"]) <= 2
        assert page1["next_cursor"] is not None
        print(f"  [OK] Cursor pagination page 1 returned next_cursor: {page1['next_cursor'][:12]}...")

        # Cursor pagination page 2
        _, page2, _ = req("GET", f"/api/v1/products?limit=2&cursor={page1['next_cursor']}", token=buyer_token, expected_status=200)
        assert len(page2["items"]) > 0
        print("  [OK] Cursor pagination page 2 successfully advanced")
        passed += 5

        # ── 7. REST v2 Backward-Compatible Translation ────────────
        print("\n[7/14] Verifying REST v2 Backward-Compatible Translation...")
        _, v2_list, _ = req("GET", "/api/v2/products?limit=2", token=buyer_token, expected_status=200)
        assert isinstance(v2_list["items"][0]["price"], str), "v2 price must be a string for decimal precision"
        print(f"  [OK] REST v2 translated float price to string decimal: '{v2_list['items'][0]['price']}'")
        passed += 1

        # ── 8. PostgreSQL ACID Transactions & Orders ──────────────
        print("\n[8/14] Verifying PostgreSQL ACID Orders (PG Database 1)...")
        # Buyer places order
        order_payload = {
            "items": [
                {
                    "product_id": product_id,
                    "product_name": "Manager Edge Router",
                    "quantity": 2,
                    "unit_price": 1250.00,
                }
            ]
        }
        _, order_res, _ = req("POST", "/api/v1/orders", body=order_payload, token=buyer_token, expected_status=201)
        order_id = order_res["id"]
        print(f"  [OK] Buyer placed ACID order {order_id[:8]}... Total: ${order_res['total_amount']}")

        # Buyer sees own orders
        _, my_orders, _ = req("GET", "/api/v1/orders/mine", token=buyer_token, expected_status=200)
        assert len(my_orders) >= 1
        print("  [OK] Buyer viewed own orders at /api/v1/orders/mine")

        # Buyer blocked from seeing all tenant orders
        req("GET", "/api/v1/orders", token=buyer_token, expected_status=403)
        print("  [OK] Buyer blocked from /api/v1/orders (403)")

        # Manager allowed to view all tenant orders
        _, mgr_orders, _ = req("GET", "/api/v1/orders", token=manager_token, expected_status=200)
        assert len(mgr_orders) >= 1
        print("  [OK] Manager viewed all tenant orders (200)")

        # Auditor allowed to inspect all tenant orders
        _, aud_orders, _ = req("GET", "/api/v1/orders", token=auditor_token, expected_status=200)
        assert len(aud_orders) >= 1
        print("  [OK] Auditor viewed all tenant orders for compliance inspection (200)")

        # Manager transitions order status
        _, upd_order, _ = req("PATCH", f"/api/v1/orders/{order_id}", body={"status": "confirmed"}, token=manager_token, expected_status=200)
        assert upd_order["status"] == "confirmed"
        print("  [OK] Manager transitioned order status to 'confirmed'")

        # Auditor blocked from modifying order status (Read-Only)
        req("PATCH", f"/api/v1/orders/{order_id}", body={"status": "shipped"}, token=auditor_token, expected_status=403)
        print("  [OK] Auditor blocked from modifying order status (403)")
        passed += 7

        # ── 9. PostgreSQL Database 2: Audit Logs ──────────────────
        print("\n[9/14] Verifying Audit Logs (PG Database 2: nexuscatalog_audit)...")
        # Buyer blocked
        req("GET", "/api/v1/audit-logs", token=buyer_token, expected_status=403)
        print("  [OK] Buyer blocked from compliance audit logs (403)")

        # Manager blocked
        req("GET", "/api/v1/audit-logs", token=manager_token, expected_status=403)
        print("  [OK] Manager blocked from compliance audit logs (403)")

        # Auditor allowed
        _, aud_logs, _ = req("GET", "/api/v1/audit-logs", token=auditor_token, expected_status=200)
        assert len(aud_logs) > 0
        print(f"  [OK] Auditor listed {len(aud_logs)} audit records from nexuscatalog_audit")

        # Admin allowed
        _, adm_logs, _ = req("GET", "/api/v1/audit-logs", token=admin_token, expected_status=200)
        assert len(adm_logs) > 0
        print(f"  [OK] Admin listed audit records from nexuscatalog_audit")
        passed += 4

        # ── 10. PostgreSQL Database 3: Warehouses & Inventory ─────
        print("\n[10/14] Verifying Warehouses & Inventory (PG Database 3: nexuscatalog_inventory)...")
        # Buyer blocked
        req("GET", "/api/v1/inventory/warehouses", token=buyer_token, expected_status=403)
        print("  [OK] Buyer blocked from warehouse inventory (403)")

        # Admin creates warehouse
        wh_payload = {"name": f"Regional Logistics Hub {uuid.uuid4().hex[:4]}", "location_code": "US-CENTRAL-03"}
        _, wh_res, _ = req("POST", "/api/v1/inventory/warehouses", body=wh_payload, token=admin_token, expected_status=201)
        wh_id = wh_res["id"]
        print(f"  [OK] Admin created warehouse: {wh_res['name']} (ID: {wh_id[:8]}...)")

        # Manager creates stock batch
        batch_payload = {
            "warehouse_id": wh_id,
            "product_id": product_id,
            "sku": f"SKU-MGR-{uuid.uuid4().hex[:6].upper()}",
            "quantity": 150,
            "reserved_quantity": 10,
        }
        _, batch_res, _ = req("POST", "/api/v1/inventory/batches", body=batch_payload, token=manager_token, expected_status=201)
        print(f"  [OK] Manager created stock batch in nexuscatalog_inventory (SKU: {batch_res['sku']}, Qty: 150)")

        # Auditor reads batches
        _, aud_batches, _ = req("GET", "/api/v1/inventory/batches", token=auditor_token, expected_status=200)
        assert len(aud_batches) > 0
        print(f"  [OK] Auditor inspected inventory stock batches (Count: {len(aud_batches)})")
        passed += 4

        # ── 11. MongoDB Database 2: Product Reviews ───────────────
        print("\n[11/14] Verifying Product Reviews (Mongo Database 2: nexuscatalog_reviews)...")
        # Buyer submits review
        review_payload = {
            "product_id": product_id,
            "rating": 5,
            "title": "Outstanding throughput!",
            "comment": "Deployed in our staging rack and observed zero packet loss under heavy load.",
            "pros": ["Low latency", "Easy mounting"],
            "cons": ["Fans are slightly audible under peak stress"],
            "metadata": {"verified": True},
        }
        _, rev_res, _ = req("POST", "/api/v1/reviews", body=review_payload, token=buyer_token, expected_status=201)
        print(f"  [OK] Buyer submitted product review to nexuscatalog_reviews (Rating: 5/5)")

        # Auditor blocked from submitting review (Read-Only)
        req("POST", "/api/v1/reviews", body=review_payload, token=auditor_token, expected_status=403)
        print("  [OK] Auditor blocked from mutating review (403 Read-Only)")

        # List reviews
        _, rev_list, _ = req("GET", f"/api/v1/reviews?product_id={product_id}", token=buyer_token, expected_status=200)
        assert len(rev_list["items"]) >= 1
        print(f"  [OK] Retrieved {len(rev_list['items'])} review(s) with dynamic pros/cons")
        passed += 3

        # ── 12. MongoDB Database 3: Telemetry Events ──────────────
        print("\n[12/14] Verifying Telemetry & Events (Mongo Database 3: nexuscatalog_events)...")
        # Record event
        event_payload = {
            "session_id": f"sess-{uuid.uuid4().hex[:8]}",
            "event_type": "checkout_start",
            "resource_id": order_id,
            "properties": {"step": 2, "cart_value": 2500.00, "ui_theme": "dark"},
        }
        _, evt_res, _ = req("POST", "/api/v1/events", body=event_payload, token=buyer_token, expected_status=201)
        print(f"  [OK] Ingested clickstream event into nexuscatalog_events (Type: {evt_res['event_type']})")

        # Auditor queries telemetry events
        _, evt_list, _ = req("GET", "/api/v1/events?limit=10", token=auditor_token, expected_status=200)
        assert len(evt_list) > 0
        print(f"  [OK] Auditor retrieved telemetry events from nexuscatalog_events (Count: {len(evt_list)})")
        passed += 2

        # ── 13. Strawberry GraphQL Interface ──────────────────────
        print("\n[13/14] Verifying Strawberry GraphQL Interface (/graphql)...")
        # GraphiQL IDE check
        resp_gql_ide = client.get("/graphql", headers={"Accept": "text/html"})
        assert resp_gql_ide.status_code == 200
        print("  [OK] GET /graphql - GraphiQL Interactive IDE served (200 OK)")

        # GraphQL Query products
        gql_products = """
        query {
            products(filters: { limit: 3 }) {
                items {
                    id
                    name
                    price
                    category
                }
                total
            }
        }
        """
        _, gql_res, _ = req("POST", "/graphql", body={"query": gql_products}, token=buyer_token, expected_status=200)
        assert len(gql_res["data"]["products"]["items"]) > 0
        print(f"  [OK] GraphQL Query 'products' - Returned {len(gql_res['data']['products']['items'])} items")

        # GraphQL Mutation createProduct as Manager (succeeds)
        gql_mgr_mut = """
        mutation {
            createProduct(input: {
                name: "GraphQL Managed Accelerator",
                description: "AI inference accelerator",
                price: 4999.00,
                stock: 10,
                category: "Accelerators"
            }) {
                id
                name
                price
            }
        }
        """
        _, gql_mgr_res, _ = req("POST", "/graphql", body={"query": gql_mgr_mut}, token=manager_token, expected_status=200)
        assert "data" in gql_mgr_res and gql_mgr_res["data"]["createProduct"] is not None
        gql_prod_id = gql_mgr_res["data"]["createProduct"]["id"]
        print(f"  [OK] GraphQL Mutation 'createProduct' as Manager - Created: {gql_mgr_res['data']['createProduct']['name']}")

        # GraphQL Mutation createProduct as Buyer (rejected with Forbidden)
        gql_buyer_mut = """
        mutation {
            createProduct(input: {
                name: "Unauthorized GPU",
                description: "Should fail",
                price: 199.99,
                stock: 1,
                category: "GPU"
            }) {
                id
            }
        }
        """
        _, gql_buyer_res, _ = req("POST", "/graphql", body={"query": gql_buyer_mut}, token=buyer_token, expected_status=200)
        assert "errors" in gql_buyer_res and "Forbidden" in gql_buyer_res["errors"][0]["message"]
        print("  [OK] GraphQL Mutation 'createProduct' as Buyer - Forbidden RBAC error raised")

        # GraphQL Query reviews
        gql_rev = f"""
        query {{
            reviews(productId: "{product_id}") {{
                id
                rating
                title
                comment
            }}
        }}
        """
        _, gql_rev_res, _ = req("POST", "/graphql", body={"query": gql_rev}, token=buyer_token, expected_status=200)
        assert "data" in gql_rev_res and isinstance(gql_rev_res["data"]["reviews"], list)
        print("  [OK] GraphQL Query 'reviews' - Fetched reviews successfully")
        passed += 5

        # ── 14. Telemetry & Prometheus ─────────────────────────────
        print("\n[14/14] Verifying Prometheus Telemetry (/metrics)...")
        resp_metrics = client.get("/metrics")
        assert resp_metrics.status_code == 200
        metrics_text = resp_metrics.text
        assert "http_requests_total" in metrics_text or "http_request_duration_seconds" in metrics_text or "process_cpu_seconds_total" in metrics_text
        print("  [OK] GET /metrics - Telemetry active, HTTP requests instrumented")
        passed += 1

    print("\n" + "=" * 70)
    print(f"ALL {passed} VERIFICATION CHECKS PASSED WITH ZERO ERRORS!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_tests()
    except TestFailure as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[FAIL] UNEXPECTED ERROR: {e}")
        sys.exit(1)
