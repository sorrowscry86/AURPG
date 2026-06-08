"""Shared fixtures for prompt evaluation tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
SYSTEM_PROMPT_PATH = REPO_ROOT / "src/aurpg/prompts/aurpg_system_prompt_prototype.xml"
CAMPAIGN_STATE_PATH = REPO_ROOT / "src/aurpg/prompts/examples/sample_campaign_state.xml"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.yaml"
    with path.open() as f:
        return yaml.safe_load(f)


def all_fixture_names() -> list[str]:
    return [p.stem for p in sorted(FIXTURES_DIR.glob("*.yaml"))]


@pytest.fixture(scope="session")
def system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text()


@pytest.fixture(scope="session")
def campaign_state() -> str:
    return CAMPAIGN_STATE_PATH.read_text()


@pytest.fixture(scope="session")
def anthropic_client():
    """Return an Anthropic client, or skip if no API key is set."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping live LLM tests")
    import anthropic
    return anthropic.Anthropic(api_key=api_key)
