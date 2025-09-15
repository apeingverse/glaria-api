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

    # Public URL used for both CORS defaults and SIWE domain checks
    # (keep the same env name you already use on the frontend)
    NEXT_PUBLIC_URL: str = os.getenv("NEXT_PUBLIC_URL", "https://www.glaria.xyz")

    # CORS (full origins like https://www.glaria.xyz)
    ALLOW_ORIGINS: list[str] = Field(default_factory=list)  # override with ALLOWED_ORIGINS (CSV)

    # SIWE/Farcaster domain allowlist (authorities, e.g. "www.glaria.xyz", "localhost:3000")
    ALLOWED_SIWE_DOMAINS: list[str] = Field(default_factory=list)  # override with ALLOWED_SIWE_DOMAINS (CSV)

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
        os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "43200")  # 30 days
    )

    # ---------- Helpers ----------

    def expected_domain(self) -> str:
        """
        Exact authority for SIWE domain matching.
        Uses netloc so localhost:3000 is preserved in dev.
        """
        netloc = urlparse(self.NEXT_PUBLIC_URL).netloc
        return netloc or "www.glaria.xyz"

    def allowed_siwe_domains(self) -> set[str]:
        """
        Domains (authorities) that are accepted for SIWE's `domain`.
        Defaults to {www, apex, localhost dev}, but can be overridden with ALLOWED_SIWE_DOMAINS.
        """
        configured = set(self.ALLOWED_SIWE_DOMAINS or [])
        if configured:
            return configured

        dom = self.expected_domain()  # e.g. "www.glaria.xyz" or "localhost:3000"
        apex = dom.removeprefix("www.")

        allowed = {dom, apex, "localhost:3000", "127.0.0.1:3000"}
        # Add common Netlify/Vercel preview hosts here if needed via env:
        # e.g. ALLOWED_SIWE_DOMAINS="www.glaria.xyz,glaria.xyz,deploy-preview-123--yourapp.netlify.app"
        return allowed

    def frontend_origins(self) -> list[str]:
        """
        Full origins (scheme + host[:port]) for CORS.
        """
        origins = set(self.ALLOW_ORIGINS or [])
        if origins:
            return list(origins)

        # Build sensible defaults from NEXT_PUBLIC_URL and apex + local dev
        parsed = urlparse(self.NEXT_PUBLIC_URL)
        scheme = parsed.scheme or "https"
        dom = self.expected_domain()
        apex = dom.removeprefix("www.")

        defaults = {
            f"{scheme}://{dom}",
            f"{scheme}://{apex}",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }
        return list(defaults)


def build_settings() -> Settings:
    s = Settings()

    # ---- Ensure async driver for SQLAlchemy ----
    if s.DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in s.DATABASE_URL:
        s.DATABASE_URL = s.DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )
    if s.DATABASE_URL.startswith("postgres://"):  # older Heroku-style URIs
        s.DATABASE_URL = s.DATABASE_URL.replace(
            "postgres://", "postgresql+asyncpg://", 1
        )

    # ---- Load allow-lists from env (optional) ----
    # CORS
    env_origins = _split_csv(os.getenv("ALLOWED_ORIGINS"))
    if env_origins:
        s.ALLOW_ORIGINS = env_origins
    else:
        s.ALLOW_ORIGINS = s.frontend_origins()

    # SIWE domains
    env_siwe = _split_csv(os.getenv("ALLOWED_SIWE_DOMAINS"))
    if env_siwe:
        s.ALLOWED_SIWE_DOMAINS = env_siwe
    else:
        s.ALLOWED_SIWE_DOMAINS = list(s.allowed_siwe_domains())

    return s


settings = build_settings()
