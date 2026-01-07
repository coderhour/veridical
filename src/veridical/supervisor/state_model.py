import json
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field


class LoopState(BaseModel):
    """Represents the persistent state of a supervisor loop."""

    iteration: int = Field(..., description="The current iteration number.")
    session_id: str | None = Field(None, description="The active Jules session ID.")
    error_context: str | None = Field(
        None, description="The last error context for feedback."
    )
    work_branch: str = Field(..., description="The name of the git branch for this run.")
    tasks_file: Path | None = Field(
        None, description="Path to the tasks.md file for the run."
    )

    @classmethod
    def state_file_path(cls, repo_root: Path) -> Path:
        """Get the path to the state file."""
        return repo_root / ".veridical_state.json"

    def save(self, repo_root: Path) -> None:
        """Save the current state to a JSON file in the repo root."""
        state_file = self.state_file_path(repo_root)
        # Pydantic's model_dump is used for serialization, which handles Path objects
        with state_file.open("w") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2)

    @classmethod
    def load(cls, repo_root: Path) -> Self | None:
        """Load state from the JSON file if it exists."""
        state_file = cls.state_file_path(repo_root)
        if not state_file.exists():
            return None
        with state_file.open("r") as f:
            data = json.load(f)
            return cls(**data)

    @classmethod
    def clear(cls, repo_root: Path) -> None:
        """Remove the state file if it exists."""
        state_file = cls.state_file_path(repo_root)
        if state_file.exists():
            state_file.unlink()
