import os
from urllib.parse import urlparse
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(val: str | None) -> list[str]:
    return [v.strip() for v in (val or "").split(",") if v.strip()]


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Glaria Backend"
    ENV: str = os.getenv("ENV", "production")

    # In your Settings(BaseModel)
    AWS_ACCESS_KEY_ID: str = Field(..., alias="aws_access_key_id")
    AWS_SECRET_ACCESS_KEY: str = Field(..., alias="aws_secret_access_key")
    AWS_REGION: str = Field(..., alias="aws_region")
    S3_BUCKET_NAME: str = Field(..., alias="s3_bucket_name")
    #DEEPAI_API_KEY: str = Field(..., alias="deepai_api_key")

    # Twitter OAuth
    TWITTER_CLIENT_ID: str = Field(..., alias="twitter_client_id")
    TWITTER_CLIENT_SECRET: str = Field(..., alias="twitter_client_secret")
    TWITTER_CALLBACK_URL: str = Field(..., alias="twitter_callback_url")

    NEYNAR_API_KEY: str

    # Frontend URL used for CORS + SIWE domain checks
    NEXT_PUBLIC_URL: str = os.getenv("NEXT_PUBLIC_URL", "https://www.glaria.xyz")

    # CORS (schemed origins like https://www.glaria.xyz)
    ALLOW_ORIGINS: list[str] = Field(default_factory=list)  # override via ALLOWED_ORIGINS (CSV)
    ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    ALLOW_HEADERS: list[str] = ["*"]
    ALLOW_CREDENTIALS: bool = True

    # SIWE/Farcaster domain allow-list (authorities, e.g. "www.glaria.xyz", "localhost:3000")
    ALLOWED_SIWE_DOMAINS: str = Field(default="", alias="ALLOWED_SIWE_DOMAINS_RAW")

    # DB
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/glaria",
    )

    # Farcaster API Key (🔑 Required)
    FARCASTER_API_KEY: str

    # On-chain
    OPTIMISM_RPC_URL: str = os.getenv("OPTIMISM_RPC_URL", "https://mainnet.optimism.io")
    ID_REGISTRY_ADDRESS: str = os.getenv(
        "ID_REGISTRY_ADDRESS",
        "0x00000000fc6c5f01fc30151999387bb99a9f489b",
    )

    # Auth / JWT
    JWT_SECRET: str = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRES_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "43200"))  # 30 days

    # Cookies
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "access_token")
    SESSION_COOKIE_DOMAIN: str | None = os.getenv("SESSION_COOKIE_DOMAIN", ".glaria.xyz")
    SESSION_COOKIE_SECURE: bool = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_SAMESITE: str = os.getenv("SESSION_COOKIE_SAMESITE", "lax")  # 'lax' or 'none'

    # Load .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ---------- Helpers ----------

    def expected_domain(self) -> str:
        netloc = urlparse(self.NEXT_PUBLIC_URL).netloc
        return netloc or "www.glaria.xyz"

    def allowed_siwe_domains(self) -> set[str]:
        configured = set(self.ALLOWED_SIWE_DOMAINS or [])
        if configured:
            return configured

        dom = self.expected_domain()
        apex = dom.removeprefix("www.")
        return {dom, apex, "localhost:3000", "127.0.0.1:3000"}

    def frontend_origins(self) -> list[str]:
        if self.ALLOW_ORIGINS:
            return self.ALLOW_ORIGINS

        parsed = urlparse(self.NEXT_PUBLIC_URL)
        scheme = parsed.scheme or "https"
        dom = self.expected_domain()
        apex = dom.removeprefix("www.")
        return list({
            f"{scheme}://{dom}",
            f"{scheme}://{apex}",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        })


def build_settings() -> Settings:
    s = Settings()

    # Ensure asyncpg
    if s.DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in s.DATABASE_URL:
        s.DATABASE_URL = s.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    if s.DATABASE_URL.startswith("postgres://"):
        s.DATABASE_URL = s.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

    # Load CORS overrides
    env_origins = _split_csv(os.getenv("ALLOWED_ORIGINS"))
    if env_origins:
        s.ALLOW_ORIGINS = env_origins
    else:
        s.ALLOW_ORIGINS = s.frontend_origins()

    # Load SIWE domain overrides
    env_siwe = _split_csv(s.ALLOWED_SIWE_DOMAINS)
    if env_siwe:
        s.ALLOWED_SIWE_DOMAINS = env_siwe
    else:
        s.ALLOWED_SIWE_DOMAINS = list(s.allowed_siwe_domains())

    return s


settings = build_settings()