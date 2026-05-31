# AURPG Design Document

> **Status: Prototype in progress**
>
> AURPG is currently defining its prompt-engine architecture before application
> code is built. The first implementation-ready prototype lives at
> [`src/aurpg/prompts/aurpg_system_prompt_prototype.xml`](../src/aurpg/prompts/aurpg_system_prompt_prototype.xml).
> Usage and evaluation guidance lives at
> [`docs/PROMPT_USAGE_GUIDE.md`](PROMPT_USAGE_GUIDE.md), with a sample state at
> [`src/aurpg/prompts/examples/sample_campaign_state.xml`](../src/aurpg/prompts/examples/sample_campaign_state.xml).

---

## Current prototype scope

The XML prompt prototype establishes the initial contract for:

1. **Unified narrative-mechanical resolution** for solo and squad play
2. **Verifiable state machines** for clocks, tracks, and progress moves
3. **Campaign creation orchestration** through a 4-stage onboarding wizard
4. **Safety and consent infrastructure** with live interrupt commands
5. **Prompt-quality controls** for agency, prose, pacing, and hidden-reasoning containment

## Near-term design targets

1. **State schema finalisation** — define canonical runtime fields for scenes, actors, clocks, tracks, and safety settings → **Done:** `src/aurpg/state.py` contains the canonical Python dataclasses
2. **Execution loop refinement** — validate fiction-first move triggering and outcome-to-consequence mapping → in progress via evaluation transcripts
3. **Prompt module boundaries** — separate reusable core rules from genre or campaign overlays → partially addressed by MOLEX/ANEX/MLRPE frameworks in prompt
4. **Session lifecycle design** — add save, resume, recap, and summarisation rules → see section below
5. **Validation strategy** — specify prompt tests, golden transcripts, and future parser checks → **Done:** `src/aurpg/validator.py` + `tests/test_validator.py`

---

## 1. Goals & Non-Goals

### Goals

- Run a full-featured fiction-first text RPG using an LLM as the entire game engine.
- Enforce mechanical integrity (dice resolution, clock advancement, progress tracking) inside the prompt, with no external code required for the core game loop.
- Provide verifiable, inspectable state so players can audit or export session data.
- Support solo and small-squad play (1–4 players) in any genre without hard-coded genre branches.
- Give players strong safety controls — live interrupt commands, calibratable consent matrix — that the engine obeys without exception.

### Non-Goals (current phase)

- A multiplayer server or real-time networking layer.
- Persistent storage (database, cloud sync) beyond what the player manually saves.
- A graphical or browser-based front end.
- Integration with external dice-roller services (dice are simulated inside the LLM context for now).
- Automated model fine-tuning or reinforcement learning on session data.

---

## 2. Architecture Overview

AURPG is a **prompt-as-engine** system. The LLM is the runtime; the XML system prompt is the program.

```
┌─────────────────────────────────────────────────────┐
│                    User Interface                    │
│          (chat client, CLI, future web UI)           │
└───────────────────────┬─────────────────────────────┘
                        │ player message
                        ▼
┌─────────────────────────────────────────────────────┐
│              System Prompt (XML)                     │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│   │ Rules &  │  │ Safety & │  │ Orchestration    │  │
│   │ Mechanics│  │ Consent  │  │ Mode Logic       │  │
│   └──────────┘  └──────────┘  └──────────────────┘  │
│   ┌──────────────────────────────────────────────┐   │
│   │            Fiction-First Loop                │   │
│   │  read intent → check safety → assess fiction │   │
│   │  → choose resolution → resolve → narrate     │   │
│   │  → update state → return 3 CYOA options      │   │
│   └──────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │ engine turn
                        ▼
┌─────────────────────────────────────────────────────┐
│              Campaign State (XML)                    │
│  session_state / resources / state_machines /        │
│  safety_profile                                      │
└─────────────────────────────────────────────────────┘
```

### Component responsibilities

| Component | Responsibility |
|-----------|---------------|
| System prompt XML | Engine rules, resolution logic, safety modules, orchestration modes |
| Campaign state XML | Runtime mutable state: clocks, tracks, stress, inventory, relationships |
| `src/aurpg/state.py` | Canonical Python dataclass schema — source of truth for field names and types |
| `src/aurpg/validator.py` | Offline validation of campaign state XML files |
| `tests/` | Golden-path and regression tests |

