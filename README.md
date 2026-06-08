# AURPG - Amalgamated Ultimate RPG System

AURPG is a framework for structuring LLM-powered text-based roleplay, leveraging frontier language
models to handle rich, complex state across long-running sessions.

## Vision

Traditional text RPGs rely on hand-crafted state machines and scripted outcomes. AURPG replaces
that rigid backbone with a frontier LLM that:

- Maintains narrative state - tracks characters, inventory, relationships, world events, and quest
  progress across arbitrarily long sessions.
- Drives dynamic storytelling - responds coherently to any player action without pre-scripted
  branches.
- Enforces structured output - uses a typed schema layer so game logic can reliably parse and act on
  model responses.
- Scales to complexity - supports multi-party campaigns, persistent worlds, and cross-session
  continuity.

## Status

Pre-alpha - prompt prototype ready for player-testing prep.

The system architecture and component design are still being documented, but the current XML prompt
prototype and sample state are now packaged for manual playtests. Start with
[`docs/PLAYER_TESTING.md`](docs/PLAYER_TESTING.md) and
[`docs/PROMPT_USAGE_GUIDE.md`](docs/PROMPT_USAGE_GUIDE.md).

## Repository Layout

```
AURPG/
|-- docs/          # Design documents, architecture notes, and specs
|-- src/           # Source code (populated once design is approved)
|   `-- aurpg/
`-- tests/         # Test suite and future harness checks
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

See [LICENSE](LICENSE).
