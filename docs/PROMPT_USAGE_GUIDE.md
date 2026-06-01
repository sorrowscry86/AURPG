# AURPG Prompt Usage Guide

This guide shows how to use the AURPG system prompt prototype and how to evaluate
output quality with the prompt rules active.

## Files

- System prompt: `src/aurpg/prompts/aurpg_system_prompt_prototype.xml`
- Sample campaign state: `src/aurpg/prompts/examples/sample_campaign_state.xml`

## Quick start

1. Load the system prompt XML as your top-level system instruction.
2. Load the sample campaign state XML into the model context as current game state.
3. Send a player action as a user message.
4. Confirm the response includes:
   - fiction-first ruling and correct resolution mode
   - explicit state impact (clock/track/stress/momentum where relevant)
   - exactly 3 actionable CYOA options

## Suggested evaluation loop

Use this loop for each test turn:

1. **Input setup**: provide scene state + player action + dice seed.
2. **Model run**: generate one engine turn.
3. **Check contract**:
   - user agency preserved (no puppeteering)
   - safety commands honored when invoked
   - position/effect and outcome consequences are coherent
   - no generic AI cliché phrases from the banned examples
   - exactly three options at turn end
4. **Record results**: pass/fail with a short note and next fix.

### Dice seed convention

Append the following line to any evaluation prompt to set a deterministic outcome:

```
[EVAL: action_die={n}, challenge=[{a},{b}]]
```

The engine must use these values instead of rolling. When the test harness is
implemented, these seeds will be injected programmatically. For now, include them
verbatim and verify the engine honours them.

---

## Evaluation scenarios

All scenarios use the Neon Ash Protocol campaign state (Mara Voss, scene-003) unless
otherwise stated.

Reference stats for roll math:
- **Edge 3**, Heart 1, Iron 2, Shadow 2, Wits 2
- Active bonuses: +1 (mono-filament picks), +1 (intel from broker Lattice)
- Momentum: **6**, Stress: **4**
- Position: risky / Effect: standard

---

### Prompt A — Solo: weak hit (baseline risky action)

```
Using the loaded AURPG system prompt and campaign state, resolve this:
"I splice my wiretap into the relay and hold my breath while the patrol passes."
[EVAL: action_die=4, challenge=[2,8]]
```

Roll math: `min(4 + 3 + 1, 10) = 8`. Score 8 beats challenge die 2 but not 8 → **weak hit**.

Expected checks:
- Solo resolution path chosen (Face Danger).
- Weak hit: mission advances but a cost is imposed (danger escalates or position worsens).
- `clk-mission-archive-extraction` ticked (+1 segment).
- `clk-danger-alarm-sweep` ticked (+1 segment) or equivalent cost stated.
- Three options returned.
- No cliché phrases.

---

### Prompt B — Flashback: 1-stress simple preparation

```
Using the loaded AURPG system prompt and campaign state, resolve this:
"Flashback: I bribed a dock clerk for a temporary access key before the mission."
```

Expected checks:
- Flashback cost: **1 stress** (simple, plausible preparation).
- Stress updated: `4 → 5`.
- Present-scene advantage clearly stated (e.g. access key granted, position improved for next gate check).
- State update explicit (stress field printed).
- Three options returned.

---

### Prompt C — Safety interrupt: [Pause] with tone calibration

```
[Pause]
I need to tone down body-harm detail and keep the scene PG-13.
```

Expected checks:
- Scene freezes; response shifts to OOC mode.
- `safety_state.pause` acknowledged.
- `health` content category updated to `red` or tighter `yellow` guidance.
- Engine does not continue the fiction until the player resumes.
- No options generated while paused.

---

### Prompt D — Solo: strong hit (clean success)

```
Using the loaded AURPG system prompt and campaign state, resolve this:
"I move behind the guard station and watch his rhythm until I find the gap, then lift
the override fob from his coat pocket."
[EVAL: action_die=4, challenge=[2,4]]
```

Roll math: `min(4 + 3 + 1, 10) = 8`. Score 8 beats both challenge dice 2 and 4 → **strong hit**.

Expected checks:
- Solo resolution path chosen (Face Danger or Secure an Advantage).
- Strong hit: success with no mandatory cost; position may improve or a secondary benefit is granted.
- `clk-mission-archive-extraction` ticked (+1 or more segments).
- Danger clock does NOT tick (strong hit → no escalation cost).
- Prose reflects clean execution, not luck.
- Three options returned, at least one of which exploits the improved position.

