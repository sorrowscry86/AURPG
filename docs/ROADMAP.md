# AURPG — Roadmap to Player Testing

> **As of June 2026.** All phases build sequentially; no phase begins until the previous phase's exit criteria are met.

---

## Current State

| Artifact | Status |
|----------|--------|
| System prompt spec (XML) | Complete — v0.2-prototype |
| Resolution mechanics (Solo/Squad/Flashback/Progress) | Fully specified |
| State machines (clocks, tracks, momentum) | Fully specified |
| Safety infrastructure (consent matrix, live commands) | Fully specified |
| Evaluation harness | 14 canonical fixtures, 531 non-live tests passing |
| Design documentation | Complete — 10 sections authored |
| Python project skeleton | Complete — `pyproject.toml`, package layout, CI workflows |
| Core engine | Complete — `dice`, `llm`, `safety`, `session`, `wizard`, `state/manager` |
| CLI interface | Complete — `aurpg new`, `play`, `resume`, `list` |
| REST API server | Complete — FastAPI server with session CRUD, turn, settings, models |
| Test automation | Complete — 531 unit/integration tests; live evaluation suite on main/nightly |
| Player-facing interface | CLI ready; Flutter GUI design spec drafted |

---

## Definition of "Player Testing Ready"

A player can:

1. Start a new campaign using the 4-stage Campaign Creation Wizard
2. Play through at least 5 narrative turns with correct mechanical resolution
3. Invoke any safety command and have it honored immediately
4. Save a session and resume it in a later process invocation
5. Receive the Stars & Wishes aftercare debrief at session end

The engine must pass all golden transcript regression tests before any external player receives access.

---

## Phase 0 — Spec Hardening

**Goal**: Make the prompt spec implementation-ready and fully documented so that application code can be written unambiguously.

**Estimated duration**: 2–3 weeks

### Tasks

**Design documentation**
- [x] Author all 10 planned DESIGN.md sections: Goals & Non-Goals, Architecture Overview, State Model, LLM Integration, Session Lifecycle, Game Rules Layer, API/Interface Design, Error Handling & Safety, Testing Strategy, Roadmap
- [x] Finalize module boundary decisions: separate core rules from genre/campaign overlays in the XML spec

**Golden transcript expansion**
- [x] Expand library from 3 → 14 canonical scenarios covering every mechanic:
  - Solo resolution — strong hit, weak hit, miss, and critical (double 6s)
  - Squad resolution — all four outcome tiers
  - Flashback — 1-stress, 2-stress, and 3-stress costs
  - Progress Move — rolling completed progress boxes vs. 2d10
  - Momentum burning — cancellation of a challenge die at or below current value
  - Clock advancement — standard fill, danger fill, racing (two clocks), mission success/failure
  - Full safety interrupt cycle — `[X-Card]` → OOC calibration → scene resume
  - Aftercare debrief — Stars & Wishes exchange

**State schema canonicalization**
- [x] Document every field in all five XML state containers — `<session_state>`, `<resources>`, `<state_machines>`, `<safety_profile>`, and `<turn_seed>` — with data type, required/optional status, valid range/enum, and validation rule
- [x] Add `<safety_profile>` and `<turn_seed>` to the `<xml_state_architecture>` section of `aurpg_system_prompt_prototype.xml`
- [x] Define session lifecycle rules: save format, resume context injection, recap summarization trigger (context length threshold)

**Prompt quality audit**
- [x] Run all 14 fixtures through offline pattern checks via `test_golden_transcripts.py`
- [x] Verify all five hard rules (L1–L5) are exercised in at least one transcript each

### Exit Criteria

- [x] All 14 golden transcript fixtures validated (offline); live suite runs nightly on main
- [x] DESIGN.md sections 1–10 authored and reviewed
- [x] State schema documented with field-level types and validation rules
- [x] Session lifecycle design decisions recorded

---

## Phase 1 — Project Skeleton & Evaluation Infrastructure

**Goal**: Bootstrap a testable Python package and automate golden transcript regression so prompt changes are caught immediately.

**Depends on**: Phase 0 complete

**Estimated duration**: 2–3 weeks

### Tasks

**Project bootstrap**
- [x] Create `pyproject.toml` (Python 3.11+, project metadata, optional dev/test extras)
- [x] Configure test runner: `pytest` + `pytest-asyncio` for async LLM calls
- [x] Initialize `src/aurpg/__init__.py` and package layout mirroring the planned module list

**State schema implementation**
- [x] `src/aurpg/state/__init__.py` — dataclass models for all five XML state containers
- [x] `src/aurpg/parser.py` — XML ↔ dataclass round-trip with validation; reject malformed state early
- [x] `src/aurpg/validator.py` — schema-level checks on raw XML before parsing

**Evaluation harness**
- [x] `tests/prompts/test_golden_transcripts.py` — fixture-driven tests (offline pattern checks + live marker)
- [x] 14 YAML fixture files covering all mechanics
- [x] Banned-phrase, regex, and state-delta checks running without API key

