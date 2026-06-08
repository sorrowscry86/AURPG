# AURPG Player Guide

A text RPG powered by an AI engine. You type what your character does; the engine narrates what happens, updates your stats, and offers options. Everything runs in your terminal.

---

## 1. Installation

```
pip install aurpg
```

From source:

```
git clone <repo-url>
cd AURPG
pip install -e .
```

Verify the install:

```
aurpg --help
```

---

## 2. Starting a New Campaign

```
aurpg new
```

This runs the **Campaign Creation Wizard** — four stages of setup prompts. Invalid input is re-prompted automatically.

### Stage 1 — Campaign Setup

```
Campaign title: The Shattered Reaches
Genre: dark fantasy
Tone: grim, morally complex
Canon mode ['flexible_canon', 'sandbox', 'strict_continuity']: flexible_canon
```

**Canon modes:**
- `strict_continuity` — the engine remembers and enforces every detail
- `flexible_canon` — continuity is maintained but the engine adapts gracefully
- `sandbox` — no hard canon; experiment freely

### Stage 2 — Character

```
Character name: Sable
Edge [1-3]: 2
Heart [1-3]: 1
Iron [1-3]: 2
Shadow [1-3]: 3
Wits [1-3]: 2
Load ['heavy', 'light', 'normal']: light
```

**Attributes** (each 1–3, total must not exceed 10):

| Attribute | Governs |
|-----------|---------|
| Edge | Speed, aggression, reflexes |
| Heart | Empathy, resolve, social bonds |
| Iron | Physical endurance, brute force |
| Shadow | Deception, stealth, dark knowledge |
| Wits | Perception, problem-solving, improvisation |

**Load** controls encumbrance: `light` (few items, fast), `normal` (standard), `heavy` (gear-laden, slower).

Starting values are always: **Stress 0 / Momentum 2 / Harm: none**.

### Stage 3 — Safety

Rate each content category: `green` (allowed), `yellow` (caution, handle carefully), or `red` (off-limits).

```
Safety for 'horror' ['green', 'red', 'yellow']: yellow
Safety for 'health' ['green', 'red', 'yellow']: green
Safety for 'relationships' ['green', 'red', 'yellow']: green
Safety for 'social_issues' ['green', 'red', 'yellow']: yellow
Orchestration mode ['collaborative_consult', 'generative_synthesis', 'strict_manual']: collaborative_consult
```

**Orchestration modes:**
- `strict_manual` — you drive every decision; the engine executes
- `collaborative_consult` — the engine suggests; you confirm
- `generative_synthesis` — the engine improvises freely within your safety settings

### Stage 4 — Starting Position

```
Initial position ['controlled', 'desperate', 'risky']: controlled
Initial effect ['great', 'limited', 'standard']: standard
```

**Position** sets how dangerous your opening situation is. **Effect** sets how much impact your actions have at the start.

After the wizard completes, the game loop starts immediately.

---

## 3. The Game Screen

Each turn shows the **ledger** (your current stats), a narrative response, and an options list.

```
────────────────────────────────────────────────────────────
  STRESS 3/10  |  MOMENTUM   4  |  HARM: none
  Position: risky  |  Effect: standard
  Clocks:
    [████░░░░] rival-ambush (4/8)
  Tracks:
    escape-the-city: 12/40 ticks
────────────────────────────────────────────────────────────

The lamplighter rounds the corner just as you press yourself
into the alcove. His footsteps slow — he heard something.
The lantern light sweeps toward your hiding spot. You have
maybe three seconds before the beam finds you.

  What do you do?
  1) Press deeper into the shadows and hold your breath
  2) Create a distraction — hurl a coin down the alley
  3) Break for the rooftops while his back is turned
  (or type freely)

> 
```

The `>` prompt is where all input goes.

---

## 4. Taking Your Turn

Type what your character does at the `>` prompt. Describe actions, intentions, or dialogue. The engine interprets your input as fiction.

**Good inputs:**

```
> I grab the lantern and shatter it against the wall
> Sable lunges for the window latch and tries to force it open
> I tell the guard I'm a city inspector — show him a forged seal
> Make for the canal. I know this district; we can lose them in the waterways.
```

**Less effective:**
- Single words: `run` — the engine may work with it, but detail gets better results
- Out-of-character planning without a safety command: use `/recap` or `/sheet` instead

After you press Enter:
1. The engine generates a narrative response describing the outcome
2. Your ledger updates (stress, momentum, harm, clocks, tracks)
3. The engine offers 2–3 options for your next action (you can ignore them and type freely)
4. The session auto-saves

---

## 5. In-Game Commands

Type these at the `>` prompt at any time.

| Command | What it does |
|---------|-------------|
| `/quit` | Save the session and exit to the terminal |
| `/sheet` | Show your full character sheet (attributes, inventory, relationships) |
| `/help` | Show the command list |
| `/recap` | Show a summary of recent turns |

**Example `/sheet` output:**

```
────────────────────────────────────────────────────────────
  CHARACTER: Sable   Load: light
  Attributes:
    edge: 2
    heart: 1
    iron: 2
    shadow: 3
    wits: 2
────────────────────────────────────────────────────────────
```

**Example `/recap` output:**

```
[Recap]
Turn 4: Sable evaded the city watch by breaking through the
market stalls. Stress rose to 3. The rival-ambush clock
ticked to 4/8.
Turn 5: Attempted to bribe the dock gate guard. Failed —
harm set to "shaken". Momentum fell to 2.
```

---

## 6. Safety System

Safety commands interrupt the fiction immediately. They are recognized anywhere in your input — you do not need to stop the scene first.

Type them at the `>` prompt like any other input:

```
> [X-Card]
> [Pause]
> I need to take a break [Pause]
> !enforce_hard_stop
```

