"""
app/config.py
─────────────────────────────────────────────────────────────
Centralized settings loaded from the .env file using
Pydantic BaseSettings. A single `settings` singleton is
imported everywhere — no raw os.getenv calls in route code.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── JWT ──────────────────────────────────
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # ── PostgreSQL (3 Databases) ─────────────────
    postgres_url: str
    postgres_url_audit: str = ""
    postgres_url_inventory: str = ""

    # ── MongoDB (3 Databases) ────────────────────
    mongo_url: str
    mongo_db_name: str = "nexuscatalog"
    mongo_db_reviews: str = "nexuscatalog_reviews"
    mongo_db_events: str = "nexuscatalog_events"

    # ── App ──────────────────────────────────────
    app_env: str = "development"
    app_port: int = 8000


# Single shared instance — import this everywhere
settings = Settings()
