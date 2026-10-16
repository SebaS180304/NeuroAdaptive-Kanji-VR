"""
Punto de entrada de la app FastAPI.

Fase 1 - Foundation & Feasibility: este es el "FastAPI skeleton" que
pide M1, con WebSocket probado y health checks. Los routers de
contenido pedagogico (kanji, trials), adaptacion (ESL/LAL) y dashboard
se agregan en fases posteriores sobre esta misma estructura modular.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, participants, pretest, sessions, websocket
from app.config import get_settings
from app.core.logging import configure_logging
from app.services import stale_sessions

settings = get_settings()
configure_logging(settings.environment)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(stale_sessions.run_forever())
    yield
    task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version=settings.api_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(participants.router)
    app.include_router(pretest.router)
    app.include_router(sessions.router)
    app.include_router(websocket.router)

    return app


app = create_app()
