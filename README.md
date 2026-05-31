# AURPG — Amalgamated Ultimate RPG System

AURPG is a framework for structuring LLM-powered text-based roleplay, leveraging frontier language models to handle rich, complex state across long-running sessions.

## Vision

Traditional text RPGs rely on hand-crafted state machines and scripted outcomes. AURPG replaces that rigid backbone with a frontier LLM that:

- **Maintains narrative state** — tracks characters, inventory, relationships, world events, and quest progress across arbitrarily long sessions.
- **Drives dynamic storytelling** — responds coherently to any player action without pre-scripted branches.
- **Enforces structured output** — uses a typed schema layer so game logic can reliably parse and act on model responses.
- **Scales to complexity** — supports multi-party campaigns, persistent worlds, and cross-session continuity.

## Status

**Pre-alpha — prompt-engineering phase.**

The XML system prompt prototype is functional and manually evaluated. The canonical state schema and XML validator are in place. The design document is complete. Implementation of a Python session wrapper is the next milestone.

See [`docs/DESIGN.md`](docs/DESIGN.md) for the full specification and roadmap.

## Quick start (developer evaluation)

```bash
git clone https://github.com/sorrowscry86/AURPG.git
cd AURPG
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                     # run the test suite
```

To run the engine:

1. Load `src/aurpg/prompts/aurpg_system_prompt_prototype.xml` as the system instruction in your LLM client.
2. Load `src/aurpg/prompts/examples/sample_campaign_state.xml` into context.
3. Send a player action.
4. See `docs/PROMPT_USAGE_GUIDE.md` for evaluation criteria and canonical test prompts.

## Repository Layout

```
AURPG/
├── docs/                        # Design document, prompt usage guide
├── src/aurpg/
│   ├── prompts/
│   │   ├── aurpg_system_prompt_prototype.xml   # The engine — load as system instruction
│   │   └── examples/
│   │       └── sample_campaign_state.xml       # Reference runtime state
│   ├── state.py                 # Canonical Python dataclass state model
│   └── validator.py             # Campaign state XML validator
└── tests/
    ├── test_validator.py        # Validator unit tests
    └── test_state.py            # State model unit tests (Clock, ProgressTrack)
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

See [LICENSE](LICENSE).
