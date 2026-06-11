"""Tests for GET /settings, PUT /settings, GET /models."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# GET /settings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_settings_returns_200(client):
    resp = await client.get("/settings")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_settings_has_required_fields(client):
    data = (await client.get("/settings")).json()
    assert "provider" in data
    assert "api_key_set" in data
    assert "api_key_preview" in data
    assert "model" in data
    assert "saves_dir" in data
    assert "port" in data


@pytest.mark.asyncio
async def test_get_settings_provider_is_string(client):
    data = (await client.get("/settings")).json()
    assert isinstance(data["provider"], str)


@pytest.mark.asyncio
async def test_get_settings_api_key_set_is_bool(client):
    data = (await client.get("/settings")).json()
    assert isinstance(data["api_key_set"], bool)


@pytest.mark.asyncio
async def test_get_settings_api_key_set_when_key_present(client):
    # patched_settings uses "sk-test-key" so api_key_set should be True
    data = (await client.get("/settings")).json()
    assert data["api_key_set"] is True


@pytest.mark.asyncio
async def test_get_settings_api_key_preview_masks_key(client):
    # Real key is "sk-test-key"; preview should not expose the full value
    data = (await client.get("/settings")).json()
    preview = data["api_key_preview"]
    assert "sk-test-key" not in preview
    assert "***" in preview


@pytest.mark.asyncio
async def test_get_settings_model_is_string(client):
    data = (await client.get("/settings")).json()
    assert isinstance(data["model"], str)
    assert data["model"]


@pytest.mark.asyncio
async def test_get_settings_port_is_int(client):
    data = (await client.get("/settings")).json()
    assert isinstance(data["port"], int)


# ---------------------------------------------------------------------------
# PUT /settings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_settings_returns_200(client):
    resp = await client.put("/settings", json={"model": "claude-opus-4-8"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_put_settings_updates_model(client):
    await client.put("/settings", json={"model": "claude-opus-4-8"})
    data = (await client.get("/settings")).json()
    assert data["model"] == "claude-opus-4-8"


@pytest.mark.asyncio
async def test_put_settings_updates_provider(client):
    resp = await client.put("/settings", json={"provider": "anthropic"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_put_settings_empty_body_returns_400(client):
    resp = await client.put("/settings", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_put_settings_response_has_required_fields(client):
    data = (await client.put("/settings", json={"model": "claude-haiku-4-5-20251001"})).json()
    assert "provider" in data
    assert "api_key_set" in data
    assert "model" in data


# ---------------------------------------------------------------------------
# GET /models
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_models_returns_200(client):
    resp = await client.get("/models")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_models_has_provider_and_models(client):
    data = (await client.get("/models")).json()
    assert "provider" in data
    assert "models" in data


@pytest.mark.asyncio
async def test_get_models_models_is_list(client):
    data = (await client.get("/models")).json()
    assert isinstance(data["models"], list)


@pytest.mark.asyncio
async def test_get_models_anthropic_provider_returns_non_empty_list(client):
    data = (await client.get("/models")).json()
    # patched_settings uses anthropic provider — static list always present
    assert len(data["models"]) > 0


@pytest.mark.asyncio
async def test_get_models_each_model_has_required_fields(client):
    data = (await client.get("/models")).json()
    for model in data["models"]:
        assert "id" in model
        assert "name" in model
        assert "context_length" in model
        assert "provider" in model


@pytest.mark.asyncio
async def test_get_models_includes_sonnet(client):
    data = (await client.get("/models")).json()
    ids = [m["id"] for m in data["models"]]
    assert any("sonnet" in mid for mid in ids)


@pytest.mark.asyncio
async def test_get_models_includes_haiku(client):
    data = (await client.get("/models")).json()
    ids = [m["id"] for m in data["models"]]
    assert any("haiku" in mid for mid in ids)
