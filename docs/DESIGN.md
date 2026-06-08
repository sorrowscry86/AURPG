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

## Goals and Non-Goals

### Goals

- Run a complete solo or squad RPG session from campaign creation to session end using only an LLM and a structured XML system prompt.
- Produce fiction-first narrative output that is mechanically verifiable: every consequence traces to an explicit dice resolution and a state update.
- Maintain persistent, inspectable game state across an entire session without external memory or database support.
- Enforce safety and consent contracts in real time through in-context command parsing, without external moderation infrastructure.
- Remain model-agnostic: the prompt should produce correct behaviour on any reasoning-capable LLM that supports system instructions and 32k+ context.

### Non-Goals

- Replacing dedicated TTRPG virtual tabletops (Roll20, Foundry) for visual, multi-user, or real-time play.
- Implementing a persistent server, user accounts, or session storage outside the LLM context window.
- Supporting more than one active player character per session in this version (multi-PC squad play is a future expansion).
- Generating or managing visual assets, audio, or map layouts.
- Enforcing game balance through hard-coded outcome tables — balance is achieved through probability tuning and GM-posture rules, not branching logic.

---

## Architecture Overview

AURPG is a **prompt-as-engine** architecture. The LLM is the entire runtime. There is no application server, no database, and no external game logic. The three key layers are:

```
┌─────────────────────────────────────────────────┐
│  System Prompt (XML)                            │
│  ├─ Hard rules (L1–L5)                          │
│  ├─ Resolution modules (solo / squad / clocks)  │
│  ├─ Output format modules (ledger / somatic)    │
│  ├─ Safety and consent modules                  │
│  └─ Orchestration modes                         │
├─────────────────────────────────────────────────┤
│  Campaign State (XML, injected into context)    │
│  ├─ session_state (scene, player, resolution)   │
│  ├─ resources (attributes, inventory, bonds)    │
│  ├─ state_machines (clocks, progress tracks)    │
│  └─ safety_profile                              │
├─────────────────────────────────────────────────┤
│  Player Turn (user message)                     │
│  └─ Declared action, intent, or safety command  │
└─────────────────────────────────────────────────┘
         ↓ LLM resolves per rules_modules ↓
┌─────────────────────────────────────────────────┐
│  Engine Turn (assistant message)                │
│  ├─ Ledger update (state delta)                 │
│  ├─ Narrative prose (deep-POV, somatic-first)   │
│  └─ Exactly 3 CYOA options + freeform invite    │
└─────────────────────────────────────────────────┘
```

**No branching code.** The LLM reads the rules from the system prompt, evaluates the fiction, applies the resolution logic in-context, and produces structured output. Mechanical correctness is enforced by the prompt's hard rules and verified by the evaluation harness in `docs/PROMPT_USAGE_GUIDE.md`.

**Future compiler layer.** A planned prompt compiler will accept the XML modules and campaign state as inputs and assemble the final prompt string for any target model, handling token budget, module selection, and schema versioning. This is not yet implemented.

---

## State Model

All game state is represented as XML attributes and elements in the `aurpg_campaign_state` document. State is divided into five containers:

### `session_state`

Runtime context for the current scene and resolution. Fields:

| Field | Type | Description |
|---|---|---|
| `campaign.id` | string | Unique campaign identifier |
| `campaign.orchestration_mode` | enum | `strict_manual` / `collaborative_consult` / `generative_synthesis` |
| `play_state.mode` | enum | `solo` / `squad` |
| `play_state.scene_id` | string | Current scene label |
| `player_state.stress` | int 0–10 | Accumulated stress; breaks at 10 |
| `player_state.momentum` | int −6–+10 | Momentum buffer for outcome upgrade |
| `player_state.harm` | string | Active harm label(s) or `none` |
| `resolution_state.position` | enum | `controlled` / `risky` / `desperate` |
| `resolution_state.effect` | enum | `limited` / `standard` / `great` |
| `safety_state.hard_stop` | bool | `!enforce_hard_stop` active |
| `safety_state.pause` | bool | `[Pause]` OOC mode active |

### `resources`

Character capabilities and relationships. Attributes (edge / heart / iron / shadow / wits) hold integer values set during campaign creation. Bonuses are transient modifiers from items or setup. Relationships track NPC status and link to relevant clocks.

### `state_machines`

All progress clocks and progress tracks. Each clock has a `filled` counter against its `segments` cap. Each track has `boxes_filled` (0–10) and `ticks_in_current_box` (0–3). The engine advances these explicitly every turn.

