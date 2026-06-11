"""GET /health"""

from __future__ import annotations

import importlib.metadata

from fastapi import APIRouter

from aurpg.server.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    try:
        version = importlib.metadata.version("aurpg")
    except importlib.metadata.PackageNotFoundError:
        version = "dev"
    return HealthResponse(status="ok", version=version)
