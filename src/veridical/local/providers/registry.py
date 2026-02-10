"""Local provider registry for resolving provider names to implementations."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Global registry mapping provider names to provider instances.
_REGISTRY: dict[str, type] = {}


@dataclass
class ProviderInfo:
    """Summary information about a registered provider."""

    name: str
    description: str
    detected: bool


class LocalProviderRegistry:
    """Maps provider names to provider classes.

    Usage::

        LocalProviderRegistry.register("claude-code", ClaudeCodeProvider)
        provider_cls = LocalProviderRegistry.resolve("claude-code")
        provider = provider_cls()
    """

    @staticmethod
    def register(name: str, provider_cls: type) -> None:
        """Register a provider class under a name.

        Args:
            name: Provider name (e.g. ``"claude-code"``, ``"gemini-cli"``)
            provider_cls: Class that satisfies the LocalProvider protocol
        """
        _REGISTRY[name] = provider_cls
        logger.debug(f"Registered local provider: {name}")

    @staticmethod
    def resolve(name: str) -> type:
        """Resolve a provider name to its class.

        Args:
            name: Provider name

        Returns:
            The registered provider class

        Raises:
            KeyError: If the provider name is not registered
        """
        if name not in _REGISTRY:
            available = ", ".join(sorted(_REGISTRY.keys())) or "(none)"
            raise KeyError(f"Unknown local provider '{name}'. Available providers: {available}")
        return _REGISTRY[name]

    @staticmethod
    def available() -> list[str]:
        """Return sorted list of registered provider names."""
        return sorted(_REGISTRY.keys())

    @staticmethod
    def detect_available() -> list[ProviderInfo]:
        """Return info for all registered providers, including detection status.

        Returns:
            List of ProviderInfo with detection results
        """
        results: list[ProviderInfo] = []
        for name in sorted(_REGISTRY.keys()):
            provider_cls = _REGISTRY[name]
            provider = provider_cls()
            results.append(
                ProviderInfo(
                    name=name,
                    description=provider.description,
                    detected=provider.detect(),
                )
            )
        return results

    @staticmethod
    def clear() -> None:
        """Clear all registered providers (useful for testing)."""
        _REGISTRY.clear()

    @staticmethod
    def _get_registry() -> dict[str, type]:
        """Return the internal registry dict (for testing)."""
        return _REGISTRY


def _register_builtins() -> None:
    """Register built-in local providers.

    Called at import time so that providers are always available.
    """
    from veridical.local.providers.claude_code import ClaudeCodeProvider
    from veridical.local.providers.gemini_cli import GeminiCliProvider

    LocalProviderRegistry.register("claude-code", ClaudeCodeProvider)
    LocalProviderRegistry.register("gemini-cli", GeminiCliProvider)


_register_builtins()
