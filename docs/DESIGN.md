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

1. **State schema finalisation** — define canonical runtime fields for scenes, actors, clocks, tracks, and safety settings
2. **Execution loop refinement** — validate fiction-first move triggering and outcome-to-consequence mapping
3. **Prompt module boundaries** — separate reusable core rules from genre or campaign overlays
4. **Session lifecycle design** — add save, resume, recap, and summarisation rules
5. **Validation strategy** — specify prompt tests, golden transcripts, and future parser checks

---

## 1. Goals & Non-Goals

### Goals

- **Prompt-as-engine**: The LLM is the runtime. The XML system prompt encodes all rules, resolution logic, safety guardrails, and output contracts. No application server is required to play.
- **Unified resolution**: A single engine handles PbtA-style conversational move triggers, FitD position/effect consequence logic, and Ironsworn-style solo resolution without the player switching modes manually.
- **Verifiable state**: Every mechanical action produces explicit, inspectable state updates (clocks, tracks, stress, momentum). The state is never implicit or hidden in prose.
- **Safety-first**: Consent limits are captured before play begins and enforced throughout. Safety commands are parsed client-side before the LLM ever sees the turn.
- **Platform-agnostic entry**: The prompt-only form works in any LLM chat interface. The Python application layer wraps it for structured sessions without requiring a new interface.
- **Closed alpha readiness**: The system must support 3–5 external testers playing unassisted sessions within 6 months of the roadmap start date.

### Non-Goals

- **Multiplayer server**: Real-time multi-player session management is out of scope for v1.
- **Persistent hosted character sheets**: No web storage, database, or account system in v1.
- **Visual or graphical UI**: Text output only. A richer UI is a post-alpha concern.
- **Rules enforcement without an LLM**: The engine is not designed to function without a capable language model; it does not fall back to a deterministic rules parser.
- **Coverage of all TTRPG systems**: AURPG defines its own unified ruleset derived from PbtA/FitD/Ironsworn. It is not a generic TTRPG adapter.
- **Real-time dice rolling service**: Dice are resolved inside the LLM context. An external dice oracle is a nice-to-have for transparency, not a core requirement.

---

## 2. Architecture Overview

AURPG has four layers. The prompt and state layers are functional today; the application and interface layers are built during Phases 1–3 of the roadmap.

```
┌──────────────────────────────────────────────────────┐
│  Player Interface  (CLI: aurpg new / play / resume)  │
├──────────────────────────────────────────────────────┤
│  Session Manager                                     │
│  (wizard · turn loop · save · resume · recap)        │
├──────────────────────────────────────────────────────┤
│  LLM Integration                                     │
│  (prompt assembly · API call · response parse)       │
├──────────────────────────────────────────────────────┤
│  State Manager   │   Safety Parser   │  Dice Oracle  │
│  (load/validate/ │   (pre-LLM inter- │  (seeded /    │
│   mutate/persist)│    rupt detection)│   live CSPRNG)│
└──────────────────────────────────────────────────────┘
         │                                  │
  Anthropic API                    Disk (JSON / XML)
  (LLM runtime)                    (session persistence)
```

**Data flow for a single turn:**

1. Player types an action.
2. Safety Parser scans for interrupt commands before anything reaches the LLM.
3. Dice Oracle resolves any dice expressions needed to assemble the prompt context.
4. LLM Integration assembles the prompt: system XML + serialized state XML + condensed turn history + player message.
5. Anthropic API returns a structured response.
6. Response is parsed and validated against the output contract.
7. State Manager applies mutations (clock advances, stress changes, momentum updates).
8. Rendered output (ledger + prose + three options) is shown to the player.
9. Session is persisted to disk.

---

## 3. State Model

Session state is divided into five XML containers. The `<turn_seed>` container is used only in evaluation scenarios and is not present in live session files.

