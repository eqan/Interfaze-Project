from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.config import limiter
from chatbot.chatbotController import router as chatbot_router
from document_intelligence.documentIntelligenceController import (
    router as document_intelligence_router,
)
from ingestion.ingestionController import router as ingestion_router
from web_extract.webExtractController import router as web_extract_router
from stats.scheduler import scheduler
from stats.statsController import router as stats_router
from ticket.ticketController import router as ticket_router
from users.usersController import router as user_router
from database import create_tables
from config.settings import settings
import uvicorn

try:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
except ImportError:
    RateLimitExceeded = None

    def _rate_limit_exceeded_handler(*_args, **_kwargs):
        return {"detail": "rate limiting unavailable"}

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None


def create_app() -> FastAPI:
    runtime = settings.runtime
    app = FastAPI()

    if runtime.features.enable_sentry and settings.sentry_dsn and sentry_sdk is not None:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            send_default_pii=True,
        )

    app.state.limiter = limiter
    if RateLimitExceeded is not None:
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime.cors.allow_origins,
        allow_credentials=runtime.cors.allow_credentials,
        allow_methods=runtime.cors.allow_methods,
        allow_headers=runtime.cors.allow_headers,
    )

    app.include_router(chatbot_router)
    app.include_router(user_router)
    if runtime.features.enable_interfaze:
        app.include_router(document_intelligence_router)
    if runtime.features.enable_stats:
        app.include_router(stats_router)
    if runtime.features.enable_ticketing:
        app.include_router(ticket_router)
    if runtime.features.enable_ingestion:
        app.include_router(ingestion_router)
    if runtime.features.enable_web_extract:
        app.include_router(web_extract_router)

    @app.get("/")
    async def root():
        return {"message": "Backend Server has been booted"}

    @app.on_event("startup")
    async def _start_scheduler():
        if runtime.features.enable_scheduler and not scheduler.running:
            scheduler.start()

    @app.on_event("shutdown")
    async def _shutdown_scheduler():
        if scheduler.running:
            scheduler.shutdown()

    if runtime.features.enable_sentry:
        @app.get("/sentry-debug")
        async def trigger_error():
            division_by_zero = 1 / 0

    return app


app = create_app()

if __name__ == "__main__":
    runtime_server = settings.runtime.server
    create_tables()
    uvicorn.run(
        app,
        host=runtime_server.host,
        port=runtime_server.port,
    )