**CI**
- [x] `ci.yml` — PR gate runs all non-live tests (no API key required; fork-safe)
- [x] `eval.yml` — post-merge and nightly live evaluation with real Anthropic API

### Exit Criteria

- [x] `pytest -m "not live"` passes all 531 tests
- [x] CI green on every push
- [x] XML ↔ dataclass round-trip validated for all state container types

---

## Phase 2 — Core Engine

**Goal**: A programmatic session runner that executes a complete AURPG turn lifecycle from Python, with no manual state intervention.

**Depends on**: Phase 1 complete

**Estimated duration**: 4–6 weeks

### Tasks

**Dice oracle** (`src/aurpg/dice.py`)
- [x] Deterministic seeded rolls for test reproducibility
- [x] Live CSPRNG rolls for real play
- [x] Roll formatters for all dice expressions used in the spec (1d6+attr, Nd6 pool, 2d10)

**LLM integration layer** (`src/aurpg/llm.py`)
- [x] Anthropic SDK client with prompt assembly (system XML + state XML + user message)
- [x] Structured output schema for engine responses (ledger block + prose block + options array)
- [x] Retry logic with exponential backoff; token budget tracking and alerting

**State manager** (`src/aurpg/state/manager.py`)
- [ ] Load, validate, apply turn result mutations, serialize, persist (JSON and XML)
- [ ] Immutable turn history log (append-only) for Rewind support

**Safety command parser** (`src/aurpg/safety.py`)
- [ ] In-message detection of `[X-Card]`, `[Rewind]`, `[Fast-Forward]`, `[Pause]`, `!enforce_hard_stop` before the turn reaches the LLM
- [ ] Interrupt handlers: freeze turn loop, emit OOC calibration prompt, update safety profile, resume or rewind as appropriate

**Session manager** (`src/aurpg/session.py`)
- [x] Initialize new session (wizard config → starting state)
- [x] Turn loop: receive player input → inject dice → call LLM → parse response → apply state → render → repeat
- [x] Save session to disk; load and resume with context-injected recap
- [x] Recap summarization: compress turn history when context approaches limit

**Campaign wizard** (`src/aurpg/wizard.py`)
- [x] Drive 4-stage onboarding dialogue (System/Character/Safety/Orchestration)
- [x] Validate player configuration and write to initial session state

**Integration tests**
- [x] `tests/integration/test_session_lifecycle.py` — wizard → 10 turns → save → resume → safety interrupts
- [x] Fixed dice seed ensures deterministic outcomes across runs

### Exit Criteria

- [x] Integration test runs 10-turn session end-to-end with no failures
- [x] State transitions are deterministic for fixed dice seeds
- [x] Safety interrupt correctly freezes turn loop and resumes after calibration
- [x] Session save and resume produces identical state and continuing narrative

---

## Phase 3 — Minimal Viable Interface

**Goal**: A player-usable CLI that exposes the full game loop without requiring developer intervention.

**Depends on**: Phase 2 complete

**Estimated duration**: 2–3 weeks

### Tasks

**CLI commands** (`src/aurpg/cli/`)
- [x] `aurpg new` — launch Campaign Creation Wizard and start a new session
- [x] `aurpg play <session-id>` — enter the turn loop for an active session
- [x] `aurpg resume` — list saved sessions and resume the selected one
- [x] `aurpg list` — show all saved sessions with last-played date and scene summary
- [x] `/quit` in-session — save and exit gracefully

**In-turn rendering**
- [x] State ledger display: formatted block showing current clocks, tracks, stress, momentum, and harm before each turn's prose
- [x] Character sheet view: full attribute list, bonuses, inventory, NPC relationships on demand (`/sheet`)
- [x] Safety command acknowledgment: visible OOC mode banner when a safety command is active

**Campaign wizard CLI flow**
- [x] Interactive prompts for all 4 wizard stages with input validation

**REST API server** (`src/aurpg/server/`) — *added beyond original scope*
- [x] FastAPI server with session CRUD, turn endpoint, settings, and model listing
- [x] 67 server endpoint tests added; 531 total non-live tests passing

**Player onboarding materials**
- [x] `docs/PLAYER_GUIDE.md` — install, campaign start, ledger reading, safety commands, resolution
- [x] `docs/PLAYER_TESTING.md` — Phase 4 internal alpha play guide with mechanic checklist

### Exit Criteria

- [x] CLI functional end-to-end: `aurpg new` → turn loop → `/quit` → `aurpg resume`
- [x] All five safety commands intercepted and handled before LLM
- [x] Session save/resume works across process restarts
- [x] Player Guide authored for non-developer audiences

---

## Phase 4 — Internal Alpha

**Goal**: Developer and close collaborators exercise every mechanic and orchestration mode in real play before external players see the system.

**Depends on**: Phase 3 complete

**Estimated duration**: 2–4 weeks of structured play sessions

### Tasks

**Mechanic coverage**
- [ ] Play through 3+ distinct campaign starts across different genres and orchestration modes
- [ ] Exercise all resolution types: Solo, Squad, Flashback, Progress Move, Momentum Burn, Critical
- [ ] Advance every clock type to completion: standard, danger, racing (two simultaneous), mission success, mission failure
- [ ] Trigger every safety command in live play; verify interrupt and resume behavior

