"""Local provider presets for Veridical.

Provides named provider configurations for popular local AI coding tools,
encapsulating tool-specific command construction, error delivery, and detection.
"""

from veridical.local.providers.protocol import LocalProvider
from veridical.local.providers.registry import LocalProviderRegistry

__all__ = ["LocalProvider", "LocalProviderRegistry"]