### `safety_profile`

Per-category consent settings (horror / health / relationships / social_issues) with green / yellow / red status. The engine reads this before narrating any content in a sensitive category and soft-pedals or blocks it according to the active setting.

### `turn_seed` (evaluation use only)

Present only in test fixtures. Describes the intended player action and expected resolution path for golden-transcript evaluation.

---

## LLM Integration

### Prompt assembly

The session is initialised by loading two documents into the model context:

1. **System prompt** (`aurpg_system_prompt_prototype.xml`) — loaded as the system instruction.
2. **Campaign state** (`aurpg_campaign_state.xml`) — injected as the first user or system message, clearly labelled as current game state.

The system prompt is static for the session. The campaign state is mutable; the engine's output updates it in-context and the player or tooling exports updated state as needed.

### Model requirements

- Minimum 32k context window (128k+ recommended for long campaigns with summary history).
- Instruction-following fidelity sufficient to respect hard rules L1–L5 consistently.
- Structured output: the engine must produce the ledger line, resolution line, prose, and three options in order every turn.

### Token budget management

The note-insert rule (every 4 turns) and session-summary rule (every 8 turns or on scene change) are the primary tools for managing context growth. The summary crystallises prior continuity into a compact paragraph; the note insert refreshes active clock state without re-reading the full state block.

### Dice resolution

The engine simulates dice rolls using its own sampling during inference. There is no external dice service. The player may override a roll by stating values explicitly; the engine accepts player-declared results and resolves from them.

---

## Session Lifecycle

```
Boot → Campaign Creation Wizard → Scene Initialisation
  → [ Turn Loop ] → Scene Transition → [ Turn Loop ] → ...
    → Session End → Stars & Wishes debrief → State Export
```

### Boot

Engine receives the system prompt and any pre-existing campaign state. If no state exists, the Campaign Creation Wizard runs through its four stages before the first scene.

### Campaign Creation Wizard

Four stages, each gated on player confirmation:

1. **System and Metadata** — genre, tone, scale, play mode.
2. **Character Generation** — protagonist concept, attributes, bonds, inventory, starting pressures.
3. **Safety Checklist** — green / yellow / red boundaries per content category.
4. **Orchestration Mode** — GM-posture locked; play begins.

### Turn Loop

Each turn:
1. Player declares action (or safety command).
2. Engine checks safety state first (L1 / hard stop / pause).
3. Engine applies fiction-first loop (fiction → move trigger → resolution → state update → prose → options).
4. At turn 4, 8, 12, … a note-insert ledger refresh is delivered.
5. At turn 8, 16, … or on scene transition, a session summary is crystallised.

### Scene Transition

On a major narrative beat, location shift, or player-initiated time jump:
- Engine closes the current scene with a summary paragraph.
- Engine updates scene fields in `play_state`.
- Clock and track states carry forward.

### Session End

Triggered by player request or `[Fast-Forward]` to end of session:
- Stars and Wishes debrief offered.
- Full state export produced in XML.
- Any unresolved clocks and tracks noted for next session.

---

## Game Rules Layer

Rules are enforced entirely through the prompt's `<rules_modules>` and `<output_format_modules>` sections. There is no hard-coded branching, no external rule lookup, and no validation outside the LLM context.

### Mechanics hierarchy

1. **Hard rules (L1–L5)** — always applied, cannot be overridden by narrative context.
2. **Fiction-first loop** — determines whether a move fires before any roll logic runs.
3. **Attribute and resolution rules** — define how scores are calculated and outcomes mapped.
4. **Position / effect matrix** — modifies consequence severity based on scene framing.
5. **Clock and track rules** — govern how state machines advance each turn.
6. **Output format rules** — govern ledger, somatic-first protocol, and choice count.

### Genre overlays (planned)

The system prompt currently bundles all rules in a single XML document. Future versions will split the core rules (resolution, clocks, safety) from genre-specific overlays (e.g., cyberpunk setting tags, relationship ladder for social play, injury-debuff tables for tactical combat). Overlays will be injected as additional context blocks alongside the core system prompt.

---

## Error Handling and Safety

### Content safety

Safety is the highest-priority module, evaluated before any fiction is generated each turn. The consent matrix governs content at the category level. Live safety commands override all other rules immediately.

