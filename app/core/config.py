# app/core/config.py
import os
from urllib.parse import urlparse
from pydantic import BaseModel, Field


def _split_csv(val: str | None) -> list[str]:
    return [v.strip() for v in (val or "").split(",") if v.strip()]


class Settings(BaseModel):
    # App
    APP_NAME: str = "Glaria Backend"
    ENV: str = os.getenv("ENV", "development")

    # CORS / Frontend
    NEXT_PUBLIC_URL: str = os.getenv("NEXT_PUBLIC_URL", "https://www.apeingtest.com")
    ALLOW_ORIGINS: list[str] = Field(default_factory=list)  # can be overridden by ALLOWED_ORIGINS env (CSV)

    # DB
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/glaria",
    )

    # Chain
    OPTIMISM_RPC_URL: str = os.getenv("OPTIMISM_RPC_URL", "https://mainnet.optimism.io")
    ID_REGISTRY_ADDRESS: str = os.getenv(
        "ID_REGISTRY_ADDRESS",
        "0x00000000fc6c5f01fc30151999387bb99a9f489b",
    )

    # Auth / JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRES_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "43200")
    )  # 30 days

    def expected_domain(self) -> str:
        host = urlparse(self.NEXT_PUBLIC_URL).hostname
        return host or "www.apeingtest.com"


def build_settings() -> Settings:
    s = Settings()

    # ---- Ensure async driver for SQLAlchemy on Render ----
    # Render injects "postgresql://..."; upgrade to async driver if needed.
    if s.DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in s.DATABASE_URL:
        s.DATABASE_URL = s.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

    # ---- CORS ----
    # If ALLOWED_ORIGINS env is provided, use it (CSV).
    env_origins = _split_csv(os.getenv("ALLOWED_ORIGINS"))
    if env_origins:
        s.ALLOW_ORIGINS = env_origins
    else:
        dom = s.expected_domain()
        apex = dom.removeprefix("www.")
        s.ALLOW_ORIGINS = [
            f"https://{dom}",           # e.g. https://www.apeingtest.com
            f"https://{apex}",          # e.g. https://apeingtest.com
            s.NEXT_PUBLIC_URL,          # keeps whatever was passed (idempotent)
            "http://localhost:3000",    # Next.js dev
            "http://localhost:5173",    # Vite dev
        ]

    return s


settings = build_settings()
