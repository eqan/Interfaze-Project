from functools import lru_cache

from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from config.settings import settings

# Create a limiter instance with the default rate
limiter = Limiter(key_func=get_remote_address)
runtime = settings.runtime

# Model settings for generating responses
# Gemini REST API expects camelCase keys within generationConfig
generation_config = {
  "temperature": runtime.ai.temperature,
  "topP": runtime.ai.top_p,
  "topK": runtime.ai.top_k,
  "maxOutputTokens": runtime.ai.max_output_tokens,
  "responseMimeType": runtime.ai.response_mime_type,
}

safety_settings = [
  # Gemini's safety settings for blocking harmful content
  # (Set to "BLOCK_ALL" for blocking)
  {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ALL"},
  {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ALL"},
  {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ALL"},
  {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ALL"},
]

database_url = (
    f"postgresql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

engine = create_engine(
    database_url,
    pool_size=runtime.database_pool.pool_size,
    max_overflow=runtime.database_pool.max_overflow,
    pool_timeout=runtime.database_pool.pool_timeout,
    pool_recycle=runtime.database_pool.pool_recycle,
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": runtime.database_pool.connect_timeout,
        "keepalives": runtime.database_pool.keepalives,
        "keepalives_idle": runtime.database_pool.keepalives_idle,
        "keepalives_interval": runtime.database_pool.keepalives_interval,
        "keepalives_count": runtime.database_pool.keepalives_count,
    },
)

# Keep loaded ORM attributes readable after session_scope() commits and removes
# the scoped session. This avoids detached-instance errors in service flows that
# return or inspect ORM objects outside the context manager.
Session = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))


@lru_cache(maxsize=1)
def get_voyage_client():
    if not settings.voyage_api_key:
        return None
    import voyageai

    return voyageai.Client(api_key=settings.voyage_api_key)


@lru_cache(maxsize=1)
def get_firecrawl_client():
    if not settings.firecrawl_api_key:
        return None
    from firecrawl import FirecrawlApp

    return FirecrawlApp(api_key=settings.firecrawl_api_key)


@lru_cache(maxsize=1)
def get_pinecone_index():
    if not settings.pinecone_api_key or not settings.pinecone_host:
        return None
    from pinecone import Pinecone

    client = Pinecone(api_key=settings.pinecone_api_key)
    return client.Index(host=settings.pinecone_host)


@lru_cache(maxsize=1)
def get_interfaze_client():
    if not settings.interfaze_api_key:
        return None

    try:
        from interfaze import Interfaze
    except ImportError as exc:
        raise RuntimeError("Interfaze SDK is not installed") from exc

    kwargs = {"api_key": settings.interfaze_api_key}
    if settings.interfaze_base_url:
        kwargs["base_url"] = settings.interfaze_base_url

    return Interfaze(**kwargs)
