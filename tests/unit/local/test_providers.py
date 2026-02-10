"""Unit tests for local provider protocol, registry, and built-in providers."""

from unittest.mock import patch

import pytest

from veridical.local.providers.claude_code import ClaudeCodeProvider
from veridical.local.providers.gemini_cli import GeminiCliProvider
from veridical.local.providers.protocol import LocalProvider
from veridical.local.providers.registry import LocalProviderRegistry

# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    """Verify built-in providers satisfy the LocalProvider protocol."""

    def test_claude_code_satisfies_protocol(self):
        assert isinstance(ClaudeCodeProvider(), LocalProvider)

    def test_gemini_cli_satisfies_protocol(self):
        assert isinstance(GeminiCliProvider(), LocalProvider)


# ---------------------------------------------------------------------------
# LocalProviderRegistry
# ---------------------------------------------------------------------------


class TestLocalProviderRegistry:
    """Tests for the provider registry."""

    def setup_method(self):
        """Save and restore registry state around each test."""
        self._saved = dict(LocalProviderRegistry._get_registry())

    def teardown_method(self):
        LocalProviderRegistry.clear()
        for name, cls in self._saved.items():
            LocalProviderRegistry.register(name, cls)

    def test_builtins_registered(self):
        names = LocalProviderRegistry.available()
        assert "claude-code" in names
        assert "gemini-cli" in names

    def test_resolve_known(self):
        cls = LocalProviderRegistry.resolve("claude-code")
        assert cls is ClaudeCodeProvider

    def test_resolve_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown local provider"):
            LocalProviderRegistry.resolve("nonexistent")

    def test_register_and_resolve_custom(self):
        class FakeProvider:
            pass

        LocalProviderRegistry.register("fake", FakeProvider)
        assert LocalProviderRegistry.resolve("fake") is FakeProvider

    def test_register_overwrites(self):
        class A:
            pass

        class B:
            pass

        LocalProviderRegistry.register("dup", A)
        LocalProviderRegistry.register("dup", B)
        assert LocalProviderRegistry.resolve("dup") is B

    def test_clear(self):
        LocalProviderRegistry.clear()
        assert LocalProviderRegistry.available() == []

    def test_detect_available(self):
        infos = LocalProviderRegistry.detect_available()
        assert len(infos) >= 2
        names = [i.name for i in infos]
        assert "claude-code" in names
        assert "gemini-cli" in names
        for info in infos:
            assert isinstance(info.detected, bool)
            assert isinstance(info.description, str)


# ---------------------------------------------------------------------------
# ClaudeCodeProvider
# ---------------------------------------------------------------------------


class TestClaudeCodeProvider:
    """Tests for the Claude Code provider."""

    def setup_method(self):
        self.provider = ClaudeCodeProvider()

    def test_name(self):
        assert self.provider.name == "claude-code"

    def test_description(self):
        assert "Claude Code" in self.provider.description

    def test_default_mode(self):
        assert self.provider.default_mode() == "subprocess"

    # -- subprocess mode --

    def test_build_command_subprocess_basic(self):
        cmd = self.provider.build_command("Fix the bug", mode="subprocess")
        assert "claude" in cmd
        assert "--print" in cmd
        assert "--output-format" in cmd
        assert "text" in cmd
        assert "-p" in cmd
        assert "Fix the bug" in cmd

    def test_build_command_subprocess_with_error_context(self):
        cmd = self.provider.build_command(
            "Fix the bug", error_context="test failed", mode="subprocess"
        )
        assert "--append-system-prompt" in cmd
        assert "test failed" in cmd

    def test_build_command_subprocess_no_error_context(self):
        cmd = self.provider.build_command("Fix the bug", mode="subprocess")
        assert "--append-system-prompt" not in cmd

    # -- interactive mode --

    def test_build_command_interactive(self):
        cmd = self.provider.build_command("Fix the bug", mode="interactive")
        assert cmd == "claude"

    def test_build_command_interactive_ignores_error_context(self):
        cmd = self.provider.build_command(
            "Fix the bug", error_context="test failed", mode="interactive"
        )
        assert cmd == "claude"

    # -- detection --

    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_detect_found(self, mock_which):
        assert self.provider.detect() is True
        mock_which.assert_called_with("claude")

    @patch("shutil.which", return_value=None)
    def test_detect_not_found(self, _mock_which):
        assert self.provider.detect() is False


# ---------------------------------------------------------------------------
# GeminiCliProvider
# ---------------------------------------------------------------------------


class TestGeminiCliProvider:
    """Tests for the Gemini CLI provider."""

    def setup_method(self):
        self.provider = GeminiCliProvider()

    def test_name(self):
        assert self.provider.name == "gemini-cli"

    def test_description(self):
        assert "Gemini" in self.provider.description

    def test_default_mode(self):
        assert self.provider.default_mode() == "subprocess"

    # -- subprocess mode --

    def test_build_command_subprocess_basic(self):
        cmd = self.provider.build_command("Fix the bug", mode="subprocess")
        assert "gemini" in cmd
        assert "-p" in cmd
        assert "Fix the bug" in cmd

    def test_build_command_subprocess_with_error_context(self):
        cmd = self.provider.build_command(
            "Fix the bug", error_context="test failed", mode="subprocess"
        )
        assert "gemini" in cmd
        assert "Fix the bug" in cmd
        assert "test failed" in cmd

    def test_build_command_subprocess_no_error_context(self):
        cmd = self.provider.build_command("Fix the bug", mode="subprocess")
        assert "test failed" not in cmd

    # -- interactive mode --

    def test_build_command_interactive(self):
        cmd = self.provider.build_command("Fix the bug", mode="interactive")
        assert cmd == "gemini"

    def test_build_command_interactive_ignores_error_context(self):
        cmd = self.provider.build_command(
            "Fix the bug", error_context="test failed", mode="interactive"
        )
        assert cmd == "gemini"

    # -- detection --

    @patch("shutil.which", return_value="/usr/bin/gemini")
    def test_detect_found(self, mock_which):
        assert self.provider.detect() is True
        mock_which.assert_called_with("gemini")

    @patch("shutil.which", return_value=None)
    def test_detect_not_found(self, _mock_which):
        assert self.provider.detect() is False
