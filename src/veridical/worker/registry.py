"""Worker registry for resolving backend names to worker classes."""

import logging

logger = logging.getLogger(__name__)

# Global registry mapping backend names to factory callables.
# Each factory receives (config, **backend_config) and returns a Worker instance.
_REGISTRY: dict[str, type] = {}


class WorkerRegistry:
    """Maps backend names to worker classes.

    Usage::

        WorkerRegistry.register("jules", JulesWorker)
        worker_cls = WorkerRegistry.resolve("jules")
    """

    @staticmethod
    def register(name: str, worker_cls: type) -> None:
        """Register a worker class under a backend name.

        Args:
            name: Backend name (e.g. ``"jules"``, ``"local"``)
            worker_cls: Class that satisfies the Worker protocol
        """
        _REGISTRY[name] = worker_cls
        logger.debug(f"Registered worker backend: {name}")

    @staticmethod
    def resolve(name: str) -> type:
        """Resolve a backend name to its worker class.

        Args:
            name: Backend name

        Returns:
            The registered worker class

        Raises:
            KeyError: If the backend name is not registered
        """
        if name not in _REGISTRY:
            available = ", ".join(sorted(_REGISTRY.keys())) or "(none)"
            raise KeyError(f"Unknown worker backend '{name}'. Available backends: {available}")
        return _REGISTRY[name]

    @staticmethod
    def available() -> list[str]:
        """Return sorted list of registered backend names."""
        return sorted(_REGISTRY.keys())

    @staticmethod
    def clear() -> None:
        """Clear all registered backends (useful for testing)."""
        _REGISTRY.clear()


def _register_builtins() -> None:
    """Register built-in worker backends.

    Called at import time so that ``jules`` is always available.
    """
    from veridical.worker.jules import JulesWorker

    WorkerRegistry.register("jules", JulesWorker)


_register_builtins()
