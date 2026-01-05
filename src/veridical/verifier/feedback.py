"""Error summarization for feedback generation."""

import asyncio

from veridical.models.result import GateResult, VerificationResult
from veridical.verifier.analysis import LogAnalyzer


class FeedbackGenerator:
    """Generates error summaries for feedback to the next iteration."""

    def __init__(self, max_length: int = 2000, analyzer: LogAnalyzer | None = None) -> None:
        """Initialize the feedback generator.

        Args:
            max_length: Maximum length of generated feedback
            analyzer: Optional LogAnalyzer for LLM-based summarization.
        """
        self.max_length = max_length
        self._analyzer = analyzer

    async def generate_feedback(self, result: VerificationResult) -> str:
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

        summarization_tasks = [self._summarize_gate(gate) for gate in failed_gates]
        sections = await asyncio.gather(*summarization_tasks)

        full_feedback = "\n\n".join(sections)

        # Truncate if necessary
        if len(full_feedback) > self.max_length:
            full_feedback = full_feedback[: self.max_length - 3] + "..."

        return full_feedback

    async def _summarize_gate(self, gate: GateResult) -> str:
        """Summarize a single gate failure.

        Args:
            gate: Failed gate result

        Returns:
            Summary string
        """
        lines = [f"## {gate.name} (exit code {gate.exit_code})"]

        # Prioritize error output
        content = gate.error_output or gate.output

        # Get summary, using analyzer if available
        summary: str
        if self._analyzer:
            summary = await self._analyzer.analyze_log(content)
        else:
            summary = self.compress_log_output(content)

        lines.append(summary)

        return "\n".join(lines)

    def identify_error_lines(self, output: str) -> list[int]:
        """Identify line numbers containing potential errors.

        Args:
            output: multi-line string

        Returns:
            List of 0-based line indices
        """
        error_keywords = {"error", "fail", "exception", "fatal", "panic", "traceback"}
        lines = output.splitlines()
        error_indices = []
        for i, line in enumerate(lines):
            # Case insensitive check
            if any(kw in line.lower() for kw in error_keywords):
                error_indices.append(i)
        return error_indices

    def compress_log_output(self, output: str, context_lines: int = 5) -> str:
        """Compress log output by retaining errors and context.

        Strategy:
        1. Find all lines with keywords.
        2. Keep N lines before/after each matching line.
        3. Keep first N lines (head) and last N lines (tail).
        4. Join segments with "..."

        Args:
            output: Raw log output
            context_lines: Number of context lines to keep around errors

        Returns:
            Compressed output
        """
        if not output:
            return "(no output)"

        lines = output.splitlines()
        total_lines = len(lines)

        # If short enough, return all
        if total_lines <= 50:
            return output

        keep_indices = set()

        # Always keep head and tail
        head_lines = 10
        tail_lines = 10

        for i in range(min(head_lines, total_lines)):
            keep_indices.add(i)
        for i in range(max(0, total_lines - tail_lines), total_lines):
            keep_indices.add(i)

        # Find errors
        error_indices = self.identify_error_lines(output)

        # Add context around errors
        for idx in error_indices:
            start = max(0, idx - context_lines)
            end = min(total_lines, idx + context_lines + 1)
            for i in range(start, end):
                keep_indices.add(i)

        # Construct output
        sorted_indices = sorted(keep_indices)
        result = []
        last_idx = -1

        for idx in sorted_indices:
            if last_idx != -1 and idx > last_idx + 1:
                result.append("...")
            result.append(lines[idx])
            last_idx = idx

        return "\n".join(result)
