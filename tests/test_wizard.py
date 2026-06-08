"""TDD tests for aurpg.wizard — campaign creation wizard.

Tests cover:
- validate_config: valid config passes, each invalid field caught individually
- attribute sum > 10 rejected
- config_to_state_xml: well-formed XML, passes validator, embeds correct values
- run_wizard: injected prompt_fn completing all 4 stages returns correct WizardConfig
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from aurpg.wizard import WizardConfig, config_to_state_xml, run_wizard, validate_config
from aurpg.validator import validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_config(**overrides) -> WizardConfig:
    """Return a fully valid WizardConfig with sensible defaults."""
    defaults = dict(
        title="Test Campaign",
        genre="fantasy",
        tone="grim",
        canon_mode="strict_continuity",
        character_name="Hero",
        edge=2,
        heart=2,
        iron=2,
        shadow=2,
        wits=2,
        load="normal",
        safety={
            "horror": "green",
            "health": "yellow",
            "relationships": "green",
            "social_issues": "red",
        },
        orchestration_mode="strict_manual",
        initial_position="risky",
        initial_effect="standard",
    )
    defaults.update(overrides)
    return WizardConfig(**defaults)


# ---------------------------------------------------------------------------
# validate_config — happy path
# ---------------------------------------------------------------------------


class TestValidateConfigValid:
    def test_valid_config_returns_no_errors(self):
        cfg = _minimal_config()
        errors = validate_config(cfg)
        assert errors == []

    def test_all_attribute_values_at_boundaries(self):
        # edge 1, others 2, sum = 1+2+2+2+2 = 9 ≤ 10
        cfg = _minimal_config(edge=1, heart=2, iron=2, shadow=2, wits=2)
        assert validate_config(cfg) == []

    def test_sum_exactly_10_is_valid(self):
        cfg = _minimal_config(edge=2, heart=2, iron=2, shadow=2, wits=2)
        assert validate_config(cfg) == []


# ---------------------------------------------------------------------------
# validate_config — attribute range violations
# ---------------------------------------------------------------------------


class TestValidateConfigAttributeRange:
    @pytest.mark.parametrize("attr", ["edge", "heart", "iron", "shadow", "wits"])
    def test_attribute_below_1_is_rejected(self, attr):
        cfg = _minimal_config(**{attr: 0})
        errors = validate_config(cfg)
        assert any(attr in e for e in errors), f"Expected error mentioning '{attr}', got {errors}"

    @pytest.mark.parametrize("attr", ["edge", "heart", "iron", "shadow", "wits"])
    def test_attribute_above_3_is_rejected(self, attr):
        cfg = _minimal_config(**{attr: 4})
        errors = validate_config(cfg)
        assert any(attr in e for e in errors), f"Expected error mentioning '{attr}', got {errors}"

    def test_attribute_sum_above_10_is_rejected(self):
        # 3+3+3+3+3 = 15 > 10
        cfg = _minimal_config(edge=3, heart=3, iron=3, shadow=3, wits=3)
        errors = validate_config(cfg)
        assert any("sum" in e.lower() or "10" in e for e in errors), (
            f"Expected attribute-sum error, got {errors}"
        )

    def test_attribute_sum_11_is_rejected(self):
        # 3+3+2+2+1 = 11 > 10
        cfg = _minimal_config(edge=3, heart=3, iron=2, shadow=2, wits=1)
        errors = validate_config(cfg)
        assert any("sum" in e.lower() or "10" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_config — string field violations
# ---------------------------------------------------------------------------


class TestValidateConfigStringFields:
    def test_invalid_load_rejected(self):
        cfg = _minimal_config(load="ultralight")
        errors = validate_config(cfg)
        assert any("load" in e for e in errors)

    def test_invalid_canon_mode_rejected(self):
        cfg = _minimal_config(canon_mode="strict")
        errors = validate_config(cfg)
        assert any("canon_mode" in e for e in errors)

    def test_invalid_orchestration_mode_rejected(self):
        cfg = _minimal_config(orchestration_mode="auto")
        errors = validate_config(cfg)
        assert any("orchestration_mode" in e for e in errors)

    def test_invalid_initial_position_rejected(self):
        cfg = _minimal_config(initial_position="neutral")
        errors = validate_config(cfg)
        assert any("initial_position" in e for e in errors)

    def test_invalid_initial_effect_rejected(self):
        cfg = _minimal_config(initial_effect="massive")
        errors = validate_config(cfg)
        assert any("initial_effect" in e for e in errors)

    @pytest.mark.parametrize("category", ["horror", "health", "relationships", "social_issues"])
    def test_invalid_safety_status_rejected(self, category):
        safety = {
            "horror": "green",
            "health": "yellow",
            "relationships": "green",
            "social_issues": "red",
        }
        safety[category] = "orange"
        cfg = _minimal_config(safety=safety)
        errors = validate_config(cfg)
        assert any("safety" in e or category in e for e in errors), (
            f"Expected safety error for category '{category}', got {errors}"
        )


# ---------------------------------------------------------------------------
# config_to_state_xml — structure
# ---------------------------------------------------------------------------


class TestConfigToStateXml:
    def test_returns_string(self):
        cfg = _minimal_config()
        result = config_to_state_xml(cfg)
        assert isinstance(result, str)

    def test_well_formed_xml(self):
        """ET.fromstring must not raise."""
        from xml.etree import ElementTree as ET
        cfg = _minimal_config()
        xml_str = config_to_state_xml(cfg)
        # Should not raise
        root = ET.fromstring(xml_str)
        assert root is not None

    def test_has_required_top_level_elements(self):
        from xml.etree import ElementTree as ET
        cfg = _minimal_config()
        root = ET.fromstring(config_to_state_xml(cfg))
        tags = {child.tag for child in root}
        assert "session_state" in tags
        assert "state_machines" in tags
        assert "safety_profile" in tags

    def test_embeds_title(self):
        cfg = _minimal_config(title="Dragon Throne")
        xml_str = config_to_state_xml(cfg)
        assert "Dragon Throne" in xml_str

    def test_embeds_character_name(self):
        cfg = _minimal_config(character_name="Zephyr Kaine")
        xml_str = config_to_state_xml(cfg)
        assert "Zephyr Kaine" in xml_str

    def test_embeds_orchestration_mode(self):
        cfg = _minimal_config(orchestration_mode="generative_synthesis")
        xml_str = config_to_state_xml(cfg)
        assert "generative_synthesis" in xml_str

    def test_starting_stress_is_zero(self):
        from xml.etree import ElementTree as ET
        cfg = _minimal_config()
        root = ET.fromstring(config_to_state_xml(cfg))
        player = root.find("session_state/player_state")
        assert player is not None
        assert player.get("stress") == "0"

    def test_starting_momentum_is_two(self):
        from xml.etree import ElementTree as ET
        cfg = _minimal_config()
        root = ET.fromstring(config_to_state_xml(cfg))
        player = root.find("session_state/player_state")
        assert player is not None
        assert player.get("momentum") == "2"

    def test_starting_harm_is_none(self):
        from xml.etree import ElementTree as ET
        cfg = _minimal_config()
        root = ET.fromstring(config_to_state_xml(cfg))
        player = root.find("session_state/player_state")
        assert player is not None
        assert player.get("harm") == "none"

    def test_no_clocks_in_initial_state(self):
        from xml.etree import ElementTree as ET
        cfg = _minimal_config()
        root = ET.fromstring(config_to_state_xml(cfg))
        clocks_elem = root.find("state_machines/clocks")
        assert clocks_elem is not None
        assert len(list(clocks_elem)) == 0

    def test_no_progress_tracks_in_initial_state(self):
        from xml.etree import ElementTree as ET
        cfg = _minimal_config()
        root = ET.fromstring(config_to_state_xml(cfg))
        tracks_elem = root.find("state_machines/progress_tracks")
        assert tracks_elem is not None
        assert len(list(tracks_elem)) == 0

    def test_initial_position_embedded(self):
        cfg = _minimal_config(initial_position="controlled")
        xml_str = config_to_state_xml(cfg)
        assert "controlled" in xml_str

    def test_initial_effect_embedded(self):
        cfg = _minimal_config(initial_effect="great")
        xml_str = config_to_state_xml(cfg)
        assert "great" in xml_str

    def test_safety_categories_embedded(self):
        from xml.etree import ElementTree as ET
        cfg = _minimal_config(
            safety={
                "horror": "red",
                "health": "yellow",
                "relationships": "green",
                "social_issues": "yellow",
            }
        )
        root = ET.fromstring(config_to_state_xml(cfg))
        cats = {
            cat.get("name"): cat.get("status")
            for cat in root.findall("safety_profile/content_category")
        }
        assert cats.get("horror") == "red"
        assert cats.get("health") == "yellow"
        assert cats.get("relationships") == "green"
        assert cats.get("social_issues") == "yellow"

    def test_attributes_embedded_in_resources(self):
        from xml.etree import ElementTree as ET
        cfg = _minimal_config(edge=3, heart=1, iron=2, shadow=2, wits=2)
        root = ET.fromstring(config_to_state_xml(cfg))
        attrs = {
            a.get("name"): a.get("value")
            for a in root.findall("resources/attributes/attribute")
        }
        assert attrs.get("edge") == "3"
        assert attrs.get("heart") == "1"


# ---------------------------------------------------------------------------
# config_to_state_xml — passes aurpg.validator.validate()
# ---------------------------------------------------------------------------


class TestConfigToStateXmlValidator:
    def test_output_passes_validator(self):
        cfg = _minimal_config()
        xml_str = config_to_state_xml(cfg)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(xml_str)
            tmp_path = Path(fh.name)
        try:
            errors = validate(tmp_path)
            assert errors == [], "Validator errors:\n" + "\n".join(errors)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_output_passes_validator_all_modes(self):
        """Spot-check several mode combos."""
        combos = [
            ("strict_manual", "controlled", "limited"),
            ("collaborative_consult", "risky", "standard"),
            ("generative_synthesis", "desperate", "great"),
        ]
        for orch, pos, eff in combos:
            cfg = _minimal_config(
                orchestration_mode=orch,
                initial_position=pos,
                initial_effect=eff,
            )
            xml_str = config_to_state_xml(cfg)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".xml", delete=False, encoding="utf-8"
            ) as fh:
                fh.write(xml_str)
                tmp_path = Path(fh.name)
            try:
                errors = validate(tmp_path)
                assert errors == [], (
                    f"Validator errors for orch={orch}: " + "\n".join(errors)
                )
            finally:
                tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# run_wizard — injected prompt_fn
# ---------------------------------------------------------------------------


class TestRunWizard:
    def _make_prompt_fn(self, answers: list[str]):
        """Return a callable that pops from the answers list on each call."""
        answers_iter = iter(answers)

        def _fn(_prompt: str = "") -> str:
            return next(answers_iter)

        return _fn

    def test_run_wizard_returns_wizard_config(self):
        answers = [
            # Stage 1
            "My Campaign",  # title
            "sci-fi",       # genre
            "hopeful",      # tone
            "flexible_canon",  # canon_mode
            # Stage 2
            "Zara",         # character_name
            "2",            # edge
            "2",            # heart
            "2",            # iron
            "2",            # shadow
            "2",            # wits
            "light",        # load
            # Stage 3
            "green",        # horror
            "yellow",       # health
            "green",        # relationships
            "red",          # social_issues
            "collaborative_consult",  # orchestration_mode
            # Stage 4
            "risky",        # initial_position
            "standard",     # initial_effect
        ]
        prompt_fn = self._make_prompt_fn(answers)
        result = run_wizard(prompt_fn=prompt_fn)
        assert isinstance(result, WizardConfig)

    def test_run_wizard_correct_stage1_values(self):
        answers = [
            "Epic Saga", "fantasy", "dark", "sandbox",
            "Hero", "1", "2", "2", "2", "2", "heavy",
            "green", "green", "green", "green", "strict_manual",
            "controlled", "limited",
        ]
        result = run_wizard(prompt_fn=self._make_prompt_fn(answers))
        assert result.title == "Epic Saga"
        assert result.genre == "fantasy"
        assert result.tone == "dark"
        assert result.canon_mode == "sandbox"

    def test_run_wizard_correct_stage2_values(self):
        answers = [
            "T", "g", "t", "flexible_canon",
            "Kira", "3", "1", "2", "2", "2", "normal",
            "green", "green", "green", "green", "strict_manual",
            "risky", "standard",
        ]
        result = run_wizard(prompt_fn=self._make_prompt_fn(answers))
        assert result.character_name == "Kira"
        assert result.edge == 3
        assert result.heart == 1
        assert result.iron == 2
        assert result.shadow == 2
        assert result.wits == 2
        assert result.load == "normal"

    def test_run_wizard_correct_stage3_values(self):
        answers = [
            "T", "g", "t", "flexible_canon",
            "Hero", "2", "2", "2", "2", "2", "light",
            "red", "yellow", "green", "yellow", "generative_synthesis",
            "desperate", "great",
        ]
        result = run_wizard(prompt_fn=self._make_prompt_fn(answers))
        assert result.safety == {
            "horror": "red",
            "health": "yellow",
            "relationships": "green",
            "social_issues": "yellow",
        }
        assert result.orchestration_mode == "generative_synthesis"

    def test_run_wizard_correct_stage4_values(self):
        answers = [
            "T", "g", "t", "strict_continuity",
            "Hero", "2", "2", "2", "2", "2", "light",
            "green", "green", "green", "green", "collaborative_consult",
            "controlled", "great",
        ]
        result = run_wizard(prompt_fn=self._make_prompt_fn(answers))
        assert result.initial_position == "controlled"
        assert result.initial_effect == "great"

    def test_run_wizard_re_prompts_on_invalid_input(self):
        """Wizard must re-prompt if user gives invalid canon_mode, then accept valid one."""
        answers = [
            "T", "g", "t",
            "bad_mode",       # invalid canon_mode — should re-prompt
            "flexible_canon",  # valid
            "Hero", "2", "2", "2", "2", "2", "light",
            "green", "green", "green", "green", "strict_manual",
            "risky", "standard",
        ]
        result = run_wizard(prompt_fn=self._make_prompt_fn(answers))
        assert result.canon_mode == "flexible_canon"

    def test_run_wizard_re_prompts_on_invalid_attribute(self):
        """Wizard must re-prompt if attribute value out of range."""
        answers = [
            "T", "g", "t", "sandbox",
            "Hero",
            "5",  # invalid edge (> 3) — re-prompt
            "2",  # valid
            "2", "2", "2", "2", "light",
            "green", "green", "green", "green", "strict_manual",
            "risky", "standard",
        ]
        result = run_wizard(prompt_fn=self._make_prompt_fn(answers))
        assert result.edge == 2
