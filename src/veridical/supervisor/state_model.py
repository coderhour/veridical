"""Pydantic model for serializing supervisor loop state."""

import json
import logging
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

STATE_FILE_NAME = ".veridical_state.json"


class LoopState(BaseModel):
    """Represents the persistent state of the supervisor loop."""

    task_description: str = Field(
        "", description="The original task description for this loop."
    )
    tasks_file: str | None = Field(
        None, description="Path to the tasks.md file for dynamic verification."
    )
    iteration: int = Field(
        1, description="The current iteration number (1-based)."
    )
    session_id: str | None = Field(
        None, description="The active Jules session ID."
    )
    error_context: str | None = Field(
        None, description="The error context from the previous failed iteration."
    )
    work_branch: str | None = Field(
        None, description="The name of the Git branch created for this loop."
    )

    @classmethod
    def get_state_file_path(cls, repo_path: Path) -> Path:
        """Get the default path for the state file."""
        return repo_path / STATE_FILE_NAME

    def save(self, repo_path: Path) -> None:
        """Save the current state to a JSON file in the repo root.

        Args:
            repo_path: Path to the repository root.
        """
        state_file = self.get_state_file_path(repo_path)
        try:
            state_json = self.model_dump_json(indent=2)
            state_file.write_text(state_json)
            logger.info(f"Saved supervisor state to {state_file}")
        except IOError as e:
            logger.error(f"Error saving state file to {state_file}: {e}", exc_info=True)
            # Decide if we should raise or just log
            raise

    @classmethod
    def load(cls, repo_path: Path) -> Self | None:
        """Load state from the JSON file if it exists.

        Args:
            repo_path: Path to the repository root.

        Returns:
            An instance of LoopState or None if the file doesn't exist.
        """
        state_file = cls.get_state_file_path(repo_path)
        if not state_file.exists():
            return None

        try:
            state_json = state_file.read_text()
            state = cls.model_validate_json(state_json)
            logger.info(f"Loaded supervisor state from {state_file}")
            return state
        except (IOError, ValidationError, json.JSONDecodeError) as e:
            logger.warning(
                f"Could not load or validate state file at {state_file}. "
                f"Starting with a fresh state. Error: {e}"
            )
            # If state is corrupted, it's safer to start fresh.
            # We can optionally back up the corrupted file.
            cls.clear(repo_path)
            return None

    @classmethod
    def clear(cls, repo_path: Path) -> None:
        """Remove the state file from the repo root.

        Args:
            repo_path: Path to the repository root.
        """
        state_file = cls.get_state_file_path(repo_path)
        if state_file.exists():
            try:
                state_file.unlink()
                logger.info(f"Cleared supervisor state file: {state_file}")
            except IOError as e:
                logger.error(f"Error clearing state file {state_file}: {e}", exc_info=True)
                raise
