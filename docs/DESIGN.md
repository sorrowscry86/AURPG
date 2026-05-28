# AURPG Design Document

> **Status: Prototype in progress**
>
> AURPG is currently defining its prompt-engine architecture before application
> code is built. The first implementation-ready prototype lives at
> [`src/aurpg/prompts/aurpg_system_prompt_prototype.xml`](../src/aurpg/prompts/aurpg_system_prompt_prototype.xml).

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

## Planned follow-on sections

1. **Goals & Non-Goals** — scope of the system
2. **Architecture Overview** — high-level component diagram
3. **State Model** — how world, character, and narrative state are represented
4. **LLM Integration** — prompt strategy, structured output schemas, model selection
5. **Session Lifecycle** — initialisation, turn loop, persistence, and resumption
6. **Game Rules Layer** — how rules are enforced without hard-coding branches
7. **API / Interface Design** — how clients interact with the engine
8. **Error Handling & Safety** — content moderation, recovery from bad model output
9. **Testing Strategy** — unit, integration, and golden-path tests
10. **Roadmap** — phased delivery milestones
