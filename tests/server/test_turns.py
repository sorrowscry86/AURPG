"""Tests for POST /sessions/{id}/turn."""

from __future__ import annotations

import pytest

from aurpg.llm import EngineResponse

_FAKE_RESPONSE = EngineResponse(
    raw_text="[SCENE] Dockyard\n[STRESS] +0\nThe shadows part.\n1) Press forward.\n2) Fall back.\n3) Call for help.",
    ledger_block="[SCENE] Dockyard\n[STRESS] +0",
    options=["Press forward.", "Fall back.", "Call for help."],
    input_tokens=100,
    output_tokens=50,
)

_XCARD_RESPONSE = EngineResponse(
    raw_text="[OOC] X-Card invoked. Stepping out of the fiction.",
    ledger_block=None,
    options=[],
    input_tokens=0,
    output_tokens=0,
)


def _make_run_turn(response: EngineResponse):
    """Return a mock run_turn function that returns the given response."""

    def _run_turn(session, player_input, *, client):
        from aurpg.session import Session

        new_session = Session(
            id=session.id,
            state=session.state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=session.recap_threshold,
            system_prompt_path=session.system_prompt_path,
        )
        return new_session, response

    return _run_turn


# ---------------------------------------------------------------------------
# Normal turns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_returns_200(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_FAKE_RESPONSE))

    resp = await client.post(
        f"/sessions/{session_id}/turn", json={"player_input": "I rush into the shadows."}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_turn_response_has_required_fields(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_FAKE_RESPONSE))

    data = (
        await client.post(
            f"/sessions/{session_id}/turn", json={"player_input": "I rush forward."}
        )
    ).json()
    assert "raw_text" in data
    assert "options" in data
    assert "ledger_block" in data
    assert "state" in data
    assert "safety_event" in data


@pytest.mark.asyncio
async def test_turn_raw_text_is_string(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_FAKE_RESPONSE))

    data = (
        await client.post(
            f"/sessions/{session_id}/turn", json={"player_input": "Look around."}
        )
    ).json()
    assert isinstance(data["raw_text"], str)
    assert data["raw_text"]


@pytest.mark.asyncio
async def test_turn_options_is_list(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_FAKE_RESPONSE))

    data = (
        await client.post(
            f"/sessions/{session_id}/turn", json={"player_input": "Look around."}
        )
    ).json()
    assert isinstance(data["options"], list)


@pytest.mark.asyncio
async def test_turn_three_options_returned(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_FAKE_RESPONSE))

    data = (
        await client.post(
            f"/sessions/{session_id}/turn", json={"player_input": "Look around."}
        )
    ).json()
    assert len(data["options"]) == 3


@pytest.mark.asyncio
async def test_turn_ledger_block_string(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_FAKE_RESPONSE))

    data = (
        await client.post(
            f"/sessions/{session_id}/turn", json={"player_input": "Look around."}
        )
    ).json()
    assert data["ledger_block"] == "[SCENE] Dockyard\n[STRESS] +0"


@pytest.mark.asyncio
async def test_turn_safety_event_is_null_for_normal_input(
    client, session_id, fake_client, monkeypatch
):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_FAKE_RESPONSE))

    data = (
        await client.post(
            f"/sessions/{session_id}/turn", json={"player_input": "I press forward."}
        )
    ).json()
    assert data["safety_event"] is None


@pytest.mark.asyncio
async def test_turn_state_snapshot_in_response(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_FAKE_RESPONSE))

    data = (
        await client.post(
            f"/sessions/{session_id}/turn", json={"player_input": "Look."}
        )
    ).json()
    state = data["state"]
    assert "stress" in state
    assert "momentum" in state
    assert "harm" in state
    assert "clocks" in state


# ---------------------------------------------------------------------------
# Safety command turns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_x_card_sets_safety_event(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_XCARD_RESPONSE))

    data = (
        await client.post(
            f"/sessions/{session_id}/turn", json={"player_input": "[X-Card]"}
        )
    ).json()
    assert data["safety_event"] is not None
    assert data["safety_event"]["command"] == "x_card"


@pytest.mark.asyncio
async def test_turn_hard_stop_sets_safety_event(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client
    monkeypatch.setattr(_turns, "run_turn", _make_run_turn(_XCARD_RESPONSE))

    data = (
        await client.post(
            f"/sessions/{session_id}/turn", json={"player_input": "!enforce_hard_stop"}
        )
    ).json()
    assert data["safety_event"] is not None
    assert data["safety_event"]["command"] == "hard_stop"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_invalid_uuid_returns_400(client):
    resp = await client.post(
        "/sessions/not-a-uuid/turn", json={"player_input": "Hello."}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_turn_unknown_session_id_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000002"
    resp = await client.post(
        f"/sessions/{fake_id}/turn", json={"player_input": "Hello."}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_turn_engine_error_returns_502(client, session_id, fake_client, monkeypatch):
    import aurpg.server._store as _store
    import aurpg.server.routes.turns as _turns

    _store._client = fake_client

    def _failing_run_turn(session, player_input, *, client):
        raise RuntimeError("LLM timeout")

    monkeypatch.setattr(_turns, "run_turn", _failing_run_turn)

    resp = await client.post(
        f"/sessions/{session_id}/turn", json={"player_input": "Hello."}
    )
    assert resp.status_code == 502
    assert resp.json()["detail"] == {"error": "engine_timeout", "message": "LLM timeout"}
