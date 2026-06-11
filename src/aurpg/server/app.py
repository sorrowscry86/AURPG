"""AURPG FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from aurpg.server.routes import health, sessions, settings, turns


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from aurpg.server._settings import get_app_settings  # noqa: PLC0415

    saves = Path(get_app_settings().saves_dir)
    saves.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="AURPG Server",
    description="HTTP adapter over the AURPG game engine.",
    lifespan=_lifespan,
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(turns.router)
app.include_router(settings.router)
