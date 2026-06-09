# AGENTS.md

This file provides guidance to Codex and other AI agents when working with code in this repository.

## Project Status

AURPG is in **Phase 4 — Internal Alpha**. The full CLI application is built and tested. Phases 0–3 are complete.

| Phase | Status |
|-------|--------|
| 0 — Spec Hardening | Complete |
| 1 — Evaluation Infrastructure | Complete |
| 2 — Core Engine | Complete |
| 3 — Minimal Viable Interface | Complete |
| 4 — Internal Alpha | Active |

## Development Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Unix:
source .venv/bin/activate

pip install -e ".[dev]"
```

Python 3.11+ required. Run tests with:

```bash
pytest tests/ --ignore=tests/prompts   # offline suite (no API key needed)
pytest tests/                          # full suite (10 live LLM tests skipped without ANTHROPIC_API_KEY)
```

437 tests pass offline. 10 live golden transcript tests require `ANTHROPIC_API_KEY` and are marked `@pytest.mark.live`.

## Architecture

AURPG is a **prompt-as-engine** system. The LLM is the runtime, governed by a structured XML system prompt. A Python application layer manages state, dice, safety, and the player-facing CLI.

### Module layout

| Path | Purpose |
|------|---------|
| `src/aurpg/prompts/aurpg_system_prompt_prototype.xml` | The engine spec — rules, resolution logic, safety, orchestration modes |
| `src/aurpg/prompts/examples/sample_campaign_state.xml` | Reference runtime state |
| `src/aurpg/dice.py` | `OutcomeTier`, `ActionRoll`, `SquadRoll`; seeded and live RNG |
| `src/aurpg/llm.py` | `EngineResponse`, `assemble_prompt`, `call_engine_with_retry`, `make_client` |
| `src/aurpg/safety.py` | `SafetyCommand` enum; pre-LLM gate for X-Card/Rewind/Fast-Forward/Pause/hard_stop |
| `src/aurpg/state/__init__.py` | `CampaignStateXML` dataclass |
| `src/aurpg/state/manager.py` | `CampaignState`, load/save/tick/rewind/mutate |
| `src/aurpg/session.py` | `Session`, `new_session`, `run_turn`, `save_session`, `load_session`, `summarize_recap` |
| `src/aurpg/wizard.py` | `WizardConfig`, `run_wizard`, `config_to_state_xml` |
| `src/aurpg/cli/renderer.py` | Pure rendering: ledger, character sheet, safety banner, options |
| `src/aurpg/cli/game_loop.py` | `play_session` — full turn loop with pause gate and meta-commands |
| `src/aurpg/cli/main.py` | `build_parser`, `cmd_new/play/list`, `main` entry point |

### XML state schema

Five containers inside campaign state XML:

- **`<session_state>`** — metadata, scene context, player stats (stress/momentum/harm), resolution state, safety flags
- **`<resources>`** — attributes (edge/heart/iron/shadow/wits), bonuses, NPC relationships, inventory
- **`<state_machines>`** — progress clocks (standard/danger/racing/linked/mission) and progress tracks
- **`<safety_profile>`** — per-category (horror/health/relationships/social_issues) green/yellow/red consent
- **`<turn_seed>`** — next player intent and expected resolution path (used in fixtures)

### Safety commands

Safety commands are detected **before** the LLM sees the turn, in `src/aurpg/safety.py`. They are never left for the model to notice on its own.

| Command | Effect |
|---------|--------|
| `[X-Card]` | Immediate scene pause; OOC calibration |
| `[Rewind]` | Roll back to previous turn |
| `[Fast-Forward]` | Skip current scene |
| `[Pause]` | Freeze turn loop; only safety commands accepted |
| `!enforce_hard_stop` | Hard session termination |

### Resolution mechanics

**Solo mode**: `Action_Score = min(1d6 + Attribute + Bonuses, 10)` vs. two 1d10 challenge dice. Momentum −6 to +10; burning momentum cancels challenge dice.

**Squad mode**: Nd6 pool (1–4 dice); outcome from highest die (6 = strong hit, 4–5 = weak hit, 1–3 = miss, multiple 6s = critical).

Position (controlled/risky/desperate) and Effect (limited/standard/great) modify consequence severity.

### Orchestration modes

`strict_manual` | `collaborative_consult` | `generative_synthesis` — set during the Campaign Creation Wizard.

## CLI Usage

```bash
aurpg new                     # start a campaign (wizard → game loop)
aurpg play <session-id>       # resume an existing session
aurpg resume <session-id>     # alias for play
aurpg list                    # list all saved sessions
```

Default saves directory: `~/.aurpg/saves/`. Default model: `claude-haiku-4-5-20251001`.

In-session meta-commands: `/quit`, `/sheet`, `/help`, `/recap`.

## Test layout

| Path | Contents |
|------|---------|
| `tests/test_roundtrip.py` | XML parse→mutate→validate round-trip |
| `tests/test_dice.py` | Dice oracle, seeded determinism |
| `tests/test_safety.py` | Safety command gate |
| `tests/test_session.py` | Session lifecycle unit tests |
| `tests/test_wizard.py` | Wizard config validation |
| `tests/integration/test_session_lifecycle.py` | 8-scenario end-to-end lifecycle suite |
| `tests/cli/` | CLI renderer and game loop unit tests |
| `tests/prompts/test_golden_transcripts.py` | 10 live LLM regression tests (`@pytest.mark.live`) |

## Contributing

Use `feat:`, `fix:`, `docs:`, `refactor:`, `chore:` commit prefixes. File issues with `[P0]`/`[P1]`/`[P2]` severity labels. 100-character line limit, full type hints, Black formatting.
