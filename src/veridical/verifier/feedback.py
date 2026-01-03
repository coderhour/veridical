"""Error summarization for feedback generation."""

import re

from veridical.models.result import GateResult, VerificationResult


class FeedbackGenerator:
    """Generates error summaries for feedback to the next iteration."""

    def __init__(self, max_length: int = 2000) -> None:
        """Initialize the feedback generator.

        Args:
            max_length: Maximum length of generated feedback
        """
        self.max_length = max_length

    def generate_feedback(self, result: VerificationResult) -> str:
        """Generate error feedback from verification result.

        Args:
            result: Verification result containing gate outcomes

        Returns:
            Summarized error context for the next iteration
        """
        if result.passed:
            return ""

        failed_gates = result.failed_gates
        if not failed_gates:
            return ""

        sections: list[str] = []

        for gate in failed_gates:
            section = self._summarize_gate(gate)
            sections.append(section)

        full_feedback = "\n\n".join(sections)

        # Truncate if necessary
        if len(full_feedback) > self.max_length:
            full_feedback = full_feedback[: self.max_length - 3] + "..."

        return full_feedback

    def _summarize_gate(self, gate: GateResult) -> str:
        """Summarize a single gate failure.

        Args:
            gate: Failed gate result

        Returns:
            Summary string
        """
        lines = [f"## {gate.name} (exit code {gate.exit_code})"]

        # Prioritize error output
        content = gate.error_output or gate.output

        # Extract relevant parts
        extracted = self._extract_errors(content)
        lines.append(extracted)

        return "\n".join(lines)

    def _extract_errors(self, output: str) -> str:
        """Extract error-relevant content from command output.

        Prioritizes:
        1. Stack traces
        2. Error messages
        3. Failed test summaries

        Args:
            output: Raw command output

        Returns:
            Extracted relevant content
        """
        if not output:
            return "(no output)"

        # Look for common error patterns
        patterns = [
            # Python traceback
            r"Traceback \(most recent call last\):.*?(?=\n\n|\Z)",
            # Pytest failures
            r"FAILED.*?(?=\n\n|\Z)",
            # Ruff/lint errors
            r"error\[.*?\]:.*",
            # Type errors
            r"error:.*",
            # General errors
            r"Error:.*",
        ]

        extracted_parts: list[str] = []

        for pattern in patterns:
            matches = re.findall(pattern, output, re.DOTALL | re.IGNORECASE)
            extracted_parts.extend(matches)

        if extracted_parts:
            # Deduplicate and join
            seen: set[str] = set()
            unique_parts = []
            for part in extracted_parts:
                normalized = part.strip()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    unique_parts.append(normalized)

            return "\n".join(unique_parts[:10])  # Limit to 10 errors

        # Fallback: return last 50 lines
        lines = output.strip().split("\n")
        return "\n".join(lines[-50:])
