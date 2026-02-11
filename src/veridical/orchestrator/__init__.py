"""Multi-agent parallel orchestration for Veridical."""

from veridical.orchestrator.decomposer import TaskDecomposer
from veridical.orchestrator.dispatcher import ParallelDispatcher
from veridical.orchestrator.loop import OrchestratorLoop
from veridical.orchestrator.resolver import ConflictResolver

__all__ = [
    "ConflictResolver",
    "OrchestratorLoop",
    "ParallelDispatcher",
    "TaskDecomposer",
]
