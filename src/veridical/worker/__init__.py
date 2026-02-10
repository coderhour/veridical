"""Worker abstraction layer for Veridical.

Provides a protocol-based interface for AI worker backends,
decoupling the supervisor loop from any specific implementation.
"""

from veridical.worker.models import (
    PollResult,
    SyncResult,
    WorkerConfig,
    WorkHandle,
    WorkResult,
)
from veridical.worker.protocol import Worker
from veridical.worker.registry import WorkerRegistry

__all__ = [
    "PollResult",
    "SyncResult",
    "WorkHandle",
    "WorkResult",
    "Worker",
    "WorkerConfig",
    "WorkerRegistry",
]
