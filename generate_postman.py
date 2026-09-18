"""
generate_postman.py
─────────────────────────────────────────────────────────────
Generates Postman Collection v2.1 and Environment JSON files
for NexusCatalog Enterprise with 4-Role RBAC & 6 Databases.
"""

import json

def build_postman_artifacts():
    # ── Environment ───────────────────────────────────────────
    environment = {
        "id": "nexuscatalog-enterprise-env",
        "name": "NexusCatalog Enterprise Environment",
        "values": [
            {"key": "baseUrl", "value": "http://localhost:8000", "type": "default", "enabled": True},
            {"key": "adminEmail", "value": "admin@nexuscatalog.io", "type": "default", "enabled": True},
            {"key": "adminPassword", "value": "Admin@1234", "type": "default", "enabled": True},
            {"key": "managerEmail", "value": "manager@nexuscatalog.io", "type": "default", "enabled": True},
            {"key": "managerPassword", "value": "Manager@1234", "type": "default", "enabled": True},
            {"key": "buyerEmail", "value": "buyer@nexuscatalog.io", "type": "default", "enabled": True},
            {"key": "buyerPassword", "value": "Buyer@1234", "type": "default", "enabled": True},
            {"key": "auditorEmail", "value": "auditor@nexuscatalog.io", "type": "default", "enabled": True},
            {"key": "auditorPassword", "value": "Auditor@1234", "type": "default", "enabled": True},
            {"key": "adminToken", "value": "", "type": "secret", "enabled": True},
            {"key": "managerToken", "value": "", "type": "secret", "enabled": True},
            {"key": "buyerToken", "value": "", "type": "secret", "enabled": True},
            {"key": "auditorToken", "value": "", "type": "secret", "enabled": True},
            {"key": "tenantId", "value": "", "type": "default", "enabled": True},
            {"key": "productId", "value": "", "type": "default", "enabled": True},
            {"key": "orderId", "value": "", "type": "default", "enabled": True},
            {"key": "warehouseId", "value": "", "type": "default", "enabled": True},
            {"key": "nextCursor", "value": "", "type": "default", "enabled": True}
        ]
    }

    # ── Collection ────────────────────────────────────────────
    collection = {
        "info": {
            "_postman_id": "nexuscatalog-enterprise-suite-v2",
            "name": "NexusCatalog Enterprise Test Suite (4 Roles & 6 Databases)",
            "description": "Full end-to-end testing suite for NexusCatalog: 4-Role RBAC (Admin, Manager, Buyer, Auditor), 6 Polyglot Databases (3 PostgreSQL + 3 MongoDB), REST v1/v2, Strawberry GraphQL, and Prometheus.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [
            {
                "name": "01 Health & Discovery",
                "item": [
                    {
                        "name": "Health Check (GET /)",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {"raw": "{{baseUrl}}/", "host": ["{{baseUrl}}"], "path": [""]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "pm.test('Service is healthy', function() { pm.expect(pm.response.json().status).to.eql('ok'); });"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "OpenAPI Specification (GET /openapi.json)",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {"raw": "{{baseUrl}}/openapi.json", "host": ["{{baseUrl}}"], "path": ["openapi.json"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "pm.test('Paths include all 6 databases', function() {",
                                    "    var p = pm.response.json().paths;",
                                    "    pm.expect(p['/api/v1/audit-logs']).to.not.be.undefined;",
                                    "    pm.expect(p['/api/v1/inventory/warehouses']).to.not.be.undefined;",
                                    "    pm.expect(p['/api/v1/reviews']).to.not.be.undefined;",
                                    "    pm.expect(p['/api/v1/events']).to.not.be.undefined;",
                                    "});"
                                ]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "02 Authentication (4 Roles)",
                "item": [
                    {
                        "name": "1. Admin Login",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Content-Type", "value": "application/json"}],
                            "body": {"mode": "raw", "raw": "{\"email\": \"{{adminEmail}}\", \"password\": \"{{adminPassword}}\"}"},
                            "url": {"raw": "{{baseUrl}}/api/v1/auth/login", "host": ["{{baseUrl}}"], "path": ["api", "v1", "auth", "login"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "var j = pm.response.json();",
                                    "pm.environment.set('adminToken', j.access_token);",
                                    "console.log('Saved adminToken');"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "2. Manager Login",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Content-Type", "value": "application/json"}],
                            "body": {"mode": "raw", "raw": "{\"email\": \"{{managerEmail}}\", \"password\": \"{{managerPassword}}\"}"},
                            "url": {"raw": "{{baseUrl}}/api/v1/auth/login", "host": ["{{baseUrl}}"], "path": ["api", "v1", "auth", "login"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "var j = pm.response.json();",
                                    "pm.environment.set('managerToken', j.access_token);",
                                    "console.log('Saved managerToken');"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "3. Buyer Login",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Content-Type", "value": "application/json"}],
                            "body": {"mode": "raw", "raw": "{\"email\": \"{{buyerEmail}}\", \"password\": \"{{buyerPassword}}\"}"},
                            "url": {"raw": "{{baseUrl}}/api/v1/auth/login", "host": ["{{baseUrl}}"], "path": ["api", "v1", "auth", "login"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "var j = pm.response.json();",
                                    "pm.environment.set('buyerToken', j.access_token);",
                                    "console.log('Saved buyerToken');"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "4. Auditor Login",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Content-Type", "value": "application/json"}],
                            "body": {"mode": "raw", "raw": "{\"email\": \"{{auditorEmail}}\", \"password\": \"{{auditorPassword}}\"}"},
                            "url": {"raw": "{{baseUrl}}/api/v1/auth/login", "host": ["{{baseUrl}}"], "path": ["api", "v1", "auth", "login"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "var j = pm.response.json();",
                                    "pm.environment.set('auditorToken', j.access_token);",
                                    "console.log('Saved auditorToken');"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "Negative Test: Invalid Password (401)",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Content-Type", "value": "application/json"}],
                            "body": {"mode": "raw", "raw": "{\"email\": \"{{adminEmail}}\", \"password\": \"WrongPass\"}"},
                            "url": {"raw": "{{baseUrl}}/api/v1/auth/login", "host": ["{{baseUrl}}"], "path": ["api", "v1", "auth", "login"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 401', function() { pm.response.to.have.status(401); });"]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "03 Multi-Tenant & RBAC",
                "item": [
                    {
                        "name": "Admin: List Tenants (200 OK)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{adminToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v1/tenants", "host": ["{{baseUrl}}"], "path": ["api", "v1", "tenants"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "pm.environment.set('tenantId', pm.response.json()[0].id);"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "Negative Test: Buyer List Tenants (403 Forbidden)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{buyerToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v1/tenants", "host": ["{{baseUrl}}"], "path": ["api", "v1", "tenants"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 403 Forbidden', function() { pm.response.to.have.status(403); });"]
                            }
                        }]
                    },
                    {
                        "name": "Negative Test: Manager Create Tenant (403 Forbidden)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{managerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {"mode": "raw", "raw": "{\"name\": \"Unauthorized Tenant\"}"},
                            "url": {"raw": "{{baseUrl}}/api/v1/tenants", "host": ["{{baseUrl}}"], "path": ["api", "v1", "tenants"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 403 Forbidden', function() { pm.response.to.have.status(403); });"]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "04 MongoDB Catalog (REST v1 & v2)",
                "item": [
                    {
                        "name": "Manager: Create Product with Dynamic Specs",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{managerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n  \"name\": \"Postman AI Node {{$randomInt}}\",\n  \"description\": \"Edge acceleration appliance\",\n  \"price\": 1499.00,\n  \"stock\": 50,\n  \"category\": \"compute\",\n  \"attributes\": {\n    \"tflops\": 120,\n    \"memory_gb\": 64,\n    \"connectivity\": [\"10GbE\", \"PCIe 5.0\"]\n  }\n}"
                            },
                            "url": {"raw": "{{baseUrl}}/api/v1/products", "host": ["{{baseUrl}}"], "path": ["api", "v1", "products"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 201 Created', function() { pm.response.to.have.status(201); });",
                                    "var j = pm.response.json();",
                                    "pm.environment.set('productId', j.id);",
                                    "console.log('Saved productId');"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "Buyer: List Products (Cursor Pagination Page 1)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{buyerToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v1/products?limit=2", "host": ["{{baseUrl}}"], "path": ["api", "v1", "products"], "query": [{"key": "limit", "value": "2"}]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "var j = pm.response.json();",
                                    "if (j.next_cursor) { pm.environment.set('nextCursor', j.next_cursor); }"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "REST v2: Product List (Decimal String Price Translation)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{buyerToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v2/products?limit=2", "host": ["{{baseUrl}}"], "path": ["api", "v2", "products"], "query": [{"key": "limit", "value": "2"}]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "pm.test('Price is formatted as string decimal', function() {",
                                    "    pm.expect(pm.response.json().items[0].price).to.be.a('string');",
                                    "});"
                                ]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "05 PostgreSQL ACID Orders (PG DB 1)",
                "item": [
                    {
                        "name": "Buyer: Create ACID Order",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{buyerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n  \"items\": [\n    {\n      \"product_id\": \"{{productId}}\",\n      \"product_name\": \"Postman AI Node\",\n      \"quantity\": 2,\n      \"unit_price\": 1499.00\n    }\n  ]\n}"
                            },
                            "url": {"raw": "{{baseUrl}}/api/v1/orders", "host": ["{{baseUrl}}"], "path": ["api", "v1", "orders"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 201 Created', function() { pm.response.to.have.status(201); });",
                                    "var j = pm.response.json();",
                                    "pm.environment.set('orderId', j.id);",
                                    "console.log('Saved orderId');"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "Manager: Update Order Status (Transition to confirmed)",
                        "request": {
                            "method": "PATCH",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{managerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {"mode": "raw", "raw": "{\"status\": \"confirmed\"}"},
                            "url": {"raw": "{{baseUrl}}/api/v1/orders/{{orderId}}", "host": ["{{baseUrl}}"], "path": ["api", "v1", "orders", "{{orderId}}"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "pm.test('Status is confirmed', function() { pm.expect(pm.response.json().status).to.eql('confirmed'); });"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "Auditor: Inspect All Tenant Orders (200 OK)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{auditorToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v1/orders", "host": ["{{baseUrl}}"], "path": ["api", "v1", "orders"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 200 OK for auditor', function() { pm.response.to.have.status(200); });"]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "06 PostgreSQL Audit Logs (PG DB 2)",
                "item": [
                    {
                        "name": "Auditor: List Audit Trail (200 OK)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{auditorToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v1/audit-logs?limit=10", "host": ["{{baseUrl}}"], "path": ["api", "v1", "audit-logs"], "query": [{"key": "limit", "value": "10"}]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200 OK', function() { pm.response.to.have.status(200); });",
                                    "pm.test('Returns audit records', function() { pm.expect(pm.response.json().length).to.be.above(0); });"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "Negative Test: Buyer Access Audit Logs (403 Forbidden)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{buyerToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v1/audit-logs", "host": ["{{baseUrl}}"], "path": ["api", "v1", "audit-logs"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 403 Forbidden', function() { pm.response.to.have.status(403); });"]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "07 PostgreSQL Inventory & Warehouses (PG DB 3)",
                "item": [
                    {
                        "name": "Admin: Create Warehouse (201 Created)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{adminToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n  \"name\": \"East Coast Fulfillment Hub {{$randomInt}}\",\n  \"location_code\": \"US-EAST-99\"\n}"
                            },
                            "url": {"raw": "{{baseUrl}}/api/v1/inventory/warehouses", "host": ["{{baseUrl}}"], "path": ["api", "v1", "inventory", "warehouses"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 201 Created', function() { pm.response.to.have.status(201); });",
                                    "var j = pm.response.json();",
                                    "pm.environment.set('warehouseId', j.id);",
                                    "console.log('Saved warehouseId');"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "Manager: Restock Stock Batch (201 Created)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{managerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n  \"warehouse_id\": \"{{warehouseId}}\",\n  \"product_id\": \"{{productId}}\",\n  \"sku\": \"SKU-NODE-{{$randomInt}}\",\n  \"quantity\": 100,\n  \"reserved_quantity\": 0\n}"
                            },
                            "url": {"raw": "{{baseUrl}}/api/v1/inventory/batches", "host": ["{{baseUrl}}"], "path": ["api", "v1", "inventory", "batches"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 201 Created', function() { pm.response.to.have.status(201); });"]
                            }
                        }]
                    },
                    {
                        "name": "Auditor: Inspect Warehouse Batches (200 OK)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{auditorToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v1/inventory/batches", "host": ["{{baseUrl}}"], "path": ["api", "v1", "inventory", "batches"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 200 OK', function() { pm.response.to.have.status(200); });"]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "08 MongoDB Product Reviews (Mongo DB 2)",
                "item": [
                    {
                        "name": "Buyer: Submit Product Review (201 Created)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{buyerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n  \"product_id\": \"{{productId}}\",\n  \"rating\": 5,\n  \"title\": \"Phenomenal efficiency\",\n  \"comment\": \"Benchmarked in production under heavy load with zero packet drop.\",\n  \"pros\": [\"Fast\", \"Reliable\", \"Energy Efficient\"],\n  \"cons\": []\n}"
                            },
                            "url": {"raw": "{{baseUrl}}/api/v1/reviews", "host": ["{{baseUrl}}"], "path": ["api", "v1", "reviews"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 201 Created', function() { pm.response.to.have.status(201); });",
                                    "pm.test('Rating is 5', function() { pm.expect(pm.response.json().rating).to.eql(5); });"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "Negative Test: Auditor Submit Review (403 Read-Only)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{auditorToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n  \"product_id\": \"{{productId}}\",\n  \"rating\": 3,\n  \"title\": \"Auditor Attempt\",\n  \"comment\": \"Should fail\"\n}"
                            },
                            "url": {"raw": "{{baseUrl}}/api/v1/reviews", "host": ["{{baseUrl}}"], "path": ["api", "v1", "reviews"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 403 Forbidden', function() { pm.response.to.have.status(403); });"]
                            }
                        }]
                    },
                    {
                        "name": "Public: Read Product Reviews",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{buyerToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v1/reviews?product_id={{productId}}", "host": ["{{baseUrl}}"], "path": ["api", "v1", "reviews"], "query": [{"key": "product_id", "value": "{{productId}}"}]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 200 OK', function() { pm.response.to.have.status(200); });"]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "09 MongoDB Telemetry Events (Mongo DB 3)",
                "item": [
                    {
                        "name": "Buyer: Send Telemetry Event (201 Created)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{buyerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n  \"session_id\": \"sess-postman-{{$randomInt}}\",\n  \"event_type\": \"cart_add\",\n  \"resource_id\": \"{{productId}}\",\n  \"properties\": {\"qty\": 2, \"referrer\": \"postman\"}\n}"
                            },
                            "url": {"raw": "{{baseUrl}}/api/v1/events", "host": ["{{baseUrl}}"], "path": ["api", "v1", "events"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 201 Created', function() { pm.response.to.have.status(201); });"]
                            }
                        }]
                    },
                    {
                        "name": "Auditor: List Telemetry Events (200 OK)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{auditorToken}}"}],
                            "url": {"raw": "{{baseUrl}}/api/v1/events?limit=5", "host": ["{{baseUrl}}"], "path": ["api", "v1", "events"], "query": [{"key": "limit", "value": "5"}]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": ["pm.test('Status is 200 OK', function() { pm.response.to.have.status(200); });"]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "10 Strawberry GraphQL Interface",
                "item": [
                    {
                        "name": "GraphQL Query: products (Dual-Interface)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{buyerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "graphql",
                                "graphql": {
                                    "query": "query GetProducts {\n  products(filters: { limit: 5 }) {\n    items {\n      id\n      name\n      price\n      category\n    }\n    total\n  }\n}",
                                    "variables": ""
                                }
                            },
                            "url": {"raw": "{{baseUrl}}/graphql", "host": ["{{baseUrl}}"], "path": ["graphql"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "pm.test('Returned products', function() { pm.expect(pm.response.json().data.products.items.length).to.be.above(0); });"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "GraphQL Mutation: Manager createProduct",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{managerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "graphql",
                                "graphql": {
                                    "query": "mutation AddProduct($input: ProductInput!) {\n  createProduct(input: $input) {\n    id\n    name\n    price\n  }\n}",
                                    "variables": "{\n  \"input\": {\n    \"name\": \"GraphQL Enterprise Server\",\n    \"description\": \"Managed via GraphQL\",\n    \"price\": 3999.00,\n    \"category\": \"servers\",\n    \"stock\": 12\n  }\n}"
                                }
                            },
                            "url": {"raw": "{{baseUrl}}/graphql", "host": ["{{baseUrl}}"], "path": ["graphql"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "pm.test('Product created via GraphQL', function() { pm.expect(pm.response.json().data.createProduct.name).to.eql('GraphQL Enterprise Server'); });"
                                ]
                            }
                        }]
                    },
                    {
                        "name": "Negative Test: Buyer createProduct in GraphQL (Forbidden)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{buyerToken}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "graphql",
                                "graphql": {
                                    "query": "mutation AddProduct($input: ProductInput!) {\n  createProduct(input: $input) {\n    id\n  }\n}",
                                    "variables": "{\n  \"input\": {\n    \"name\": \"Unauthorized Hardware\",\n    \"price\": 100.0\n  }\n}"
                                }
                            },
                            "url": {"raw": "{{baseUrl}}/graphql", "host": ["{{baseUrl}}"], "path": ["graphql"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('GraphQL envelope is 200', function() { pm.response.to.have.status(200); });",
                                    "pm.test('Returns Forbidden error', function() { pm.expect(pm.response.json().errors[0].message).to.include('Forbidden'); });"
                                ]
                            }
                        }]
                    }
                ]
            },
            {
                "name": "11 Telemetry & Prometheus",
                "item": [
                    {
                        "name": "Prometheus Metrics (/metrics)",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {"raw": "{{baseUrl}}/metrics", "host": ["{{baseUrl}}"], "path": ["metrics"]}
                        },
                        "event": [{
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "pm.test('Status is 200', function() { pm.response.to.have.status(200); });",
                                    "pm.test('Prometheus telemetry active', function() { pm.expect(pm.response.text()).to.include('http_requests_total'); });"
                                ]
                            }
                        }]
                    }
                ]
            }
        ]
    }

    with open("NexusCatalog.postman_environment.json", "w", encoding="utf-8") as f:
        json.dump(environment, f, indent=2)

    with open("NexusCatalog.postman_collection.json", "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2)

    print("[OK] NexusCatalog.postman_collection.json and NexusCatalog.postman_environment.json generated!")


if __name__ == "__main__":
    build_postman_artifacts()