### `<session_state>`

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `campaign.id` | string | non-empty | Unique session identifier |
| `campaign.title` | string | non-empty | Campaign display name |
| `campaign.genre` | string | non-empty | e.g. `cyberpunk_heist`, `dark_fantasy` |
| `campaign.tone` | string | non-empty | e.g. `high_tension_character_driven` |
| `campaign.canon_mode` | enum | `strict_continuity` \| `loose` | How strictly prior events bind future narration |
| `campaign.orchestration_mode` | enum | `strict_manual` \| `collaborative_consult` \| `generative_synthesis` | GM-assistance posture |
| `play_state.mode` | enum | `solo` \| `squad` | Determines resolution formula |
| `play_state.scene_id` | string | non-empty | Scene identifier for continuity |
| `play_state.location` | string | non-empty | Current fictional location |
| `play_state.objective` | string | non-empty | Active scene objective |
| `play_state.time_marker` | string | optional | In-world time reference |
| `player_state.character_name` | string | non-empty | — |
| `player_state.deep_pov` | bool | always `true` | Reserved; controls narration frame |
| `player_state.stress` | int | 0–12 | 12 = incapacitated |
| `player_state.momentum` | int | −6 to +10 | −6 = minimum (cannot burn negative momentum) |
| `player_state.harm` | string \| null | optional | Descriptive harm tag(s) |
| `player_state.load` | enum | `light` \| `normal` \| `heavy` \| `overloaded` | Affects gear availability |
| `resolution_state.position` | enum | `controlled` \| `risky` \| `desperate` | Consequence severity multiplier |
| `resolution_state.effect` | enum | `limited` \| `standard` \| `great` | Success scale |
| `resolution_state.move_trigger` | string \| `none` | optional | Active move name |
| `resolution_state.stakes` | string | optional | Narrative summary of what's at risk |
| `safety_state.hard_stop` | bool | — | True while `!enforce_hard_stop` is active |
| `safety_state.pause` | bool | — | True while `[Pause]` OOC mode is active |
| `safety_state.intensity_check` | enum | `none` \| `pending` \| `resolved` | Check-in state |

### `<resources>`

| Container | Field | Type | Constraints |
|-----------|-------|------|-------------|
| `attributes` | `name` | enum | `edge` \| `heart` \| `iron` \| `shadow` \| `wits` |
| `attributes` | `value` | int | 1–4 (campaign start); may be modified by advancement |
| `bonuses` | `source` | string | Free text describing the bonus origin |
| `bonuses` | `value` | int | +1 or +2 typically |
| `relationships` | `npc` | string | NPC name |
| `relationships` | `status` | string | Free text (e.g. `uneasy_ally`, `actively_hunting`) |
| `relationships` | `clock_ref` | string \| empty | ID of associated clock, if any |
| `inventory` | `name` | string | Item name |
| `inventory` | `tags` | string | Comma-separated capability tags |

### `<state_machines>`

**Clocks**

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | string | unique, kebab-case prefix `clk-` |
| `name` | string | display name |
| `type` | enum | `standard` \| `danger` \| `racing` \| `linked` \| `mission` |
| `segments` | enum | `4` \| `6` \| `8` |
| `filled` | int | 0 to `segments` (filled = segments → clock complete) |
| `linked_to` | string \| empty | prerequisite clock id; this clock cannot tick until linked clock is complete |

**Progress Tracks**

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | string | unique, kebab-case prefix `trk-` |
| `name` | string | display name |
| `rank` | enum | `troublesome` \| `dangerous` \| `formidable` \| `extreme` \| `epic` |
| `boxes_filled` | int | 0–10 |
| `ticks_in_current_box` | int | 0–3 (4 ticks fills a box) |

Progress on success by rank: troublesome → 3 boxes, dangerous → 2 boxes, formidable → 1 box, extreme → 2 ticks, epic → 1 tick.

### `<safety_profile>`

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | enum | `horror` \| `health` \| `relationships` \| `social_issues` |
| `status` | enum | `green` \| `yellow` \| `red` |
| `guidance` | string | Free text instruction injected into prompt context |

Semantics: `green` = enthusiastic engagement; `yellow` = veiled, softened, or fade-to-black treatment; `red` = blocked entirely.

### `<turn_seed>` (evaluation use only)

| Field | Type | Notes |
|-------|------|-------|
| `player_intent` | string | Free-text description of the intended player action |
| `expected_resolution_path` | string | Human-authored resolution notes for golden transcript matching |

