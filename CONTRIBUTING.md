# Contributing to AURPG

Thank you for your interest in AURPG!

## Current Status

The project is in the **pre-alpha / planning phase**. We are finalising the system design before beginning major implementation work. Please review [`docs/DESIGN.md`](docs/DESIGN.md) to track the specification's progress.

## How to Help Right Now

- **Design feedback** — open an issue with `[design]` in the title to discuss architectural decisions.
- **Research** — share findings on LLM structured-output techniques, state management patterns, or relevant prior art.

## Development Guidelines (once implementation begins)

### Setup

```bash
# Clone the repo
git clone https://github.com/sorrowscry86/AURPG.git
cd AURPG

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies (to be added)
pip install -e ".[dev]"
```

### Workflow

1. Fork the repository and create a feature branch from `main`.
2. Write tests alongside new code in `tests/`.
3. Ensure all tests pass before opening a pull request.
4. Keep pull requests focused — one concern per PR.

### Code Style

- Python 3.11+
- Follow [PEP 8](https://peps.python.org/pep-0008/) with a line length of 100.
- Use type hints throughout.

## Code of Conduct

Be respectful and constructive. This is a collaborative project.
