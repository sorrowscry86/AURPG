# AURPG — Roadmap to Player Testing

> **As of June 2026.** All phases build sequentially; no phase begins until the previous phase's exit criteria are met.

---

## Current State

| Artifact | Status |
|----------|--------|
| System prompt spec (XML) | Complete — v0.1-prototype |
| Resolution mechanics (Solo/Squad/Flashback/Progress) | Fully specified |
| State machines (clocks, tracks, momentum) | Fully specified |
| Safety infrastructure (consent matrix, live commands) | Fully specified |
| Evaluation harness | 3 canonical tests, all passing |
| Design documentation | ~70% — 10 planned sections outstanding |
| Python project skeleton | Not started |
| Application code | Not started |
| Test automation | Not started |
| Player-facing interface | Not started |

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
- [ ] Author all 10 planned DESIGN.md sections: Goals & Non-Goals, Architecture Overview, State Model, LLM Integration, Session Lifecycle, Game Rules Layer, API/Interface Design, Error Handling & Safety, Testing Strategy, Roadmap
- [ ] Finalize module boundary decisions: separate core rules from genre/campaign overlays in the XML spec

**Golden transcript expansion**
- [ ] Expand library from 3 → 10 canonical scenarios covering every mechanic:
  - Solo resolution — strong hit, weak hit, miss, and critical (double 6s)
  - Squad resolution — all four outcome tiers
  - Flashback — 1-stress, 2-stress, and 3-stress costs
  - Progress Move — rolling completed progress boxes vs. 2d10
  - Momentum burning — cancellation of a challenge die at or below current value
  - Clock advancement — standard fill, danger fill, racing (two clocks), mission success/failure
  - Full safety interrupt cycle — `[X-Card]` → OOC calibration → scene resume
  - Campaign Creation Wizard — complete 4-stage run
  - Session handoff — save state, inject recap context, resume turn
  - Aftercare debrief — Stars & Wishes exchange

**State schema canonicalization**
- [ ] Document every field in all five XML state containers — `<session_state>`, `<resources>`, `<state_machines>`, `<safety_profile>`, and `<turn_seed>` — with data type, required/optional status, valid range/enum, and validation rule
- [ ] Add `<safety_profile>` and `<turn_seed>` to the `<xml_state_architecture>` section of `aurpg_system_prompt_prototype.xml` so the LLM knows their schema (both containers exist in `sample_campaign_state.xml` but are absent from the spec)
- [ ] Define session lifecycle rules: save format, resume context injection, recap summarization trigger (context length threshold)

**Prompt quality audit**
- [ ] Run all 10 transcripts through the banned-phrase check; expand the list from discovered violations
- [ ] Verify all five hard rules (L1–L5) are exercised in at least one transcript each

### Exit Criteria

- All 10 golden transcripts pass against the current prompt
- DESIGN.md sections 1–10 authored and reviewed
- State schema documented with field-level types and validation rules
- Session lifecycle design decisions recorded

---

## Phase 1 — Project Skeleton & Evaluation Infrastructure

**Goal**: Bootstrap a testable Python package and automate golden transcript regression so prompt changes are caught immediately.

**Depends on**: Phase 0 complete

**Estimated duration**: 2–3 weeks

### Tasks

**Project bootstrap**
- [ ] Create `pyproject.toml` (Python 3.11+, project metadata, optional dev/test extras)
- [ ] Configure test runner: `pytest` + `pytest-asyncio` for async LLM calls
- [ ] Initialize `src/aurpg/__init__.py` and package layout mirroring the planned module list

**State schema implementation**
- [ ] `src/aurpg/state/schema.py` — Pydantic v2 models for all five XML state containers
- [ ] `src/aurpg/state/parser.py` — XML ↔ Pydantic round-trip with validation; reject malformed state early

**Evaluation harness**
- [ ] `src/aurpg/evaluation/harness.py` — loads system prompt XML + campaign state XML, sends test turn to Anthropic API, evaluates response against the output contract:
  - Exactly 3 CYOA options present
  - Explicit state ledger update (clocks, tracks, stress, momentum) before prose
  - Correct resolution mode selected (solo vs. squad)
  - No banned cliché phrases
  - Agency preserved (no PC puppeting)
  - Safety commands honored when invoked
- [ ] `tests/evaluation/test_golden_transcripts.py` — parametrized tests, one per golden scenario
- [ ] Use an LLM judge (secondary Anthropic call) for soft evaluation where exact string match is inappropriate

**CI**
- [ ] GitHub Actions workflow with two tiers:
  - **PR checks** — run evaluation tests with mocked/cassette responses (e.g., `vcrpy`) so no API key is required; skip live LLM tests via `pytest.mark.skipif` when `ANTHROPIC_API_KEY` is absent (protects fork PRs where secrets are unavailable)
  - **Post-merge / scheduled** — run the full live LLM evaluation suite against the real Anthropic API on merges to `main` and on a nightly schedule to catch model-drift regressions

