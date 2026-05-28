# AURPG Design Document

> **Status: Pending**
>
> This document will define the architecture, component boundaries, data schemas,
> and LLM integration strategy for AURPG.  Implementation will begin once this
> specification is approved.

---

## Sections (planned)

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

---

*Fill in each section once the design review is complete.*
