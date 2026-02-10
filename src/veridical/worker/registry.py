from typing import TYPE_CHECKING, Any, ClassVar

from veridical.worker import Worker
from veridical.worker.jules import JulesWorker

if TYPE_CHECKING:
    from veridical.cli.progress import ProgressReporter
    from veridical.config.schema import VeridicalConfig


class WorkerRegistry:
    """Registry for worker implementations."""

    _registry: ClassVar[dict[str, type[Worker]]] = {
        "jules": JulesWorker,
    }

    @classmethod
    def register(cls, backend: str, worker_cls: type[Worker]) -> None:
        """Register a new worker backend."""
        cls._registry[backend] = worker_cls

    @classmethod
    def get_worker_class(cls, backend: str) -> type[Worker]:
        """Get the worker class for the given backend."""
        if backend not in cls._registry:
            valid = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown worker backend: '{backend}'. Available: {valid}")
        return cls._registry[backend]

    @classmethod
    def create_worker(
        cls,
        config: "VeridicalConfig",
        *,
        progress_reporter: "ProgressReporter | None" = None,
        **kwargs: Any,
    ) -> Worker:
        """Create a worker instance."""
        backend = config.worker.backend
        worker_cls = cls.get_worker_class(backend)

        # Instantiate with config and optional progress reporter
        # kwargs are passed through (e.g., client, repo_path, console)
        return worker_cls(  # type: ignore
            config=config,
            progress_reporter=progress_reporter,
            **kwargs,
        )