### Exit Criteria

- `pytest tests/` passes all 10 golden transcript tests
- CI green on every push
- XML ↔ Pydantic round-trip validated for all state container types

---

## Phase 2 — Core Engine

**Goal**: A programmatic session runner that executes a complete AURPG turn lifecycle from Python, with no manual state intervention.

**Depends on**: Phase 1 complete

**Estimated duration**: 4–6 weeks

### Tasks

**Dice oracle** (`src/aurpg/dice.py`)
- [ ] Deterministic seeded rolls for test reproducibility
- [ ] Live CSPRNG rolls for real play
- [ ] Roll formatters for all dice expressions used in the spec (1d6+attr, Nd6 pool, 2d10)

**LLM integration layer** (`src/aurpg/llm.py`)
- [ ] Anthropic SDK client with prompt assembly (system XML + state XML + user message)
- [ ] Structured output schema for engine responses (ledger block + prose block + options array)
- [ ] Retry logic with exponential backoff; token budget tracking and alerting

**State manager** (`src/aurpg/state/manager.py`)
- [ ] Load, validate, apply turn result mutations, serialize, persist (JSON and XML)
- [ ] Immutable turn history log (append-only) for Rewind support

**Safety command parser** (`src/aurpg/safety.py`)
- [ ] In-message detection of `[X-Card]`, `[Rewind]`, `[Fast-Forward]`, `[Pause]`, `!enforce_hard_stop` before the turn reaches the LLM
- [ ] Interrupt handlers: freeze turn loop, emit OOC calibration prompt, update safety profile, resume or rewind as appropriate

**Session manager** (`src/aurpg/session.py`)
- [ ] Initialize new session (wizard config → starting state)
- [ ] Turn loop: receive player input → inject dice → call LLM → parse response → apply state → render → repeat
- [ ] Save session to disk; load and resume with context-injected recap
- [ ] Recap summarization: compress turn history when context approaches limit

**Campaign wizard** (`src/aurpg/wizard.py`)
- [ ] Drive 4-stage onboarding dialogue (System/Character/Safety/Orchestration)
- [ ] Validate player configuration and write to initial session state

**Integration tests**
- [ ] `tests/integration/test_session_lifecycle.py` — full session: wizard → 5 turns → save → resume → 5 more turns → aftercare debrief
- [ ] Fixed dice seed ensures deterministic outcomes across runs

### Exit Criteria

- Integration test runs 10-turn session end-to-end with no failures
- State transitions are deterministic for fixed dice seeds
- Safety interrupt correctly freezes turn loop and resumes after calibration
- Session save and resume produces identical state and continuing narrative

---

## Phase 3 — Minimal Viable Interface

**Goal**: A player-usable CLI that exposes the full game loop without requiring developer intervention.

**Depends on**: Phase 2 complete

**Estimated duration**: 2–3 weeks

### Tasks

**CLI commands** (`src/aurpg/cli/`)
- [ ] `aurpg new` — launch Campaign Creation Wizard and start a new session
- [ ] `aurpg play <session-id>` — enter the turn loop for an active session
- [ ] `aurpg resume` — list saved sessions and resume the selected one
- [ ] `aurpg list` — show all saved sessions with last-played date and scene summary
- [ ] `aurpg quit` — save and exit gracefully from within a session

**In-turn rendering**
- [ ] State ledger display: formatted block showing current clocks, tracks, stress, momentum, and harm before each turn's prose
- [ ] Character sheet view: full attribute list, bonuses, inventory, NPC relationships on demand
- [ ] Safety command acknowledgment: visible OOC mode banner when a safety command is active

**Campaign wizard CLI flow**
- [ ] Interactive prompts for all 4 wizard stages with input validation and backtrack support

**Player onboarding materials**
- [ ] `docs/PLAYER_GUIDE.md` — how to install, start a campaign, read the ledger, use safety commands, interpret resolution outcomes
- [ ] Quick-reference card: resolution tables, momentum track, clock segment meanings, safety command list

### Exit Criteria

- Developer plays a complete 10-turn campaign via CLI with no manual state intervention
- All five safety commands work correctly in-session
- Session save/resume works across process restarts
- A non-developer can follow the Player Guide to start and complete a campaign without assistance

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

| Phase | Name | Estimated Duration | Cumulative |
|-------|---------------------------------|-------------------|------------|
| 0 | Spec Hardening | 2–3 weeks | ~3 weeks |
| 1 | Evaluation Infrastructure | 2–3 weeks | ~6 weeks |
| 2 | Core Engine | 4–6 weeks | ~12 weeks |
| 3 | Minimal Viable Interface | 2–3 weeks | ~15 weeks |
| 4 | Internal Alpha | 2–4 weeks | ~19 weeks |
| 5 | Closed Player Alpha | 4–6 weeks | ~25 weeks |

**Estimated time from today to closed player alpha: 5–6 months** (solo developer pace; accelerates with additional contributors).

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
