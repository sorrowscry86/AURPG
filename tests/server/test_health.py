"""Tests for GET /health."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_status_ok(client):
    data = (await client.get("/health")).json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_version_is_string(client):
    data = (await client.get("/health")).json()
    assert isinstance(data["version"], str)
    assert data["version"]  # non-empty


@pytest.mark.asyncio
async def test_health_content_type_json(client):
    resp = await client.get("/health")
    assert "application/json" in resp.headers["content-type"]