---

## 3. State Model

All runtime state is split across four containers, defined in `src/aurpg/state.py` and mirrored in the XML schema.

### `session_state`

| Field group | Key fields |
|-------------|-----------|
| `campaign` | id, title, genre, tone, canon_mode, orchestration_mode |
| `play_state` | mode (solo/squad), scene_id, location, objective, time_marker |
| `player_state` | character_name, stress (0–10), momentum (−6 to +10), harm, load |
| `resolution_state` | position (controlled/risky/desperate), effect (limited/standard/great), move_trigger, stakes |
| `safety_state` | hard_stop, pause, intensity_check |

### `resources`

- **attributes**: Edge, Heart, Iron, Shadow, Wits — each rated 1–4.
- **bonuses**: Transient modifiers from items, relationships, or setup moves.
- **relationships**: Named NPCs with status tags and optional clock references.
- **inventory**: Tagged items that grant bonuses or fictional positioning.

### `state_machines`

**Progress clocks** — 4, 6, or 8 segments. Five types:
- `standard` — general threat, project, or condition
- `danger` — ticks on misses and costly weak hits
- `racing` — two parallel clocks; first to fill wins the race
- `linked` — unlocked only when a prerequisite clock is filled
- `mission` — operation-scope clock; advances on breakthroughs or major complications

**Progress tracks** — 10 boxes × 4 ticks. Rank determines advancement rate:
- Troublesome: 3 boxes per success
- Dangerous: 2 boxes per success
- Formidable: 1 box per success
- Extreme: 2 ticks per success
- Epic: 1 tick per success

Progress move rolls the box count (not an action die) against two 1d10 challenge dice.

### `safety_profile`

Four content categories — horror, health, relationships, social_issues — each set to green (enthusiastic), yellow (veiled/softened), or red (blocked).

---

## 4. LLM Integration

### Prompt loading strategy

1. Load `aurpg_system_prompt_prototype.xml` as the **system instruction** at session start.
2. Load the current `campaign_state.xml` as the first **user message** or as an injected context block, depending on the client's API.
3. From that point, player actions are standard user messages and engine turns are assistant messages.

### Structured output

The engine currently produces semi-structured Markdown inside assistant messages. Planned future work:

- Define a JSON schema for the ledger section of each turn (state delta + roll results).
- Use the LLM's structured output / function-calling mode to emit a machine-readable ledger alongside the narrative prose.
- Keep the narrative prose in a separate field to avoid schema rigidity bleeding into fiction quality.

### Model selection

Any frontier model with a long context window (≥32k tokens) and reliable instruction-following can run the prompt. The engine has been prototype-evaluated manually. Automated evaluation across model families is a future milestone.

### Token budget guidance

| Payload | Estimated tokens |
|---------|-----------------|
| System prompt prototype | ~1,200 |
| Sample campaign state | ~600 |
| One engine turn (output) | ~400–800 |
| Full session (20 turns) | ~20k–30k |

---

## 5. Session Lifecycle

### Initialisation

1. **New campaign** — engine runs the 4-stage Campaign Creation Wizard.
2. **Resumed campaign** — player provides saved campaign state XML; engine reads it and confirms the scene context before accepting the first action.

### Turn loop

```
player action
  → engine: safety check → fiction assessment → resolution choice
  → engine: resolve mechanics + update state
  → engine: narrate consequences (deep POV)
  → engine: return ledger update + 3 CYOA options + freeform invitation
player chooses or types freeform
  → (repeat)
```

### Saving state

The player or a wrapper application saves the updated campaign state XML after each turn. The engine prints the full updated state on request (command: `!print_state`) or after any turn that includes significant state changes.

### Resuming

The player pastes or loads the saved state XML and sends a "Resume" message. The engine:
1. Acknowledges the state.
2. Summarises the last scene beat (no more than two sentences).
3. Re-presents the three options from the last turn, or generates fresh options if context is ambiguous.

### Session end / recap

The engine offers a **Stars and Wishes** debrief:
- Stars: what worked well this session (narrative beats, mechanics, tension arcs)
- Wishes: what the player wants next session (unresolved threads, new directions)

A recap summary is printed covering: scene progression, clock changes, track progress, key NPC moments, and any safety commands invoked.

---

## 6. Game Rules Layer

