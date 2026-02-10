"""Tests for WorkerRegistry."""

import pytest

from veridical.worker.jules import JulesWorker
from veridical.worker.registry import WorkerRegistry


@pytest.mark.unit
class TestWorkerRegistry:
    """Tests for the WorkerRegistry."""

    def test_jules_registered_by_default(self) -> None:
        """Jules backend is registered at import time."""
        assert "jules" in WorkerRegistry.available()

    def test_resolve_jules(self) -> None:
        """Resolving 'jules' returns JulesWorker class."""
        cls = WorkerRegistry.resolve("jules")
        assert cls is JulesWorker

    def test_resolve_unknown_raises(self) -> None:
        """Resolving an unknown backend raises KeyError."""
        with pytest.raises(KeyError, match="Unknown worker backend 'nonexistent'"):
            WorkerRegistry.resolve("nonexistent")

    def test_register_custom_backend(self) -> None:
        """Custom backends can be registered and resolved."""

        class CustomWorker:
            pass

        WorkerRegistry.register("custom", CustomWorker)
        try:
            assert WorkerRegistry.resolve("custom") is CustomWorker
            assert "custom" in WorkerRegistry.available()
        finally:
            # Clean up — re-register builtins only
            from veridical.worker.registry import _REGISTRY

            _REGISTRY.pop("custom", None)

    def test_available_returns_sorted(self) -> None:
        """available() returns backend names in sorted order."""
        backends = WorkerRegistry.available()
        assert backends == sorted(backends)

    def test_clear_and_reregister(self) -> None:
        """clear() removes all backends; builtins can be re-registered."""
        WorkerRegistry.clear()
        try:
            assert WorkerRegistry.available() == []
            with pytest.raises(KeyError):
                WorkerRegistry.resolve("jules")
        finally:
            # Restore builtins
            from veridical.worker.registry import _register_builtins

            _register_builtins()
        assert "jules" in WorkerRegistry.available()