| Command | Effect |
|---------|--------|
| `[X-Card]` | Freezes fiction immediately; flags and removes the current content. No explanation required. |
| `[Rewind]` | Steps the narrative back to an earlier moment. The engine will ask how far. |
| `[Fast-Forward]` | Skips past the current content to a point you specify. |
| `[Pause]` | Opens an out-of-character space. Fiction halts; only safety commands are accepted. |
| `!enforce_hard_stop` | Hard exits the fiction entirely. Requires a manual reset to continue. Highest severity. |

### When the session is paused

The ledger is replaced by an OOC banner:

```
┌──────────────────────────────────────────────────────────┐
│  [OOC] SESSION PAUSED — out-of-character space active    │
│  Type anything to resume, or !enforce_hard_stop to stop. │
└──────────────────────────────────────────────────────────┘

[PAUSED — type /quit to save and exit, or use a safety command to resume]
>
```

While paused you can:
- Type `[Fast-Forward]` to resume the session
- Type `/quit` to save and exit
- Type `!enforce_hard_stop` to hard-stop

You cannot send narrative input while paused. Any non-safety text you type will be routed through the safety gate and echoed back as an OOC message.

### After a hard stop

The session ends and is saved. A banner is shown:

```
╔══════════════════════════════════════════════════════════╗
║  ⚠  HARD STOP — FULLY OUT OF FICTION                    ║
║  Your wellbeing comes first. Take all the time you need. ║
╚══════════════════════════════════════════════════════════╝

[Session ended due to hard stop. Your progress is saved.]
```

To continue from a hard-stopped session, you will need to start a new campaign or contact the project maintainer for manual reset instructions.

---

## 7. Saving and Resuming

**Saves are automatic** after every completed turn. You do not need to type `/save`. Saves live at:

```
~/.aurpg/saves/<session-id>/
```

Each session folder contains the campaign state XML and a `meta.json` with model info.

### List all sessions

```
aurpg list
```

Example output:

```
3f2a1b8c-4e5d-4f1a-9b2e-7d3c0a1e4f8b  (model: claude-haiku-4-5-20251001)
a7c9d2e1-1f3b-4a2c-8e5d-0b4f7c9a3d1e  (model: claude-haiku-4-5-20251001)
```

The long string before the model is your **session ID**.

### Resume a session

```
aurpg resume 3f2a1b8c-4e5d-4f1a-9b2e-7d3c0a1e4f8b
```

or the equivalent alias:

```
aurpg play 3f2a1b8c-4e5d-4f1a-9b2e-7d3c0a1e4f8b
```

The session picks up exactly where you left off, ledger and all.

### Global options (apply to any subcommand)

```
aurpg --saves-dir /path/to/saves new
aurpg --model claude-sonnet-4-5 new
aurpg --prompt /path/to/custom_prompt.xml new
```

---

## 8. Reading the Ledger

The ledger appears above the narrative at the start of each turn.

```
────────────────────────────────────────────────────────────
  STRESS 6/10  |  MOMENTUM  -2  |  HARM: shaken
  Position: desperate  |  Effect: limited
  Clocks:
    [████████░░░░] betrayal-clock (8/12)
  Tracks:
    infiltrate-the-keep: 28/40 ticks
────────────────────────────────────────────────────────────
```

### STRESS

Current stress on a 0–10 scale. Higher stress means your character is closer to a breaking point. At 10, the engine treats your situation as critical.

### MOMENTUM

Narrative momentum on a -6 to +10 scale. Positive momentum means things are going your way; negative means you are in a downward spiral. The engine factors this into action outcomes.

### HARM

Current harm status. Common values: `none`, `shaken`, `wounded`, `broken`. Harm persists until addressed in the fiction.

### Position and Effect

- **Position**: How dangerous your current situation is — `controlled`, `risky`, or `desperate`
- **Effect**: How much your actions change things — `limited`, `standard`, or `great`

### Clocks

Clocks count down or fill up toward a threshold event (an ambush arrives, a plan succeeds, a resource runs out). Each clock shows:

```
[████░░░░] clock-name (filled/segments)
```

`█` = filled segment, `░` = empty segment. When a clock reaches full (all `█`), its event triggers.

### Progress Tracks

Progress tracks measure long-term goals over 40 ticks (10 boxes of 4 ticks each). The ledger shows total ticks accumulated:

```
infiltrate-the-keep: 28/40 ticks
```

Use `/sheet` for a box-by-box breakdown. Each box is either `[████]` (complete), `[░░░░]` (empty), or partial (e.g. `[██░░]` for 2 of 4 ticks in the current box).

---

## 9. Stars and Wishes (Session Aftercare)

After finishing a session — whether you hit `/quit`, finished a story arc, or needed a safety stop — take a few minutes for a brief debrief. This is a standard TTRPG practice:

**Stars:** What worked well? What moments were memorable or satisfying?

**Wishes:** What would you do differently? What content adjustments would improve the next session?

You can adjust your safety settings at the start of your next session (rerun `aurpg new` with a fresh campaign, or edit the saved state XML directly). Your stars and wishes are for you — there is no in-app prompt for them.

---

## 10. Quick Reference

```
COMMANDS            SAFETY                   LEDGER
─────────────────   ──────────────────────   ──────────────
/quit               [X-Card]                 █ = filled segment
/sheet              [Rewind]                 ░ = empty segment
/help               [Fast-Forward]
/recap              [Pause]                  STRESS  0–10
                    !enforce_hard_stop       MOMENTUM  -6–10

CLI
─────────────────────────────────────────────────────────────
aurpg new                        start a new campaign
aurpg list                       list saved sessions
aurpg resume <session-id>        resume a saved session
aurpg play <session-id>          alias for resume

SAVES: ~/.aurpg/saves/<session-id>/
```
