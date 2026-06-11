"""Tests for session CRUD endpoints: POST /sessions, GET /sessions, GET /sessions/{id}/state, DELETE /sessions/{id}."""

from __future__ import annotations

import copy

import pytest

from tests.server.conftest import _MINIMAL_BODY


# ---------------------------------------------------------------------------
# POST /sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_returns_201(client):
    resp = await client.post("/sessions", json=_MINIMAL_BODY)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_session_returns_session_id(client):
    data = (await client.post("/sessions", json=_MINIMAL_BODY)).json()
    assert "session_id" in data
    assert data["session_id"]


@pytest.mark.asyncio
async def test_create_session_id_is_uuid(client):
    import re

    uuid_re = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    data = (await client.post("/sessions", json=_MINIMAL_BODY)).json()
    assert uuid_re.match(data["session_id"])


@pytest.mark.asyncio
async def test_create_session_returns_state(client):
    data = (await client.post("/sessions", json=_MINIMAL_BODY)).json()
    state = data["state"]
    assert "stress" in state
    assert "momentum" in state
    assert "harm" in state
    assert "clocks" in state


@pytest.mark.asyncio
async def test_create_session_starting_stress_is_zero(client):
    data = (await client.post("/sessions", json=_MINIMAL_BODY)).json()
    assert data["state"]["stress"] == 0


@pytest.mark.asyncio
async def test_create_session_starting_momentum_is_two(client):
    data = (await client.post("/sessions", json=_MINIMAL_BODY)).json()
    assert data["state"]["momentum"] == 2


@pytest.mark.asyncio
async def test_create_session_starting_harm_is_none(client):
    data = (await client.post("/sessions", json=_MINIMAL_BODY)).json()
    assert data["state"]["harm"] == "none"


@pytest.mark.asyncio
async def test_create_session_starting_clocks_is_empty(client):
    data = (await client.post("/sessions", json=_MINIMAL_BODY)).json()
    assert data["state"]["clocks"] == []


@pytest.mark.asyncio
async def test_create_session_invalid_attribute_sum_returns_422(client):
    body = {**_MINIMAL_BODY, "edge": 5, "heart": 5, "iron": 1, "shadow": 1, "wits": 1}
    resp = await client.post("/sessions", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_session_invalid_load_returns_422(client):
    body = {**_MINIMAL_BODY, "load": "ultralight"}
    resp = await client.post("/sessions", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_session_invalid_orchestration_mode_returns_422(client):
    body = {**_MINIMAL_BODY, "orchestration_mode": "chaos_mode"}
    resp = await client.post("/sessions", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_session_invalid_position_returns_422(client):
    body = {**_MINIMAL_BODY, "initial_position": "flanking"}
    resp = await client.post("/sessions", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_session_invalid_effect_returns_422(client):
    body = {**_MINIMAL_BODY, "initial_effect": "overwhelming"}
    resp = await client.post("/sessions", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_session_attribute_below_1_returns_422(client):
    body = {**_MINIMAL_BODY, "edge": 0}
    resp = await client.post("/sessions", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_session_different_ids_each_call(client):
    id1 = (await client.post("/sessions", json=_MINIMAL_BODY)).json()["session_id"]
    id2 = (await client.post("/sessions", json=_MINIMAL_BODY)).json()["session_id"]
    assert id1 != id2


# ---------------------------------------------------------------------------
# GET /sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sessions_returns_200(client):
    resp = await client.get("/sessions")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_sessions_empty_initially(client):
    data = (await client.get("/sessions")).json()
    assert data == []


@pytest.mark.asyncio
async def test_list_sessions_shows_created_session(client, session_id):
    data = (await client.get("/sessions")).json()
    ids = [s["id"] for s in data]
    assert session_id in ids


@pytest.mark.asyncio
async def test_list_sessions_summary_has_required_fields(client, session_id):
    sessions = (await client.get("/sessions")).json()
    sess = next(s for s in sessions if s["id"] == session_id)
    assert "id" in sess
    assert "model" in sess
    assert "last_saved" in sess
    assert "turn_count" in sess


@pytest.mark.asyncio
async def test_list_sessions_character_name_matches_body(client):
    body = {**_MINIMAL_BODY, "character_name": "Kira Dawnwhisper"}
    sid = (await client.post("/sessions", json=body)).json()["session_id"]
    sessions = (await client.get("/sessions")).json()
    sess = next(s for s in sessions if s["id"] == sid)
    assert sess.get("character_name") == "Kira Dawnwhisper"


@pytest.mark.asyncio
async def test_list_sessions_turn_count_starts_at_zero(client, session_id):
    sessions = (await client.get("/sessions")).json()
    sess = next(s for s in sessions if s["id"] == session_id)
    assert sess["turn_count"] == 0


@pytest.mark.asyncio
async def test_list_sessions_multiple(client):
    await client.post("/sessions", json=_MINIMAL_BODY)
    await client.post("/sessions", json=_MINIMAL_BODY)
    data = (await client.get("/sessions")).json()
    assert len(data) >= 2


# ---------------------------------------------------------------------------
# GET /sessions/{id}/state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session_state_returns_200(client, session_id):
    resp = await client.get(f"/sessions/{session_id}/state")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_session_state_has_required_fields(client, session_id):
    data = (await client.get(f"/sessions/{session_id}/state")).json()
    assert "stress" in data
    assert "momentum" in data
    assert "harm" in data
    assert "clocks" in data
    assert "turn_history" in data


@pytest.mark.asyncio
async def test_get_session_state_unknown_id_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/sessions/{fake_id}/state")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_session_state_turn_history_starts_empty(client, session_id):
    data = (await client.get(f"/sessions/{session_id}/state")).json()
    assert data["turn_history"] == []


# ---------------------------------------------------------------------------
# DELETE /sessions/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_session_returns_200(client, session_id):
    resp = await client.delete(f"/sessions/{session_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_session_returns_deleted_true(client, session_id):
    data = (await client.delete(f"/sessions/{session_id}")).json()
    assert data == {"deleted": True}


@pytest.mark.asyncio
async def test_delete_session_removes_from_list(client, session_id):
    await client.delete(f"/sessions/{session_id}")
    sessions = (await client.get("/sessions")).json()
    ids = [s["id"] for s in sessions]
    assert session_id not in ids


@pytest.mark.asyncio
async def test_delete_unknown_session_still_returns_200(client):
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = await client.delete(f"/sessions/{fake_id}")
    assert resp.status_code == 200