`<turn_seed>` must not appear in production session files; it exists only in evaluation fixtures.

---

## 4. LLM Integration

### Model selection

| Use case | Recommended model |
|----------|------------------|
| Live play (speed-optimized) | `claude-sonnet-4-6` |
| Evaluation / quality gate | `claude-opus-4-8` |
| Rapid CI mock validation | Cached cassette responses (no API call) |

### Prompt assembly

The prompt sent to the API has three parts, assembled in order:

1. **System message** — the full `aurpg_system_prompt_prototype.xml` content wrapped in `<aurpg_system_prompt>` tags. This is static per version and should be cached with the Anthropic prompt-caching API to reduce token costs.
2. **State injection** — the current `<aurpg_campaign_state>` XML serialized inline, immediately after the system prompt.
3. **Conversation history** — the condensed turn history (see Session Lifecycle for recap rules), followed by the player's current message as the final user turn.

### Structured output

The engine response must follow the output contract in this order:

```
[LEDGER]
<explicit state updates: clocks ticked, tracks marked, stress/momentum changed>

[PROSE]
<deep-POV narrative of the turn outcome>

[OPTIONS]
1. <first choice>
2. <second choice>
3. <third choice>
Or tell me what you do.
```

The application layer parses this structure to separate display components and extract state mutations.

### Token budget and caching

- Cache the static system prompt with Anthropic's prompt caching feature.
- Track cumulative input tokens per session. When the rolling context (state + history) exceeds 80% of the model's context limit, trigger a recap summarization turn.
- The recap turn asks the model to condense turn history into a narrative summary; the summary replaces the raw turn log.

---

## 5. Session Lifecycle

```
Pre-session
    │
    ▼
[aurpg new] ──► Campaign Creation Wizard (4 stages)
                    Stage 1: System & Metadata
                    Stage 2: Character Generation
                    Stage 3: Safety Checklist
                    Stage 4: Orchestration Mode
    │
    ▼
Active Session ◄────────────────────────────────┐
    │                                           │
    ├── Receive player input                    │
    ├── Safety Parser (pre-LLM scan)            │
    │       ├── Safety command detected ──► OOC calibration ──► resume or rewind
    │       └── No interrupt → continue        │
    ├── Assemble prompt                         │
    ├── LLM API call                            │
    ├── Parse & validate response               │
    ├── Apply state mutations                   │
    ├── Render to player                        │
    ├── Persist session to disk                 │
    └── Check context length                   │
            ├── Under 80% limit ───────────────►│ (loop)
            └── Over 80% limit → Recap turn ───►│
    │
    ├── [Pause] ──► OOC mode ──► [resume] ──► Active Session
    ├── [aurpg quit] ──► Save ──► Suspended
    │
    ▼
Suspended
    │
    └── [aurpg resume] ──► load state + inject recap context ──► Active Session
    │
    └── [/end in-session] ──► Aftercare Debrief (Stars & Wishes)
    │
    ▼
Ended
```

### Save format

Sessions are persisted as JSON files in `~/.aurpg/sessions/<session-id>.json`:

```json
{
  "session_id": "...",
  "character_name": "...",
  "campaign_title": "...",
  "last_played": "ISO-8601 timestamp",
  "state": { /* all five XML containers as nested JSON */ },
  "turn_history": [ /* array of {player, engine} message pairs, condensed after recap */ ]
}
```

### Resume

On resume, the session manager:
1. Loads and validates the JSON file against the Pydantic schema.
2. Serializes the state back to XML for prompt injection.
3. Prepends a `<recap>` block to the conversation history summarizing the last session.
4. Enters the turn loop.

### Recap trigger

When accumulated input tokens (system + state + history) exceed 80% of the model context limit, the engine runs a single summarization turn: the model is asked to write a 150–300 word narrative recap of events so far. The recap replaces the raw turn log and is injected at the top of subsequent conversation history.

---

## 6. Game Rules Layer

All rules live inside `aurpg_system_prompt_prototype.xml`. The Python application layer treats them as a black box — it does not re-implement rules in code. The application layer's only mechanical responsibilities are dice rolling and state schema validation.

