# AURPG Flutter GUI — Design Spec
_Date: 2026-06-09_

## Overview

Add a Flutter frontend to AURPG backed by a local Python FastAPI server. The server is a thin HTTP adapter over the existing engine — no game logic moves or forks. The existing CLI remains fully functional. Both surfaces drive the same Python modules.

---

## Architecture

```
Flutter app
    │
    │  HTTP (localhost)
    ▼
FastAPI server  (src/aurpg/server/)
    │
    ├── session.py
    ├── wizard.py
    ├── safety.py
    ├── llm.py
    └── state/manager.py
```

- Server lives at `src/aurpg/server/` (new module, thin adapters only).
- Flutter launches (or connects to) the server on startup, polls `GET /health` to confirm liveness, then proceeds.
- Server process lifecycle: Flutter spawns it as a subprocess on desktop; on mobile the server runs in the same process via an embedded Python runtime (deferred — desktop-first).
- All save files remain in `~/.aurpg/saves/` — same format as CLI.

---

## API Contract

### Sessions

| Method | Path | Trigger | Request | Response |
|--------|------|---------|---------|----------|
| `GET` | `/sessions` | Home screen load | — | `[{id, model, last_saved, turn_count}]` |
| `POST` | `/sessions` | Wizard complete | `{wizard_config: {genre, character, safety, orchestration_mode}}` | `{session_id, state: <CampaignState>}` |
| `GET` | `/sessions/{id}/state` | Resume — hydrate HUD | — | `{stress, momentum, harm, clocks, turn_history}` |
| `DELETE` | `/sessions/{id}` | Home swipe-to-delete | — | `{deleted: true}` |

### Turn (hot path)

```
POST /sessions/{id}/turn
Body: {"player_input": "I draw my sword."}

Response:
{
  "raw_text":     "...",
  "options":      ["...", "...", "..."],
  "ledger_block": "[STRESS] 3→4...",
  "state":        {stress, momentum, harm, clocks},
  "safety_event": null | {command, ooc_text}
}
```

Safety gate (`safety.py`) runs **server-side before any LLM call**. The client never needs to detect safety commands itself.

### Health

```
GET /health → {"status": "ok", "version": "0.1.0"}
```

Flutter polls this on startup and on the settings screen.

### Streaming (deferred)

`WS /sessions/{id}/stream` — same request shape as the turn endpoint, response comes as chunks instead of a single object. Feature-flagged in Flutter; off by default until implemented.

---

## UI Screens

### Home

- List of saved sessions; each card: character name, last-saved date, turn count.
- Swipe-to-delete triggers `DELETE /sessions/{id}`.
- FAB → Wizard flow.

### Wizard

- 4-stage form: genre → character → safety profile → orchestration mode.
- Mirrors the existing `wizard.py` stage sequence.
- Submit fires `POST /sessions`; on success navigates to Game screen.
- Validation errors surfaced inline (reusing `validate_config` logic via the server response).

### Game Screen

Layout from top to bottom:

```
┌─────────────────────────────────┐
│  HUD bar                        │  ← stress · momentum · harm · clocks
├─────────────────────────────────┤
│                                 │
│  Narrative pane (scrollable)    │  ← ledger block (distinct style) + raw_text
│                                 │
├─────────────────────────────────┤
│  [ Option A ] [ Option B ] [ C ]│  ← 3 CYOA cards (tappable)
├─────────────────────────────────┤
│  [____ type freely ____] [Send] │  ← freeform input row
└─────────────────────────────────┘
```

- Tapping a CYOA card pre-fills the input field (player can still edit before sending).
- HUD updates after every turn response (from `state` in the turn response body).
- Ledger block rendered in a monospace/accent style above the prose.

### Safety Overlay

- Triggered when `safety_event` is non-null in the turn response.
- Screen dims; a banner drops from the top showing the command name and `ooc_text`.
- Narrative input is fully blocked until the player explicitly dismisses the banner.
- After dismissal, the next turn is sent normally — no special client logic needed.

---

## Project Structure (new files)

```
src/aurpg/server/
├── __init__.py
├── app.py          # FastAPI app, router registration
├── routes/
│   ├── sessions.py # CRUD + state endpoint
│   ├── turns.py    # POST /sessions/{id}/turn (hot path)
│   └── health.py   # GET /health
└── schemas.py      # Pydantic request/response models

gui/                # Flutter project root
├── pubspec.yaml
├── lib/
│   ├── main.dart
│   ├── api/        # HTTP client (Dio or http package)
│   ├── screens/
│   │   ├── home_screen.dart
│   │   ├── wizard_screen.dart
│   │   └── game_screen.dart
│   └── widgets/
│       ├── hud_bar.dart
│       ├── narrative_pane.dart
│       ├── option_cards.dart
│       └── safety_overlay.dart
└── test/
```

---

## Error Handling

- Network errors (server not running): Flutter shows a "Starting engine…" screen and retries `GET /health` for up to 10 seconds; if still unreachable, shows an error with a manual retry button.
- Turn errors (LLM timeout / backoff exhausted): server returns HTTP 502 with `{error: "engine_timeout"}`; Flutter shows an inline retry button in the narrative pane.
- Save errors: surfaced as a toast; game state is not lost (it's in memory until the next successful save).

---

## Out of Scope (this phase)

- Streaming via WebSocket (feature-flagged, off by default).
- Mobile platform (desktop-first: Windows/macOS/Linux).
- Authentication or multi-user support.
- Remote server (server always runs localhost).
- Character sheet screen (accessible via `/sheet` in CLI; deferred for GUI).

---

## Success Criteria

1. Player can complete the full Campaign Creation Wizard and start a game without touching the CLI.
2. All 5 safety commands work correctly — overlay appears, input is blocked, dismissal resumes play.
3. Session save and resume works across app restarts (same save files as CLI).
4. HUD updates correctly after every turn.
5. Existing CLI and tests are unaffected (no changes to engine modules).
