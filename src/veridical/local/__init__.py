"""Local execution components for Veridical."""

from veridical.local.providers import LocalProvider, LocalProviderRegistry
from veridical.local.runner import LocalRunner
from veridical.local.supervisor import LocalSupervisor

__all__ = ["LocalProvider", "LocalProviderRegistry", "LocalRunner", "LocalSupervisor"]
