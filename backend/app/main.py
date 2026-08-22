from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import request_id_middleware
from app.core.rate_limit import limiter

APP_VERSION = "0.1.0"


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Disc Golf Tracker API", version=APP_VERSION)

    app.state.limiter = limiter

    app.middleware("http")(request_id_middleware)
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str | bool]:
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        finally:
            await engine.dispose()

        return {"version": APP_VERSION, "database_reachable": db_ok}

    app.include_router(auth_router)
    app.include_router(users_router)

    return app


app = create_app()
