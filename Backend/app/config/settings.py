import json
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 4
    timeout_keep_alive: int = 120


class CorsSettings(BaseModel):
    allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    allow_methods: list[str] = Field(default_factory=lambda: ["GET", "POST"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])


class RateLimitSettings(BaseModel):
    chatbot: str = "5/second"
    chatbot_stream: str = "5/second"
    ingestion_scrape: str = "5/minute"
    ingestion_search: str = "5/second"
    interfaze_extract: str = "5/minute"
    ticket: str = "5/second"
    stats: str = "5/second"


class CacheSettings(BaseModel):
    backend: str = "memory"
    namespace: str = "interfaze"
    default_ttl_seconds: int = 300
    search_ttl_seconds: int = 180
    redis_url: str = ""


class FeatureSettings(BaseModel):
    enable_sentry: bool = True
    enable_scheduler: bool = True
    enable_stats: bool = True
    enable_ticketing: bool = True
    enable_ingestion: bool = True
    enable_interfaze: bool = True
    enable_google_search_grounding: bool = True


class DatabasePoolSettings(BaseModel):
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    connect_timeout: int = 10
    keepalives: int = 1
    keepalives_idle: int = 60
    keepalives_interval: int = 10
    keepalives_count: int = 5


class AISettings(BaseModel):
    temperature: float = 1
    top_p: float = 0.95
    top_k: int = 64
    max_output_tokens: int = 8192
    response_mime_type: str = "text/plain"


class RuntimeSettings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    rate_limits: RateLimitSettings = Field(default_factory=RateLimitSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    features: FeatureSettings = Field(default_factory=FeatureSettings)
    database_pool: DatabasePoolSettings = Field(default_factory=DatabasePoolSettings)
    ai: AISettings = Field(default_factory=AISettings)


class Settings(BaseSettings):
    logging_level: str = "WARNING"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 4
    timeout_keep_alive: int = 120
    model_api_key: str = ""
    model_name: str = "gemini-2.5-flash"
    model_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    allowed_origins: str = "*"
    db_user: str
    db_password: str = ""
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str
    google_oauth_url: str = "https://oauth2.googleapis.com/tokeninfo"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_days: int = 7
    enable_internal_test_auth: bool = False
    internal_service_secret: str = ""
    internal_test_token_ttl_minutes: int = 120
    internal_test_email_domain: str = "example.com"
    sentry_dsn: str = ""
    firecrawl_api_key: str = Field(default="", validation_alias="FIRECRAWL")
    voyage_api_key: str = ""
    embedding_model: str = "voyage-3"
    reasoning_model_api_key: str = ""
    pinecone_index_name: str = ""
    pinecone_api_key: str = ""
    pinecone_host: str = ""
    interfaze_api_key: str = ""
    interfaze_model_name: str = "interfaze-beta"
    interfaze_base_url: str = ""
    runtime_config_path: str = str(Path(__file__).resolve().parent / "runtime.json")

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        extra="allow",
    )

    @cached_property
    def runtime(self) -> RuntimeSettings:
        config_path = Path(self.runtime_config_path)
        if not config_path.exists():
            return self._runtime_with_env_fallback(RuntimeSettings())

        with config_path.open("r", encoding="utf-8") as file:
            raw_config = json.load(file)

        runtime = RuntimeSettings.model_validate(raw_config)
        return self._runtime_with_env_fallback(runtime)

    def _runtime_with_env_fallback(self, runtime: RuntimeSettings) -> RuntimeSettings:
        runtime.server.host = self.host
        runtime.server.port = self.port
        runtime.server.reload = self.reload
        runtime.server.workers = self.workers
        runtime.server.timeout_keep_alive = self.timeout_keep_alive

        if self.allowed_origins and runtime.cors.allow_origins == ["*"]:
            runtime.cors.allow_origins = [
                origin.strip()
                for origin in self.allowed_origins.split(",")
                if origin.strip()
            ] or ["*"]
        return runtime


settings = Settings()