### Fiction-first loop

The engine must not call for a roll unless the action creates genuine uncertainty, risk, opposition, or meaningful cost. Consequence-free narration never triggers a roll. This is Directive L2.

### Solo resolution

```
Action_Score = min(1d6 + Attribute + Bonuses, 10)
Compare against two 1d10 challenge dice:
  Strong hit  →  beats both dice
  Weak hit    →  beats one die
  Miss        →  beats neither die
```

Momentum mechanics:
- **Burning momentum**: Spend current momentum value to cancel one challenge die equal to or below the momentum value. Momentum then resets per campaign defaults (typically to +2).
- **Negative momentum**: If momentum is negative when rolling, cancel any action-die face matching the absolute value of momentum before reading the result.

### Squad resolution

```
Roll Nd6 (N = 1–4, set by scale/teamwork/setup quality)
Read the highest single die:
  Critical (multiple 6s)  →  strong hit + bonus
  Strong hit              →  one 6
  Weak hit                →  4 or 5
  Miss                    →  1 to 3
```

### Flashback

| Prep complexity | Stress cost |
|----------------|-------------|
| Simple, plausible | 1 |
| Complex, requires planning | 2 |
| Elaborate or unlikely | 3 |

Resolve immediately; update stress; grant concrete advantage or clarify fiction before returning to the current scene.

### Position × Effect consequence matrix

|  | Limited effect | Standard effect | Great effect |
|--|---------------|-----------------|--------------|
| **Controlled** | Minor cost or delay | Clean success | Success + bonus |
| **Risky** | Partial success + cost | Success + standard cost | Success + reduced cost |
| **Desperate** | Hard choice or setback | Success + severe cost | Success + notable cost |

Misses always inflict consequence first; success does not occur unless a move explicitly allows it.

### Progress clocks

| Type | Ticking rule |
|------|-------------|
| Standard | Advance on relevant action outcomes or time passage |
| Danger | Tick on miss; tick on weak hit when fiction escalates threat |
| Racing | Parallel clocks; first to fill wins the race |
| Linked | Does not tick until prerequisite clock is filled |
| Mission | Advances only on mission-scale events |

### Progress tracks

10 boxes × 4 ticks per box. Advancement on a successful action:

| Rank | Progress on success |
|------|-------------------|
| Troublesome | 3 boxes |
| Dangerous | 2 boxes |
| Formidable | 1 box |
| Extreme | 2 ticks |
| Epic | 1 tick |

**Progress Move**: When resolving a long-form objective, roll the count of filled boxes against two 1d10 challenge dice. No action die is used. Strong/weak/miss outcomes apply as normal.

---

## 7. API / Interface Design

### CLI (Phase 3)

```
aurpg new                 Start Campaign Creation Wizard; save and enter play
aurpg play <session-id>   Enter the turn loop for an existing session
aurpg resume              Interactive session picker; loads and resumes
aurpg list                Show all saved sessions with timestamps and scene summaries
aurpg quit                Save session and exit gracefully
```

In-session slash commands (available during the turn loop):

```
/sheet     Print the full character sheet (attributes, bonuses, stress, momentum, harm, inventory)
/clocks    Print all active clocks and progress tracks with current fill state
/save      Force-save the session without ending it
/end       Trigger the aftercare debrief and close the session cleanly
```

In-session safety commands (intercepted before the LLM):

```
[X-Card]              Stop; remove unsafe element; restabilize; ask for new direction
[Rewind]              Roll back to a prior state index; summarize what remains canon
[Fast-Forward]        Skip sensitive detail; preserve consequences; resume at next beat
[Pause]               Open OOC calibration mode; fiction is frozen
!enforce_hard_stop    Terminate current action path immediately; wait for new instructions
```

### REST API (post-alpha)

A thin HTTP wrapper around the session manager will be defined after the CLI is stable. Endpoints will mirror CLI operations: `POST /sessions`, `POST /sessions/{id}/turns`, `GET /sessions/{id}/state`, `DELETE /sessions/{id}`.

---

## 8. Error Handling & Safety