**Orchestration mode coverage**
- [ ] One campaign in `strict_manual` mode
- [ ] One campaign in `collaborative_consult` mode
- [ ] One campaign in `generative_synthesis` mode

**Quality assessment**
- [ ] Log all prose failures: clichés found, agency violations, hidden reasoning leakage, missing state updates
- [ ] Assess narrative pacing: are 3 CYOA options always meaningful and distinct?
- [ ] Assess fiction-first triggering: are moves only triggered on genuine uncertainty?

**Issue triage**
- [ ] File all discovered issues in GitHub Issues with severity labels (P0 = blocking / P1 = important / P2 = nice-to-fix)
- [ ] Resolve all P0 issues before proceeding to Phase 5
- [ ] Document known P1 workarounds for alpha testers

### Exit Criteria

- All P0 issues resolved (engine crashes, state corruption, safety failures)
- All P1 issues triaged with workarounds documented
- At least one complete 15+ turn campaign played to a meaningful story conclusion
- Prose quality acceptable: no clichés logged in the final 5 turns of the evaluation campaign

---

## Phase 5 — Closed Player Alpha

**Goal**: 3–5 external players experience AURPG with structured feedback collection and a triage cadence.

**Depends on**: Phase 4 complete

**Estimated duration**: 4–6 weeks

### Tasks

**Recruitment**
- [ ] Recruit 3–5 alpha testers from tabletop RPG communities (target: players with PbtA, FitD, or Ironsworn experience)
- [ ] Brief each tester on the alpha nature of the system, what to expect, and what feedback is needed

**Onboarding**
- [ ] Distribute Player Guide and quick-reference card
- [ ] Pair each tester with an async check-in channel for blockers
- [ ] Run one observed session per tester to catch setup friction before solo play

**Feedback collection**
- [ ] Per-session feedback form: session length, favorite/least-favorite moment, rules confusion points, safety command usage, prose quality rating (1–10), overall enjoyment (1–10)
- [ ] Open-ended: "What one thing would you change?"
- [ ] Bug report template in GitHub Issues with `[alpha-feedback]` label

**Triage cadence**
- [ ] Weekly feedback review; prioritize fixes for the next iteration
- [ ] Prompt iteration log: every prompt change records before/after evaluation results
- [ ] Re-run all 10 golden transcripts after any prompt change

**Completion**
- [ ] All recruited testers (3–5) complete at least 3 sessions each (target: ~45 min per session)
- [ ] Feedback digest published in `docs/ALPHA_FEEDBACK.md`
- [ ] Decision gate: proceed to open beta, or return to Phase 4 for another iteration cycle

### Exit Criteria

- No P0 safety issues across all alpha sessions (safety commands must work 100% of the time)
- Average prose quality rating ≥ 7/10
- Average overall enjoyment rating ≥ 7/10
- Feedback digest published and all P0 issues from alpha resolved

---

## Summary Timeline

| Phase | Name | Estimated Duration | Status |
|-------|---------------------------------|-------------------|----|
| 0 | Spec Hardening | 2–3 weeks | ✅ Complete |
| 1 | Evaluation Infrastructure | 2–3 weeks | ✅ Complete |
| 2 | Core Engine | 4–6 weeks | ✅ Complete |
| 3 | Minimal Viable Interface | 2–3 weeks | ✅ Complete |
| 4 | Internal Alpha | 2–4 weeks | **← Current Phase** |
| 5 | Closed Player Alpha | 4–6 weeks | Not started |

**All code phases complete. Phase 4 requires real play sessions (ANTHROPIC_API_KEY or OPENROUTER_API_KEY needed). See `docs/PLAYER_TESTING.md` for the Phase 4 checklist.**

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM output non-determinism breaks golden transcript tests | High | Medium | Use LLM-judge soft evaluation rather than exact string match |
| Prompt spec needs major revision after Phase 1 reveals gaps | Medium | High | Invest in Phase 0 transcript expansion to surface gaps before any code is written |
| Context length limits prevent long sessions | Medium | High | Design recap/summarization in Phase 0 lifecycle rules; test with 20+ turn sessions in Phase 4 |
| Safety commands missed by the model in live play | Low | Critical | Detect safety commands in `safety.py` before the LLM sees the turn; never rely on the model to notice them |
| Alpha testers disengage before completing 3 sessions | Medium | Medium | Keep sessions short (45 min target), offer async play option, pair testers with an active check-in channel |
| Anthropic API costs exceed budget during evaluation CI | Medium | Low | Cache golden transcript responses; only re-evaluate on prompt file changes |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `docs/DESIGN.md` | Architecture decisions and near-term design targets |
| `docs/PROMPT_USAGE_GUIDE.md` | Manual evaluation workflow and current canonical test results |
| `src/aurpg/prompts/aurpg_system_prompt_prototype.xml` | The engine specification |
| `src/aurpg/prompts/examples/sample_campaign_state.xml` | Reference runtime state |
| `.github/AURPG.agent.md` | Engine Architect agent persona and mechanic spec |
