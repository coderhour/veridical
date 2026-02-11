"""Task decomposition for parallel orchestration."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Subtask:
    """A single independent subtask derived from decomposition."""

    id: str
    description: str
    files_hint: list[str] = field(default_factory=list)


class TaskDecomposer:
    """Decomposes a compound task into independent subtasks.

    Uses heuristic splitting based on task structure (numbered lists,
    bullet points, OpenSpec task files).  An optional LLM-based
    decomposition path can be added later via ``--smart-decompose``.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decompose(self, task_description: str) -> list[Subtask]:
        """Split *task_description* into independent subtasks.

        The decomposer tries, in order:
        1. Numbered list items (``1. …``, ``2. …``)
        2. Markdown bullet items (``- …`` / ``* …``)
        3. Sentence splitting on ``;`` or newline boundaries

        If none of these yield more than one item the original task is
        returned as a single subtask.

        Args:
            task_description: Free-text or structured task description.

        Returns:
            List of :class:`Subtask` instances (always ≥ 1).
        """
        subtasks = (
            self._try_numbered_list(task_description)
            or self._try_bullet_list(task_description)
            or self._try_sentence_split(task_description)
        )

        if not subtasks:
            subtasks = [Subtask(id="task-1", description=task_description.strip())]

        logger.info("Decomposed task into %d subtask(s)", len(subtasks))
        return subtasks

    def decompose_from_tasks_file(self, tasks_file: Path) -> list[Subtask]:
        """Decompose from an OpenSpec ``tasks.md`` file.

        Each top-level unchecked checkbox item (``- [ ] …``) becomes a
        subtask.

        Args:
            tasks_file: Path to a ``tasks.md`` file.

        Returns:
            List of :class:`Subtask` instances.
        """
        if not tasks_file.exists():
            logger.warning("Tasks file not found: %s", tasks_file)
            return []

        text = tasks_file.read_text()
        pattern = re.compile(r"^-\s*\[\s*\]\s+(.+)$", re.MULTILINE)
        matches = pattern.findall(text)

        subtasks: list[Subtask] = []
        for idx, match in enumerate(matches, 1):
            subtasks.append(Subtask(id=f"task-{idx}", description=match.strip()))

        logger.info(
            "Decomposed tasks file %s into %d subtask(s)",
            tasks_file,
            len(subtasks),
        )
        return subtasks

    # ------------------------------------------------------------------
    # Heuristic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _try_numbered_list(text: str) -> list[Subtask] | None:
        pattern = re.compile(r"^\s*(\d+)[.)]\s+(.+)$", re.MULTILINE)
        matches = pattern.findall(text)
        if len(matches) < 2:
            return None
        return [Subtask(id=f"task-{num}", description=desc.strip()) for num, desc in matches]

    @staticmethod
    def _try_bullet_list(text: str) -> list[Subtask] | None:
        pattern = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)
        matches = pattern.findall(text)
        if len(matches) < 2:
            return None
        return [Subtask(id=f"task-{i}", description=m.strip()) for i, m in enumerate(matches, 1)]

    @staticmethod
    def _try_sentence_split(text: str) -> list[Subtask] | None:
        parts = [p.strip() for p in re.split(r"[;\n]", text) if p.strip()]
        if len(parts) < 2:
            return None
        return [Subtask(id=f"task-{i}", description=p) for i, p in enumerate(parts, 1)]
