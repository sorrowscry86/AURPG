# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

AURPG is in **pre-alpha / prompt-engineering phase**. The primary artifact is an XML system prompt prototype — no runnable application code exists yet. The design document (`docs/DESIGN.md`) is still being finalized before implementation begins.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"     # pyproject.toml not yet created; install deps as they are added
```

Python 3.11+ is required. PEP 8 applies with a 100-character line limit. Use type hints throughout.

Tests live in `tests/` — no test runner is configured yet (the directory contains only a `.gitkeep`).

## Architecture

AURPG is a **prompt-as-engine** system: the LLM itself is the runtime, governed entirely by a structured XML system prompt. There is no traditional application server yet — the prompt spec, state schema, and evaluation harness *are* the current implementation.

### Key files

| Path | Purpose |
|------|---------|
| `src/aurpg/prompts/aurpg_system_prompt_prototype.xml` | The engine's executable specification — rules, resolution logic, safety modules, orchestration modes |
| `src/aurpg/prompts/examples/sample_campaign_state.xml` | Reference runtime state for evaluation and development |
| `docs/PROMPT_USAGE_GUIDE.md` | How to load the prompt, run evaluation turns, and record pass/fail results |
| `docs/DESIGN.md` | Near-term design targets and planned spec sections |
| `.github/AURPG.agent.md` | Agent persona and mechanic spec used when running the engine architect role |
| `Full Stack Prototyping Concept Proposal_ The Amalgamated Ultimate RPG System.md` | Original strategic vision and mathematical rationale for the dice/clock architecture |

### XML state schema

The session state is divided into five containers in the prompt and campaign state files:

- **`<session_state>`** — campaign metadata, scene context, player stats (stress, momentum, harm), active resolution state (position/effect/move), and safety flags
- **`<resources>`** — attributes (edge/heart/iron/shadow/wits), bonuses, NPC relationships with clock references, and inventory
- **`<state_machines>`** — progress clocks (standard/danger/racing/linked/mission, 4–8 segments) and progress tracks (10 boxes × 4 ticks, rank-scaled)
- **`<safety_profile>`** — per-category (horror/health/relationships/social_issues) green/yellow/red consent settings
- **`<turn_seed>`** — used in examples to describe the next player intent and expected resolution path

### Resolution mechanics (encoded in the prompt)

Two modes coexist in the same prompt:

- **Solo mode**: `Action_Score = min(1d6 + Attribute + Bonuses, 10)` vs. two 1d10 challenge dice. Momentum track −6 to +10; burning momentum cancels challenge dice below the current momentum value.
- **Squad mode**: Nd6 pool (1–4 dice); outcome determined by the highest die (6 = strong hit, 4–5 = weak hit, 1–3 = miss, multiple 6s = critical).

Position (controlled/risky/desperate) and Effect (limited/standard/great) modify consequence severity. Every narrative turn must end with exactly three CYOA options.

### Orchestration modes

The prompt supports three GM-posture modes, set during the Campaign Creation Wizard:
- `strict_manual` — no AI worldbuilding without explicit player approval
- `collaborative_consult` — AI proposes, player canonizes
- `generative_synthesis` — AI auto-drafts world scaffolding from minimal input

### Safety commands (live, parsed mid-session)

`[X-Card]`, `[Rewind]`, `[Fast-Forward]`, `[Pause]`, `!enforce_hard_stop` — these are parsed by the engine in-context; no external code handles them yet.

## Prompt Evaluation Workflow

To test a prompt change:

1. Load `aurpg_system_prompt_prototype.xml` as the system instruction.
2. Load `sample_campaign_state.xml` into context as current game state.
3. Send a player action message.
4. Verify against the contract in `docs/PROMPT_USAGE_GUIDE.md`:
   - Fiction-first ruling with correct resolution mode chosen
   - Explicit state updates (clocks, tracks, stress, momentum)
   - Exactly 3 actionable options returned
   - No banned cliché phrases ("like a physical blow", "shivers down my spine", etc.)
   - Safety commands honored when invoked

The guide contains three canonical evaluation prompts (baseline risky action, flashback, safety interrupt) with expected pass/fail criteria and recorded sample outputs.

## Prompt Engineering Conventions

- XML prompt structure follows three frameworks: **MOLEX** (modular layered sections), **ANEX** (role/constraints/execution/schema separation), **MLRPE** (mission/logic/rules/presentation/examples isolation).
- Hard rules are tagged with IDs (L1–L5) for reference in iteration notes and future tests.
- State changes must always be explicit and printed before or alongside resolution-heavy prose — never implicit.
- Hidden chain-of-thought must never appear in output; translate reasoning into visible artifacts (clock updates, consequence statements, NPC reactions, ruling justifications).
- The output contract for each turn: ledger update → deep-POV prose → exactly three CYOA options + freeform invitation.

## Contributing

Open issues with `[design]` prefix for architectural decisions. Implementation PRs are not yet accepted — see `CONTRIBUTING.md` for current status.
