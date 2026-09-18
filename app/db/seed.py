"""
app/db/seed.py
─────────────────────────────────────────────────────────────
Comprehensive Idempotent Seeding Engine for NexusCatalog.

Populates realistic, rich records across all 6 Polyglot Databases:
1. PostgreSQL  : `nexuscatalog`           (Tenants, 4-Role Users, Orders, OrderItems)
2. PostgreSQL  : `nexuscatalog_audit`     (Security Audit Logs & Compliance Ledger)
3. PostgreSQL  : `nexuscatalog_inventory` (Warehouses, Stock Batches & Allocations)
4. MongoDB     : `nexuscatalog`           (Products with Dynamic Schemas)
5. MongoDB     : `nexuscatalog_reviews`   (Customer Ratings, Pros/Cons & Reviews)
6. MongoDB     : `nexuscatalog_events`    (Clickstream Telemetry & User Analytics)
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.mongo import get_collection, get_events_collection, get_reviews_collection
from app.db.postgres import AsyncSessionAudit, AsyncSessionInventory, AsyncSessionLocal
from app.models.pg.audit import AuditLog
from app.models.pg.inventory import InventoryBatch, Warehouse
from app.models.pg.order import Order, OrderItem
from app.models.pg.tenant import Tenant
from app.models.pg.user import User, UserRole

logger = logging.getLogger("nexuscatalog.seed")


async def seed_all_databases() -> None:
    """Executes idempotent seeding across all 6 databases."""
    logger.info("[SEED] Beginning multi-database seeding across all 6 databases...")

    # 1. PostgreSQL `nexuscatalog`: Tenants, Users (4 roles), Orders
    tenant_id, product_ids = await _seed_postgres_core()

    # 2. MongoDB `nexuscatalog`: Dynamic Catalog Products
    mongo_product_ids = await _seed_mongo_catalog(tenant_id)
    all_product_ids = list(set(product_ids + mongo_product_ids))

    # 3. PostgreSQL `nexuscatalog_audit`: Compliance & Security Trail
    await _seed_postgres_audit(tenant_id)

    # 4. PostgreSQL `nexuscatalog_inventory`: Warehouses & Stock Batches
    await _seed_postgres_inventory(tenant_id, all_product_ids)

    # 5. MongoDB `nexuscatalog_reviews`: Product Reviews & Sentiment
    await _seed_mongo_reviews(tenant_id, all_product_ids)

    # 6. MongoDB `nexuscatalog_events`: Clickstream Telemetry
    await _seed_mongo_events(tenant_id, all_product_ids)

    logger.info("[SEED] Multi-database seeding completed successfully across all 6 databases!")


# ── 1. PostgreSQL Core (Tenants, 4-Role Users, Orders) ────────

async def _seed_postgres_core() -> tuple[str, list[str]]:
    async with AsyncSessionLocal() as session:
        # Tenants
        tenants_data = [
            ("Demo Corp", "Primary Enterprise E-Commerce Tenant"),
            ("CyberDyn Systems", "Robotics & Hardware Division"),
            ("Apex Global", "International Logistics & Retail"),
        ]
        tenant_map: dict[str, Tenant] = {}

        for name, _ in tenants_data:
            res = await session.execute(select(Tenant).where(Tenant.name == name))
            existing = res.scalar_one_or_none()
            if existing is None:
                t = Tenant(id=str(uuid.uuid4()), name=name)
                session.add(t)
                await session.flush()
                tenant_map[name] = t
            else:
                tenant_map[name] = existing

        demo_tenant = tenant_map["Demo Corp"]
        demo_id = demo_tenant.id

        # 4 Roles Users
        users_to_seed = [
            ("admin@nexuscatalog.io", "Admin@1234", UserRole.ADMIN.value),
            ("manager@nexuscatalog.io", "Manager@1234", UserRole.MANAGER.value),
            ("buyer@nexuscatalog.io", "Buyer@1234", UserRole.BUYER.value),
            ("auditor@nexuscatalog.io", "Auditor@1234", UserRole.AUDITOR.value),
        ]
        user_objs: dict[str, User] = {}

        for email, pwd, role in users_to_seed:
            res = await session.execute(select(User).where(User.email == email))
            existing_u = res.scalar_one_or_none()
            if existing_u is None:
                u = User(
                    id=str(uuid.uuid4()),
                    tenant_id=demo_id,
                    email=email,
                    hashed_password=hash_password(pwd),
                    role=role,
                    is_active=True,
                )
                session.add(u)
                await session.flush()
                user_objs[role] = u
            else:
                # Update role if needed
                if existing_u.role != role:
                    existing_u.role = role
                    session.add(existing_u)
                user_objs[role] = existing_u

        # Orders & OrderItems in PostgreSQL
        sample_prod_ids = [
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
        ]
        buyer_user = user_objs.get(UserRole.BUYER.value)

        res = await session.execute(select(Order).where(Order.tenant_id == demo_id))
        existing_orders = res.scalars().all()

        if len(existing_orders) < 5 and buyer_user:
            now = datetime.now(timezone.utc)
            statuses = ["pending", "confirmed", "shipped", "delivered"]
            for i in range(1, 6):
                ord_id = str(uuid.uuid4())
                status = statuses[i % len(statuses)]
                price1 = Decimal("249.99")
                price2 = Decimal("79.50")
                total = (price1 * 1) + (price2 * 2)

                order = Order(
                    id=ord_id,
                    tenant_id=demo_id,
                    user_id=buyer_user.id,
                    status=status,
                    total_amount=total,
                    created_at=now - timedelta(days=i),
                    updated_at=now - timedelta(days=i - 1 if i > 1 else 0),
                )
                session.add(order)
                await session.flush()

                item1 = OrderItem(
                    id=str(uuid.uuid4()),
                    order_id=ord_id,
                    product_id=sample_prod_ids[0],
                    product_name=f"Enterprise Server Unit {i}",
                    quantity=1,
                    unit_price=price1,
                )
                item2 = OrderItem(
                    id=str(uuid.uuid4()),
                    order_id=ord_id,
                    product_id=sample_prod_ids[1],
                    product_name=f"ECC Memory Module 32GB",
                    quantity=2,
                    unit_price=price2,
                )
                session.add_all([item1, item2])

        await session.commit()
        return demo_id, sample_prod_ids


# ── 2. MongoDB Catalog Products (nexuscatalog) ────────────────

async def _seed_mongo_catalog(tenant_id: str) -> list[str]:
    collection = get_collection("products")
    existing_count = await collection.count_documents({"tenant_id": tenant_id})
    product_ids: list[str] = []

    catalog_data = [
        {
            "name": "Quantum Pro Workstation X1",
            "description": "Enterprise grade AI compute workstation with dual liquid cooling.",
            "category": "workstations",
            "price": 3499.99,
            "stock": 18,
            "attributes": {"cpu": "AMD Threadripper PRO", "ram_gb": 128, "storage": "4TB NVMe Gen5", "gpu": "NVIDIA RTX 6000 Ada"},
        },
        {
            "name": "NexusCore Edge Router 10G",
            "description": "Low-latency edge appliance featuring hardware-accelerated routing.",
            "category": "networking",
            "price": 899.50,
            "stock": 42,
            "attributes": {"throughput": "10 Gbps", "ports": 8, "sfp_plus": 4, "rack_mountable": True},
        },
        {
            "name": "OmniVision Ultra 4K Display",
            "description": "Factory-calibrated reference monitor with DCI-P3 99% color gamut.",
            "category": "displays",
            "price": 749.00,
            "stock": 35,
            "attributes": {"screen_size": "32-inch", "refresh_rate": 144, "panel": "IPS-Black", "hdr": "HDR 1000"},
        },
        {
            "name": "HyperSync SAN Storage Array",
            "description": "All-flash enterprise storage array delivering sub-millisecond IOPS.",
            "category": "storage",
            "price": 5200.00,
            "stock": 10,
            "attributes": {"raw_capacity_tb": 64, "raid_levels": ["RAID-5", "RAID-6", "RAID-10"], "form_factor": "2U"},
        },
        {
            "name": "CipherShield Hardware HSM",
            "description": "FIPS 140-3 Level 3 certified hardware security module for key management.",
            "category": "security",
            "price": 2890.00,
            "stock": 25,
            "attributes": {"algorithms": ["RSA 4096", "ECDSA P-384", "Ed25519"], "interface": "PCIe Gen4"},
        },
        {
            "name": "Apex Acoustic Studio Headphones",
            "description": "Planar magnetic open-back reference monitoring headphones.",
            "category": "audio",
            "price": 429.99,
            "stock": 60,
            "attributes": {"driver_type": "Planar Magnetic", "impedance_ohms": 32, "cable": "Balanced 4.4mm"},
        },
    ]

    now = datetime.now(timezone.utc)
    for idx, item in enumerate(catalog_data):
        doc_id = f"seed-product-00{idx+1}"
        product_ids.append(doc_id)
        await collection.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "tenant_id": tenant_id,
                    "name": item["name"],
                    "description": item["description"],
                    "category": item["category"],
                    "price": item["price"],
                    "stock": item["stock"],
                    "attributes": item["attributes"],
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now - timedelta(days=idx * 2)},
            },
            upsert=True,
        )

    return product_ids


# ── 3. PostgreSQL Audit Logs (nexuscatalog_audit) ─────────────

async def _seed_postgres_audit(tenant_id: str) -> None:
    async with AsyncSessionAudit() as session:
        res = await session.execute(select(AuditLog).where(AuditLog.tenant_id == tenant_id))
        existing_logs = res.scalars().all()
        if len(existing_logs) >= 15:
            return

        now = datetime.now(timezone.utc)
        actions = [
            ("AUTH_LOGIN", "session", "admin", "admin@nexuscatalog.io", 200, "SUCCESS"),
            ("CREATE", "product", "manager", "manager@nexuscatalog.io", 201, "SUCCESS"),
            ("UPDATE_STATUS", "order", "manager", "manager@nexuscatalog.io", 200, "SUCCESS"),
            ("CHECK_ACCESS", "audit-logs", "auditor", "auditor@nexuscatalog.io", 200, "SUCCESS"),
            ("RESTOCK", "inventory", "manager", "manager@nexuscatalog.io", 201, "SUCCESS"),
            ("SUBMIT", "review", "buyer", "buyer@nexuscatalog.io", 201, "SUCCESS"),
            ("RBAC_REJECT", "tenant", "buyer", "buyer@nexuscatalog.io", 403, "FAILED"),
        ]

        for i in range(20):
            act, res_name, role, actor_id, code, st = actions[i % len(actions)]
            log = AuditLog(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                actor_id=actor_id,
                actor_role=role,
                action=act,
                resource=res_name,
                status=st,
                status_code=code,
                ip_address=f"192.168.1.{10 + (i % 5)}",
                details={"event_index": i, "description": f"Audited operation {act} on {res_name}"},
                created_at=now - timedelta(hours=i * 3),
            )
            session.add(log)

        await session.commit()


# ── 4. PostgreSQL Inventory & Warehouses (nexuscatalog_inventory) ──

async def _seed_postgres_inventory(tenant_id: str, product_ids: list[str]) -> None:
    async with AsyncSessionInventory() as session:
        res = await session.execute(select(Warehouse).where(Warehouse.tenant_id == tenant_id))
        existing_warehouses = res.scalars().all()

        warehouses: list[Warehouse] = []
        if not existing_warehouses:
            wh_defs = [
                ("Central Hub US-East", "US-EAST-01"),
                ("West Coast Distribution Center", "US-WEST-02"),
                ("EU Frankfurt Fulfillment Depot", "EU-CENTRAL-01"),
            ]
            for name, code in wh_defs:
                wh = Warehouse(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    name=name,
                    location_code=code,
                    is_active=True,
                )
                session.add(wh)
                await session.flush()
                warehouses.append(wh)
        else:
            warehouses = list(existing_warehouses)

        # Inventory Batches
        res_batches = await session.execute(select(InventoryBatch))
        existing_batches = res_batches.scalars().all()

        if len(existing_batches) < 15 and warehouses:
            now = datetime.now(timezone.utc)
            for idx, p_id in enumerate(product_ids):
                wh = warehouses[idx % len(warehouses)]
                batch = InventoryBatch(
                    id=str(uuid.uuid4()),
                    warehouse_id=wh.id,
                    product_id=p_id,
                    sku=f"SKU-NX-{p_id[:8].upper()}-{idx+1}",
                    quantity=100 + (idx * 25),
                    reserved_quantity=5 + (idx * 2),
                    restock_date=now - timedelta(days=idx),
                )
                session.add(batch)

        await session.commit()


# ── 5. MongoDB Product Reviews (nexuscatalog_reviews) ─────────

async def _seed_mongo_reviews(tenant_id: str, product_ids: list[str]) -> None:
    collection = get_reviews_collection()
    existing_count = await collection.count_documents({"tenant_id": tenant_id})
    if existing_count >= 15:
        return

    sample_reviews = [
        {"rating": 5, "title": "Incredible performance!", "comment": "Handled our model training workloads flawlessly without thermal throttling.", "pros": ["Silent operation", "Exceptional multi-core speed"], "cons": ["Heavy chassis"]},
        {"rating": 4, "title": "Solid enterprise hardware", "comment": "Great throughput and stability over 30 days of continuous testing.", "pros": ["Rock solid uptime", "Easy rack installation"], "cons": ["Documentation could be more detailed"]},
        {"rating": 5, "title": "Top tier quality", "comment": "Color accuracy out of the box is unmatched. Perfect for grading and CAD design.", "pros": ["Flawless panel", "Rich I/O ports"], "cons": []},
        {"rating": 4, "title": "Reliable and fast", "comment": "Seamless integration into our existing hybrid cloud pipeline.", "pros": ["Low latency", "High IOPS"], "cons": ["Price is on the premium side"]},
    ]

    now = datetime.now(timezone.utc)
    for i in range(16):
        rev = sample_reviews[i % len(sample_reviews)]
        p_id = product_ids[i % len(product_ids)]
        rev_id = f"seed-review-00{i+1}"
        doc = {
            "_id": rev_id,
            "tenant_id": tenant_id,
            "product_id": p_id,
            "user_id": f"buyer-user-00{(i%3)+1}",
            "user_email": f"buyer{(i%3)+1}@company.org",
            "rating": rev["rating"],
            "title": rev["title"],
            "comment": rev["comment"],
            "verified_purchase": True,
            "pros": rev["pros"],
            "cons": rev["cons"],
            "metadata": {"sentiment": "positive", "helpful_votes": 12 + i},
            "created_at": now - timedelta(days=i),
        }
        await collection.update_one({"_id": rev_id}, {"$set": doc}, upsert=True)


# ── 6. MongoDB Clickstream Events (nexuscatalog_events) ───────

async def _seed_mongo_events(tenant_id: str, product_ids: list[str]) -> None:
    collection = get_events_collection()
    existing_count = await collection.count_documents({"tenant_id": tenant_id})
    if existing_count >= 20:
        return

    event_types = ["page_view", "product_viewed", "cart_add", "checkout_start", "filter_applied"]
    now = datetime.now(timezone.utc)

    for i in range(25):
        evt_id = f"seed-event-00{i+1}"
        ev_type = event_types[i % len(event_types)]
        p_id = product_ids[i % len(product_ids)] if ev_type in ("product_viewed", "cart_add") else None
        doc = {
            "_id": evt_id,
            "tenant_id": tenant_id,
            "session_id": f"sess-{uuid.uuid4().hex[:12]}",
            "user_id": "buyer@nexuscatalog.io",
            "event_type": ev_type,
            "resource_id": p_id,
            "properties": {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "screen_resolution": "2560x1440",
                "latency_ms": 42.5 + (i % 10),
            },
            "ip_address": f"10.0.0.{50 + i}",
            "timestamp": now - timedelta(minutes=i * 15),
        }
        await collection.update_one({"_id": evt_id}, {"$set": doc}, upsert=True)
