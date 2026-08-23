from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.courses import router as courses_router
from app.api.routes.feed import router as feed_router
from app.api.routes.friends import router as friends_router
from app.api.routes.layouts import router as layouts_router
from app.api.routes.leaderboards import router as leaderboards_router
from app.api.routes.rounds import router as rounds_router
from app.api.routes.stats import router as stats_router
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
    app.include_router(courses_router)
    app.include_router(layouts_router)
    app.include_router(admin_router)
    app.include_router(rounds_router)
    app.include_router(stats_router)
    app.include_router(friends_router)
    app.include_router(feed_router)
    app.include_router(leaderboards_router)

    return app


app = create_app()
