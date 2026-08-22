from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import request_id_middleware

APP_VERSION = "0.1.0"


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Disc Golf Tracker API", version=APP_VERSION)

    app.middleware("http")(request_id_middleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    return app


app = create_app()