### Safety command handling

Safety commands are **always detected client-side** in `src/aurpg/safety.py` before the player's message is sent to the LLM. The engine never relies on the model to recognize a safety interrupt.

| Command | Handler action |
|---------|---------------|
| `[X-Card]` | Freeze turn loop; emit OOC calibration prompt; wait for player redirection |
| `[Rewind]` | Load the state snapshot at the requested index; emit canon summary |
| `[Fast-Forward]` | Emit skip acknowledgment; advance scene to next meaningful beat |
| `[Pause]` | Enter OOC mode; print pause banner; wait for `/resume` |
| `!enforce_hard_stop` | Set `safety_state.hard_stop = true`; terminate turn loop; await new instructions |

### LLM API errors

| Error type | Response |
|------------|----------|
| Network timeout / 5xx | Exponential backoff retry (max 4 attempts: 2s / 4s / 8s / 16s) |
| Malformed / missing output contract sections | Retry up to 3 times with an explicit contract reminder prepended to the prompt |
| Rate limit (429) | Backoff per Anthropic retry-after header |
| Persistent failure after retries | Surface error to player; offer to save session and exit |

### Output contract violations

The response parser checks for:
- Exactly 3 options present
- No first-person player-character actions authored by the engine (L1 violation)
- No banned cliché phrases
- Explicit state ledger block present on resolution turns

Violations are logged. In live play, the turn is retried once with a constraint reinforcement injection. If the violation persists, the raw response is shown with a warning banner.

### State corruption

- All state mutations are validated against Pydantic schemas before writing.
- Turn history is append-only; [Rewind] does not delete entries — it sets a replay pointer.
- If a session file fails schema validation on load, the last valid checkpoint (one turn prior) is offered.

### Content policy (red-category blocking)

When a `<content_category>` has `status="red"`, the prompt instruction explicitly tells the model to refuse generation in that domain. Red-category blocks are enforced at the prompt level; the safety parser additionally flags any player input that clearly targets a red domain before it reaches the model.

---

## 9. Testing Strategy

### Three tiers

**Tier 1 — Unit tests** (`tests/unit/`): No LLM calls. No network.
- Dice oracle: verify distribution, seeded reproducibility, all roll expressions
- State schema: Pydantic validation accepts valid state, rejects invalid values
- State parser: XML → Pydantic → XML round-trip for all five containers
- Safety parser: correctly identifies all five safety command tokens, including inline placement in longer messages

**Tier 2 — Integration tests** (`tests/integration/`): No live LLM calls. Uses mocked or cassette-recorded API responses.
- Full session lifecycle: wizard → 5 turns → save → resume → 5 more turns → aftercare debrief
- State mutation correctness: each turn result produces the expected state delta for fixed dice seeds
- Safety interrupt lifecycle: each of the five commands triggers the correct handler and correctly resumes or terminates
- Recap trigger: session compresses history correctly at the 80% token threshold

**Tier 3 — Evaluation tests** (`tests/evaluation/`): Live LLM calls. Requires `ANTHROPIC_API_KEY`.
- 10 golden transcript scenarios covering every mechanic (see ROADMAP Phase 0 for the full list)
- Output contract validation: ledger present, exactly 3 options, no banned phrases, correct resolution mode
- LLM judge: a secondary model call evaluates prose quality, agency preservation, and fictional coherence

### CI strategy

| Trigger | Tests run | LLM calls |
|---------|-----------|-----------|
| Pull request | Tier 1 + Tier 2 (mocked) | None (fork-safe) |
| Merge to `main` | Tier 1 + Tier 2 + Tier 3 (live) | Yes |
| Nightly schedule | Tier 3 only (live) | Yes — detects model drift |

Evaluation tests skip gracefully via `pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"))` so PR runs from forks never fail on missing secrets.

---

## 10. Roadmap

See [`docs/ROADMAP.md`](ROADMAP.md) for the full six-phase plan from current spec to closed player alpha, including per-phase task checklists, exit criteria, estimated durations, and a risk/mitigation matrix.

**Summary timeline**: ~5–6 months from spec hardening to closed player testing.