The rules layer is entirely encoded in the system prompt XML. Key design principles:

- **Fiction-first gate**: a move or roll is only triggered when the fictional situation creates genuine uncertainty or risk — not for every declared action.
- **Position and effect declared before roll**: stakes are explicit before dice are resolved.
- **Momentum as a strategic resource** (solo mode): players decide when to burn momentum before seeing challenge dice results.
- **No scripted branches**: the engine reasons from move descriptions and position/effect to determine consequences; there is no lookup table of pre-written outcomes.
- **Clocks as pressure visualisation**: the engine always updates affected clocks explicitly in the ledger, making threat escalation visible and auditable.

---

## 7. API / Interface Design

No API exists yet. Planned interface tiers:

### Tier 1 — Direct LLM API (current)

Load the system prompt and campaign state directly into an LLM API call. Suitable for developer evaluation and prototype play.

### Tier 2 — Python wrapper (planned)

A thin `aurpg.session.Session` class that:
- Manages prompt and state injection.
- Parses the ledger section of each turn.
- Persists updated state to disk after each turn.
- Exposes `session.act(player_action: str) -> EngineResponse`.

### Tier 3 — HTTP API (future)

A FastAPI service wrapping Tier 2, with endpoints for session management, state export, and replay. Enables front-end clients.

---

## 8. Error Handling & Safety

### Content safety

- Red-category content is blocked at the prompt level; the engine refuses to generate it.
- Yellow-category content is softened or faded to black per category guidance.
- Live safety commands (`[X-Card]`, `[Rewind]`, `[Fast-Forward]`, `[Pause]`, `!enforce_hard_stop`) are the primary runtime safety mechanism.
- The system prompt's highest-priority rule (L1) prevents the engine from overriding player agency.

### Bad model output

Problems to detect and handle in future validation tooling:

| Failure mode | Detection | Recovery |
|--------------|-----------|----------|
| Wrong number of CYOA options | Count assertion on parsed output | Re-prompt with explicit instruction |
| Missing state update | Regex/schema check on ledger section | Flag to player; re-prompt |
| Banned cliché phrases | Blocklist scan | Re-prompt requesting fresh language |
| Safety command ignored | Check `safety_state` fields in output | Re-inject command with escalated priority |
| Hidden chain-of-thought leaked | Pattern match on `<think>` or similar tags | Strip or re-prompt |

### XML validation

`src/aurpg/validator.py` checks campaign state files for schema conformance before loading them into a session. Run it before every session start when using externally sourced state files.

---

## 9. Testing Strategy

### Current

- `tests/test_validator.py` — 7 unit tests covering happy path, parse errors, required fields, enum values, numeric ranges.
- Manual golden-path evaluation — three canonical prompts documented in `docs/PROMPT_USAGE_GUIDE.md`.

### Planned

| Test tier | Description | Tool |
|-----------|-------------|------|
| Unit | State model logic (clock ticking, track advancement, progress move scoring) | pytest |
| Schema | Validate all bundled XML files pass the validator | pytest |
| Golden transcript | Load prompt + state, run canonical player action, assert output contract | pytest + LLM API |
| Regression | Re-run golden transcripts after prompt edits; diff ledger sections | pytest + snapshot |
| Cliché scan | Assert banned phrases absent from all generated outputs | pytest |

### Output contract assertions (per turn)

- Ledger update present before or alongside resolution prose.
- Exactly three CYOA options.
- No banned cliché phrases.
- `safety_state.hard_stop` honoured when `true`.
- State delta values are numerically consistent with prior state.

---

## 10. Roadmap

| Milestone | Deliverables | Status |
|-----------|-------------|--------|
| M0 — Prompt prototype | System prompt XML, sample campaign state, usage guide | Done |
| M1 — Schema & tooling | `pyproject.toml`, `state.py`, `validator.py`, basic tests | Done |
| M2 — Design document | All ten design sections complete | Done |
| M3 — Extended prompt | Canonical attributes, stress/harm rules, serialization, example transcripts | In progress |
| M4 — Session wrapper | `aurpg.session.Session` class, state persistence, `act()` API | Planned |
| M5 — Golden tests | Automated golden-transcript tests against LLM API | Planned |
| M6 — HTTP API | FastAPI wrapper, session management endpoints | Planned |
| M7 — Front end | Browser or TUI client for end-user play | Future |
