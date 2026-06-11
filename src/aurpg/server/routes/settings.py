"""GET /settings, PUT /settings, GET /models"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aurpg.server._settings import get_app_settings, update_app_settings
from aurpg.server._store import invalidate_client
from aurpg.server.schemas import (
    ModelInfo,
    ModelsResponse,
    SettingsResponse,
    SettingsUpdate,
)

router = APIRouter()

# Hardcoded Anthropic models — updated manually when new releases ship
_ANTHROPIC_MODELS: list[ModelInfo] = [
    ModelInfo(id="claude-opus-4-8", name="Claude Opus 4.8", context_length=200000, provider="anthropic"),
    ModelInfo(id="claude-sonnet-4-6", name="Claude Sonnet 4.6", context_length=200000, provider="anthropic"),
    ModelInfo(id="claude-haiku-4-5-20251001", name="Claude Haiku 4.5", context_length=200000, provider="anthropic"),
]


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return key[:4] + "***" + key[-4:]


@router.get("/settings", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    s = get_app_settings()
    return SettingsResponse(
        provider=s.provider,
        api_key_set=bool(s.api_key),
        api_key_preview=_mask_key(s.api_key),
        model=s.model,
        saves_dir=s.saves_dir,
        port=s.port,
    )


@router.put("/settings", response_model=SettingsResponse)
async def put_settings(body: SettingsUpdate) -> SettingsResponse:
    kwargs = body.model_dump(exclude_none=True)
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated = update_app_settings(**kwargs)
    # New provider/key means the cached client is stale
    if "api_key" in kwargs or "provider" in kwargs:
        invalidate_client()
    return SettingsResponse(
        provider=updated.provider,
        api_key_set=bool(updated.api_key),
        api_key_preview=_mask_key(updated.api_key),
        model=updated.model,
        saves_dir=updated.saves_dir,
        port=updated.port,
    )


@router.get("/models", response_model=ModelsResponse)
async def get_models() -> ModelsResponse:
    s = get_app_settings()

    if s.provider == "openrouter":
        try:
            import httpx  # noqa: PLC0415

            headers: dict[str, str] = {"Content-Type": "application/json"}
            if s.api_key:
                headers["Authorization"] = f"Bearer {s.api_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://openrouter.ai/api/v1/models", headers=headers
                )
                resp.raise_for_status()
                data = resp.json()

            models = [
                ModelInfo(
                    id=m["id"],
                    name=m.get("name", m["id"]),
                    context_length=m.get("context_length") or 0,
                    provider="openrouter",
                )
                for m in data.get("data", [])
            ]
            return ModelsResponse(provider="openrouter", models=models)
        except Exception:
            # Fall back to Anthropic list rather than erroring the settings screen
            pass

    return ModelsResponse(provider=s.provider, models=_ANTHROPIC_MODELS)
