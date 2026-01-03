"""Dynamic AGENTS.md constraint injection."""

from pathlib import Path


class AgentsMdInjector:
    """Manages dynamic injection of constraints into AGENTS.md.

    This allows Veridical to add ephemeral constraints based on
    the current iteration's context.
    """

    EPHEMERAL_HEADER = "# EPHEMERAL CONSTRAINT"
    EPHEMERAL_MARKER = "<!-- VERIDICAL:EPHEMERAL -->"

    def __init__(self, repo_path: Path) -> None:
        """Initialize the injector.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path
        self.agents_md_path = repo_path / "AGENTS.md"

    def read_agents_md(self) -> str:
        """Read the current AGENTS.md content.

        Returns:
            Content of AGENTS.md, or empty string if not found
        """
        if self.agents_md_path.exists():
            return self.agents_md_path.read_text()
        return ""

    def inject_constraints(self, constraints: list[str]) -> str:
        """Inject ephemeral constraints into AGENTS.md content.

        This does not modify the file - it returns the modified content
        for inclusion in the prompt context.

        Args:
            constraints: List of constraint strings to inject

        Returns:
            AGENTS.md content with injected constraints
        """
        base_content = self.read_agents_md()

        if not constraints:
            return base_content

        # Build ephemeral section
        ephemeral_lines = [
            "",
            self.EPHEMERAL_MARKER,
            self.EPHEMERAL_HEADER,
            "",
        ]
        for constraint in constraints:
            ephemeral_lines.append(f"- {constraint}")
        ephemeral_lines.append("")
        ephemeral_lines.append(self.EPHEMERAL_MARKER)

        ephemeral_section = "\n".join(ephemeral_lines)

        return f"{base_content}\n{ephemeral_section}"

    def strip_ephemeral(self, content: str) -> str:
        """Remove ephemeral sections from AGENTS.md content.

        Args:
            content: AGENTS.md content that may contain ephemeral sections

        Returns:
            Content with ephemeral sections removed
        """
        lines = content.split("\n")
        result_lines: list[str] = []
        in_ephemeral = False

        for line in lines:
            if self.EPHEMERAL_MARKER in line:
                in_ephemeral = not in_ephemeral
                continue
            if not in_ephemeral:
                result_lines.append(line)

        return "\n".join(result_lines).strip()
