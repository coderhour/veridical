"""Unit tests for RuleManager."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from veridical.learning.models import LearnedRule
from veridical.learning.rules import RuleManager


@pytest.fixture
def rules_file(tmp_path: Path) -> Path:
    return tmp_path / ".veridical" / "learned_rules.yaml"


@pytest.fixture
def manager(rules_file: Path) -> RuleManager:
    return RuleManager(rules_file)


def _make_rule(
    rule_id: str = "r1",
    trigger: str = "gate:pytest",
    text: str = "Run tests first",
    confidence: float = 0.8,
    created_at: datetime | None = None,
    success_rate: float = 0.6,
) -> LearnedRule:
    return LearnedRule(
        id=rule_id,
        trigger_pattern=trigger,
        rule_text=text,
        confidence_score=confidence,
        created_at=created_at or datetime.now(),
        applied_count=0,
        success_rate=success_rate,
    )


class TestRuleManager:
    def test_load_empty(self, manager: RuleManager) -> None:
        rules = manager.load()
        assert rules == []

    def test_save_and_load(self, manager: RuleManager) -> None:
        rules = [_make_rule("r1"), _make_rule("r2", trigger="error:import errors")]
        manager.save(rules)

        loaded = manager.load()
        assert len(loaded) == 2
        assert loaded[0].id == "r1"
        assert loaded[1].id == "r2"

    def test_save_creates_parent_dirs(self, manager: RuleManager) -> None:
        assert not manager.rules_file.parent.exists()
        manager.save([_make_rule()])
        assert manager.rules_file.exists()

    def test_load_invalid_yaml(self, rules_file: Path) -> None:
        rules_file.parent.mkdir(parents=True, exist_ok=True)
        rules_file.write_text("not: [valid: yaml: {{")
        manager = RuleManager(rules_file)
        rules = manager.load()
        assert rules == []

    def test_load_empty_file(self, rules_file: Path) -> None:
        rules_file.parent.mkdir(parents=True, exist_ok=True)
        rules_file.write_text("")
        manager = RuleManager(rules_file)
        rules = manager.load()
        assert rules == []

    def test_saved_file_is_human_readable(self, manager: RuleManager) -> None:
        manager.save([_make_rule()])
        content = manager.rules_file.read_text()
        assert "rules:" in content
        assert "rule_text:" in content

    def test_roundtrip_preserves_fields(self, manager: RuleManager) -> None:
        original = _make_rule(
            rule_id="test-id",
            trigger="error:type errors",
            text="Check types carefully",
            confidence=0.75,
            success_rate=0.9,
        )
        manager.save([original])
        loaded = manager.load()
        assert len(loaded) == 1
        assert loaded[0].id == "test-id"
        assert loaded[0].trigger_pattern == "error:type errors"
        assert loaded[0].rule_text == "Check types carefully"
        assert loaded[0].confidence_score == 0.75
        assert loaded[0].success_rate == 0.9

    def test_apply_to_agents_md_requires_confirmation(
        self, manager: RuleManager, tmp_path: Path
    ) -> None:
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text("# My Project\n\nSome content.\n")

        rules = [_make_rule()]
        with pytest.raises(PermissionError):
            manager.apply_to_agents_md(rules, agents_path, confirmed=False)

        # File should not be modified
        assert "Learned Rules" not in agents_path.read_text()

    def test_apply_to_agents_md_confirmed(self, manager: RuleManager, tmp_path: Path) -> None:
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text("# My Project\n\nSome content.\n")

        rules = [_make_rule()]
        manager.apply_to_agents_md(rules, agents_path, confirmed=True)

        content = agents_path.read_text()
        assert "# Learned Rules" in content
        assert "Run tests first" in content
        assert "# My Project" in content  # Original content preserved

    def test_apply_to_agents_md_replaces_existing_section(
        self, manager: RuleManager, tmp_path: Path
    ) -> None:
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text("# My Project\n\n# Learned Rules\n\n- Old rule\n")

        rules = [_make_rule(text="New rule")]
        manager.apply_to_agents_md(rules, agents_path, confirmed=True)

        content = agents_path.read_text()
        assert "Old rule" not in content
        assert "New rule" in content
        assert content.count("# Learned Rules") == 1

    def test_apply_to_agents_md_empty_rules(self, manager: RuleManager, tmp_path: Path) -> None:
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text("# My Project\n")

        result = manager.apply_to_agents_md([], agents_path, confirmed=True)
        assert result == ""

    def test_prune_removes_stale_rules(self, manager: RuleManager) -> None:
        old_date = datetime.now() - timedelta(days=100)
        rules = [
            _make_rule("r1", created_at=old_date, success_rate=0.3),  # Should be pruned
            _make_rule("r2", created_at=old_date, success_rate=0.8),  # Kept (high success)
            _make_rule("r3", success_rate=0.3),  # Kept (recent)
        ]
        manager.save(rules)

        pruned = manager.prune(max_age_days=90)
        assert pruned == 1

        remaining = manager.load()
        assert len(remaining) == 2
        ids = {r.id for r in remaining}
        assert "r1" not in ids
        assert "r2" in ids
        assert "r3" in ids

    def test_prune_no_stale_rules(self, manager: RuleManager) -> None:
        rules = [_make_rule("r1"), _make_rule("r2")]
        manager.save(rules)

        pruned = manager.prune(max_age_days=90)
        assert pruned == 0

    def test_prune_empty_file(self, manager: RuleManager) -> None:
        pruned = manager.prune()
        assert pruned == 0