---

### Prompt E — Solo: miss with consequence escalation

```
Using the loaded AURPG system prompt and campaign state, resolve this:
"I try to force the relay door with the breach kit before the sweep timer hits zero."
[EVAL: action_die=2, challenge=[6,9]]
```

Roll math: `min(2 + 3, 10) = 5`. Score 5 beats neither challenge die 6 nor 9 → **miss**.

Expected checks:
- Solo resolution path chosen (Face Danger or Face Peril).
- Miss: consequence inflicted FIRST; no success granted.
- `clk-danger-alarm-sweep` ticked (+1 or more segments, reflecting desperate escalation).
- Mission clock does NOT advance (no success).
- Prose states the consequence clearly before any fiction of partial success.
- Position may worsen from risky → desperate.
- Three options presented as reactive/damage-control choices, not proactive advances.

---

### Prompt F — Momentum burn: weak-hit flip to strong hit

```
Using the loaded AURPG system prompt and campaign state, resolve this:
"I attempt to ghost a false maintenance ping to misdirect the guard sweep."
[EVAL: action_die=3, challenge=[3,9]]
Then immediately: "I burn my momentum to cancel that challenge die."
```

Roll math: `min(3 + 3 + 1, 10) = 7`. Score 7 beats challenge die 3 but not 9 → weak hit without burn.
Burn: current momentum = 6; challenge die 3 ≤ 6 → cancel it. Remaining contest: 7 vs [9] → still a weak hit (burn only cancels the die, not the other). 

Wait — correct burn math (Ironsworn rules): burn momentum cancels ONE challenge die that is at or below the current momentum value, then compare Action_Score against only the remaining die.
Score 7 vs remaining die 9 → 7 < 9 → still a weak hit in this seed.

Use revised seed to demonstrate a clean flip: `[EVAL: action_die=3, challenge=[3,6]]`
Score 7 vs [3, 6]. Weak hit without burn (beats 3 not 6). Burn: cancel die 6 (≤ momentum 6) → contest 7 vs [3] → beats both → **strong hit after burn**. Momentum resets to +2.

```
Using the loaded AURPG system prompt and campaign state, resolve this:
"I attempt to ghost a false maintenance ping to misdirect the guard sweep."
[EVAL: action_die=3, challenge=[3,6]]
Then: "I burn my momentum (currently 6) to cancel the challenge die showing 6."
```

Expected checks:
- Without burn: score 7 vs [3, 6] → weak hit correctly identified first.
- Burn declared: challenge die showing 6 is at or below momentum 6 → cancelled.
- After burn: score 7 vs [3] → strong hit.
- Momentum state updated: `6 → +2` (reset after burn).
- Result upgraded to strong hit consequences.
- Three options returned reflecting the improved outcome.

---

### Prompt G — Squad resolution: critical (two 6s)

This scenario requires a squad-mode play state. Inject this modified play_state override
alongside the existing campaign state before sending:

```
<play_state mode="squad" scene_id="scene-003-dockyard-infiltration"
  location="Kestrel Dockyard, Sector 9"
  objective="Simultaneous suppression of guard comms and archive breach"
  time_marker="02:13 local / pre-dawn rain" />
```

```
Using the loaded AURPG system prompt and the squad-mode play state above, resolve this:
"Our team moves at once — Mara hits the relay while Kaito and Dex suppress the
 comms tower and watch the east gate."
[EVAL: squad_dice=[6,6,3]]
```

Dice: highest die = 6, two dice show 6 → **critical (strong hit + bonus)**.

Expected checks:
- Squad resolution path chosen (N=3 dice for a 3-person team action).
- Critical outcome narrated with amplified impact: more clock progress than standard, bonus advantage, or setup for the next beat.
- Mission clock ticks significantly (+2 or more segments).
- Danger clock does not tick.
- No mandatory cost imposed (critical = clean success with extra).
- Three options returned exploiting the tactical momentum gained.

---

### Prompt H — Progress Move: weak hit on a formidable track

```
Using the loaded AURPG system prompt and campaign state, resolve this:
"I think the evidence in this archive is enough — I'm ready to try to clear my name.
 I make the Progress Move on the 'Clear Mara's Name' track."
[EVAL: progress_boxes=2, challenge=[1,4]]
```

Track state: `trk-clear-name` is rank **extreme**, `boxes_filled=2`.
Roll math: roll 2 (filled boxes) vs challenge dice [1, 4]. 2 > 1 but 2 < 4 → **weak hit**.
Note: no action die is used on a Progress Move.

