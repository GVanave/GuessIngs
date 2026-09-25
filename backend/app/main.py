import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyses, auth, meta, products, scan, users
from app.core.config import get_settings
from app.core.db import Base, get_engine
from app.core.errors import install_error_handlers
from app.core.ratelimit import rate_limit

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_production()
    docs = settings.environment != "production"

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.environment != "production":
            # Production uses Alembic migrations (see alembic/); dev/test create tables directly.
            Base.metadata.create_all(get_engine())
        yield

    app = FastAPI(
        lifespan=lifespan,
        title=f"{settings.app_name} API",
        version="1.0.0",
        docs_url="/api/docs" if docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if docs else None,
    )
    install_error_handlers(app)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id[:64]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        if not request.url.path.startswith("/api/docs"):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    default_limit = rate_limit("default", "rate_limit_default_per_minute")
    for router in (auth.router, users.router, scan.router, analyses.router, products.router, meta.router):
        app.include_router(router, prefix="/api", dependencies=[Depends(default_limit)])

    return app


app = create_app()
