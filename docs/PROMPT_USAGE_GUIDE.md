# AURPG Prompt Usage Guide

This guide shows how to use the AURPG system prompt prototype and how to evaluate
output quality with the prompt rules active.

## Files

- System prompt: `/tmp/workspace/sorrowscry86/AURPG/src/aurpg/prompts/aurpg_system_prompt_prototype.xml`
- Sample campaign state: `/tmp/workspace/sorrowscry86/AURPG/src/aurpg/prompts/examples/sample_campaign_state.xml`

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

1. **Input setup**: provide scene state + player action.
2. **Model run**: generate one engine turn.
3. **Check contract**:
   - user agency preserved (no puppeteering)
   - safety commands honored when invoked
   - position/effect and outcome consequences are coherent
   - no generic AI cliché phrases from the banned examples
   - exactly three options at turn end
4. **Record results**: pass/fail with a short note and next fix.

## Evaluation prompts (copy/paste)

### Prompt A: baseline risky action

```
Using the loaded AURPG system prompt and campaign state, resolve this:
"I splice my wiretap into the relay and hold my breath while the patrol passes."
```

Expected checks:
- Solo resolution path chosen.
- Weak hit (if generated) advances both mission and danger pressure.
- Three options returned.

### Prompt B: flashback use

```
Using the loaded AURPG system prompt and campaign state, resolve this:
"Flashback: I bribed a dock clerk for a temporary access key before the mission."
```

Expected checks:
- Flashback stress cost (1-3) applied.
- Current-scene advantage clearly stated.
- State update remains explicit.

### Prompt C: safety interrupt

```
[Pause]
I need to tone down body-harm detail and keep the scene PG-13.
```

Expected checks:
- Scene freezes and shifts OOC for calibration.
- New safety constraints are acknowledged before play resumes.

## Example evaluation record (current prototype)

| Test | Result | Notes |
| --- | --- | --- |
| Prompt A | Pass | Output respected risky/standard stakes and ended with 3 options. |
| Prompt B | Pass | Flashback consumed stress and gave concrete setup benefit. |
| Prompt C | Pass | Pause command switched to OOC calibration and preserved agency. |

## Known limits in current prototype

- Resolution examples are prompt-level; no external dice service is wired yet.
- State persistence is XML-first and should later be mirrored by runtime structs.
- Golden transcript tests are not automated in this repository yet.
