# app/main.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.settings.APP_NAME, # todo have a look at this pls
        version=settings.settings.APP_VERSION,
        debug=settings.settings.DEBUG,
    )

    # CORS (si no lo necesitas, quítalo; pero en dev suele venir bien)
    if settings.settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_v1_router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"status": "ok", "app": settings.settings.APP_NAME, "version": settings.settings.APP_VERSION}

    return app


app = create_app()