| Command | Effect |
|---|---|
| `[X-Card]` | Remove last generated content, restabilise scene, request redirect. |
| `[Rewind]` | Roll back narrative to agreed prior state, restart. |
| `[Fast-Forward]` | Fade sensitive content, preserve consequences, resume at next beat. |
| `[Pause]` | Freeze fiction, open OOC calibration exchange. |
| `!enforce_hard_stop` | Terminate current action path, wait for new instruction. |

### Model output errors

The prompt's hard rules provide the primary defence against malformed output, but LLM behaviour is non-deterministic. The evaluation harness (`PROMPT_USAGE_GUIDE.md`) defines the pass criteria for each turn. Common failure modes and mitigations:

| Failure | Mitigation |
|---|---|
| Fewer or more than 3 options returned | Repeat the L5 rule at the note-insert point; OOC correction. |
| State not updated explicitly | L4 mandate in every resolution step; player OOC correction. |
| Banned cliché phrases in prose | `<creative_tropes_mandate>` enforces a scrub pass; player correction reinforces the pattern. |
| Hidden chain-of-thought leaked | L3 rule; player correction removes the pattern from context. |
| Safety command not parsed | Retry with explicit command repetition; escalate to `!enforce_hard_stop`. |

### Out-of-context player input

When the player sends ambiguous, out-of-game, or non-action messages, the engine defaults to asking a clarifying question rather than inventing fiction (matching `strict_manual` posture). In `generative_synthesis` mode, the engine may propose a scene direction and ask for confirmation.

---

## Testing Strategy

### Current state

Testing is manual and transcript-based. The three canonical evaluation prompts in `docs/PROMPT_USAGE_GUIDE.md` define the baseline pass criteria. Results are recorded in the guide's evaluation table.

### Planned test levels

**Level 1 — Golden transcript tests**

Each test loads the system prompt + sample campaign state, sends a canonical player action, and asserts:
- Ledger line format matches `[SCENE] ... [STRESS] ...` pattern.
- A resolution line is present with move name, attribute, position/effect, and outcome tier.
- Exactly 3 numbered options appear before the freeform invite.
- No banned phrase appears in the prose section.
- State delta values match expected values (clock fills, stress, momentum).

**Level 2 — Edge-case prompts**

Cover: momentum burn, linked clock unlock, progress move on an epic-rank track, consecutive safety commands, scene transition with summary injection, squad mode critical.

**Level 3 — Session lifecycle tests**

Full session from Campaign Creation Wizard through scene transition through Stars and Wishes debrief. Assert that all four wizard stages complete, that the state export round-trips correctly, and that the session summary appears at the expected turn intervals.

### Test infrastructure (planned)

Tests will live in `tests/prompts/`. Each test is a YAML fixture specifying:
- `system_prompt_path`
- `campaign_state_path`
- `player_input`
- `expected_patterns` (regex list)
- `expected_state_delta` (field: value map)
- `banned_patterns` (regex list)

A pytest harness will load fixtures, call the LLM API, and evaluate the response against each field. The harness is not yet implemented.

---

## Roadmap

### Phase 0 — Prompt specification (current)

- [x] XML system prompt prototype (v0.2)
- [x] Sample campaign state (Neon Ash Protocol)
- [x] Evaluation harness and canonical test prompts
- [x] Canonical attributes, stress/recovery, harm tracks, serialization rules
- [x] Example transcripts for solo, squad, flashback, progress move, safety interrupts
- [ ] Finalize DESIGN.md (this document — in progress)
- [ ] pyproject.toml and project scaffolding
- [ ] Automated golden-transcript test harness

### Phase 1 — Prompt hardening

- [ ] Squad mode multi-character coordination examples
- [ ] Genre overlay prototype (cyberpunk module extracted from core)
- [ ] Session lifecycle full golden transcript (campaign creation → debrief)
- [ ] State round-trip export/import validation

### Phase 2 — Evaluation harness

- [ ] pytest fixture runner calling LLM API
- [ ] Automated banned-phrase detection
- [ ] State delta assertion framework
- [ ] CI integration for regression testing on prompt changes

### Phase 3 — Thin application layer

- [ ] Python CLI wrapper: load prompt + state, send player input, display output, auto-export state
- [ ] State persistence to local file between turns
- [ ] Optional dice service integration (replace in-context dice simulation)

### Phase 4 — Web interface

- [ ] Minimal browser UI: prompt loader, turn input, ledger display, clock visualisation
- [ ] Session save/load via exported XML files
- [ ] MCP / API integration for on-demand lore lookup (faction data, world details)