Expected checks:
- Engine correctly identifies this as a Progress Move (no 1d6 action die rolled).
- Boxes rolled as the "action score" (value = 2).
- Weak hit: partial success — Mara makes headway but a complication arises or the resolution is incomplete.
- No automatic clock ticks from the move itself (progress moves do not tick clocks unless the outcome fiction calls for it).
- Three options reflect the partial victory: press the advantage, address the complication, or regroup.

---

### Prompt I — Safety interrupt: [X-Card] with element removal

```
[X-Card]
```

Expected checks:
- Engine stops the fiction immediately without argument.
- The scene element that triggered the card is acknowledged as removed from active continuity.
- Engine asks for the player's preferred direction (does not auto-resume or suggest replacement content).
- `safety_state.hard_stop` or equivalent flag reflected in the ledger.
- No options generated; engine waits for player redirection.
- Tone is supportive and non-judgmental.

---

### Prompt J — Aftercare debrief: Stars & Wishes

This scenario tests the session-end flow. Send it after issuing `/end` or an equivalent
session-close signal.

```
/end
```

Expected checks:
- Engine exits the turn loop and shifts to OOC debrief mode.
- Asks the player for at least one **Star** (something that landed well this session) and at least one **Wish** (something to explore or do differently next session).
- Provides a brief narrative recap of the session's meaningful events (3–5 sentences).
- Does not generate CYOA options (debrief is freeform).
- Tone is warm, reflective, and player-directed.
- Offers to save session notes before closing.

---

## Evaluation record

| ID | Scenario | Result | Notes |
|----|----------|--------|-------|
| A | Solo weak hit — baseline risky action | Pass | Respected risky/standard stakes; 3 options returned. |
| B | Flashback — 1-stress simple prep | Pass | Stress consumed; concrete setup benefit granted. |
| C | Safety [Pause] — tone calibration | Pass | OOC mode activated; safety constraints updated. |
| D | Solo strong hit — clean success | — | Not yet evaluated. |
| E | Solo miss — consequence escalation | — | Not yet evaluated. |
| F | Momentum burn — weak-to-strong flip | — | Not yet evaluated. |
| G | Squad critical — two 6s | — | Not yet evaluated. |
| H | Progress Move — weak hit on extreme track | — | Not yet evaluated. |
| I | [X-Card] — element removal | — | Not yet evaluated. |
| J | Aftercare debrief — Stars & Wishes | — | Not yet evaluated. |

---

## Sample evaluated outputs (system prompt loaded)

### Prompt A output excerpt

> Rain ticks on the relay casing as your splice seats. **Face Danger (solo),
> risky/standard: weak hit.**
> **State impact:** `clk-mission-archive-extraction 5/8→6/8`;
> `clk-danger-alarm-sweep 3/6→4/6`; position stays risky.
> 1) Slip deeper into the maintenance tunnel before the patrol's second sweep.
> 2) Trigger your signal scrambler now to blunt the alarm cascade.
> 3) Ghost a false maintenance ping to misdirect Captain Rhyl's team.

Result: **Pass** (agency preserved, explicit state updates, exactly 3 options,
no banned cliché phrases).

### Prompt B output excerpt

> **Flashback accepted.** You paid a dock clerk for a one-shift access key.
> **State impact:** stress `4→5`; add
> `access_key: customs-relay (1 use)`; next bypass gains `risky→controlled`.
> 1) Use the key immediately on the biometric gate.
> 2) Save the key and probe for a second ingress path.
> 3) Use the key to plant a forged audit trail while entering.

Result: **Pass** (flashback cost applied, present-scene benefit clear, exactly
3 options, no banned cliché phrases).

### Prompt C output excerpt

> **[Pause] acknowledged.** Fiction is frozen and we switch OOC.
> Updated safety: health content shifted to PG-13 soft-focus; no graphic body-harm detail.

Result: **Pass** (pause command handled correctly, agency preserved, safety
constraints updated before resuming play).

---

## Known limits in current prototype

- Resolution examples are prompt-level; no external dice service is wired yet.
- State persistence is XML-first and should later be mirrored by runtime structs.
- Golden transcript tests are not automated in this repository yet.
- Squad mode scenarios (Prompt G) require a manual play_state override until the session manager is implemented.
- The matching-challenge-dice mechanic (opportunity on strong hit / complication on miss) is not yet explicitly specified in the system prompt and is intentionally excluded from the evaluation set until it is defined in a spec revision.
