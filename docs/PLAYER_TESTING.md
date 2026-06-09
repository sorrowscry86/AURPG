# AURPG Internal Play Testing Guide

Phase 4 internal alpha. This guide is for developers and close collaborators running structured
play sessions to validate every mechanic before external testers receive access.

## Prerequisites

- Python 3.11+
- An `ANTHROPIC_API_KEY` environment variable set to a valid key
- The repo cloned and the package installed:

```bash
git clone https://github.com/sorrowscry86/AURPG.git
cd AURPG
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Unix
pip install -e ".[dev]"
```

## Starting a session

```bash
aurpg new
```

This runs the 4-stage Campaign Creation Wizard (System / Character / Safety / Orchestration),
then drops you into the game loop.

To resume a saved session:

```bash
aurpg list                    # find your session ID
aurpg resume <session-id>
```

## In-session commands

| Command | Effect |
|---------|--------|
| `/quit` | Save and exit |
| `/sheet` | Display full character sheet |
| `/recap` | Request a session recap from the LLM |
| `/help` | Show available commands |

## What to test in Phase 4

Cover all of the following across your sessions. Log each as pass/fail with a short note.

### Resolution types

- [ ] Solo action — strong hit (Action Score > both dice)
- [ ] Solo action — weak hit (beats one die)
- [ ] Solo action — miss (beats neither die)
- [ ] Solo action — critical (double 6s on challenge dice, Action Score wins)
- [ ] Squad roll — all four outcome tiers
- [ ] Flashback — 1-stress, 2-stress, 3-stress costs
- [ ] Progress Move — rolling completed progress boxes vs. 2d10
- [ ] Momentum Burn — canceling a challenge die at or below current momentum

### Clock mechanics

- [ ] Standard clock fills to completion (4, 6, or 8 segments)
- [ ] Danger clock fills to failure state
- [ ] Racing clocks (two clocks, first to fill wins)
- [ ] Mission success and mission failure paths

### Safety commands (test each in live play)

- [ ] `[X-Card]` — immediate pause, OOC mode activates
- [ ] `[Rewind]` — rolls back to previous turn
- [ ] `[Fast-Forward]` — skips current scene
- [ ] `[Pause]` — freezes loop; narrative input blocked until resumed
- [ ] `!enforce_hard_stop` — hard session termination

### Orchestration modes

Run at least one campaign in each mode:

- [ ] `strict_manual`
- [ ] `collaborative_consult`
- [ ] `generative_synthesis`

### Persistence

- [ ] Save a session (`/quit`) and resume it in a new process (`aurpg resume`)
- [ ] Confirm narrative and state continue correctly after resume

## What a good turn looks like

Each engine response must:

1. Open with an updated state ledger (clocks, stress, momentum, harm)
2. Choose the correct resolution mode for the fictional situation
3. Present fiction in deep POV (Somatic-First: physical reaction → internal conflict → action)
4. End with exactly **3 CYOA options** + a freeform invitation
5. Honor any safety command immediately if one was present in input

## What to log

For each session, record:

- Campaign genre and orchestration mode used
- Which mechanics were triggered
- Any prose failures: clichés, agency violations, missing state updates, hidden reasoning leaked
- Safety command incidents — did the interrupt and resume work?
- Overall narrative pacing: were the 3 options meaningful and distinct?

File bugs as GitHub Issues with labels: `[P0]` blocking / `[P1]` important / `[P2]` nice-to-fix.

## Phase 4 exit criteria

- All P0 issues resolved (crashes, state corruption, safety failures)
- All P1 issues triaged with workarounds documented
- At least one complete 15+ turn campaign played to a meaningful story conclusion
- No clichés logged in the final 5 turns of the evaluation campaign
