"""Error summarization for feedback generation."""

import asyncio
import logging

from veridical.config.schema import LocalLLMConfig
from veridical.models.result import GateResult, VerificationResult
from veridical.verifier.analysis import LogAnalyzer

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    """Generates error summaries for feedback to the next iteration."""

    def __init__(
        self, max_length: int = 2000, local_llm_config: LocalLLMConfig | None = None
    ) -> None:
        """Initialize the feedback generator.

        Args:
            max_length: Maximum length of generated feedback
            local_llm_config: Optional configuration for local LLM-based analysis
        """
        self.max_length = max_length
        self.local_llm_config = local_llm_config
        self.log_analyzer = LogAnalyzer(local_llm_config) if local_llm_config else None

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

        # Use RLM-based analysis if available, otherwise fall back to heuristic
        if self.log_analyzer:
            try:
                logger.info(f"Using RLM analysis for gate '{gate.name}'")
                analyzed = asyncio.run(self.log_analyzer.analyze_log(content, gate.name))
                lines.append(analyzed)
            except Exception as e:
                logger.warning(
                    f"RLM analysis failed for gate '{gate.name}', falling back to heuristic: {e}"
                )
                compressed = self.compress_log_output(content)
                lines.append(compressed)
        else:
            # Compress output using heuristic
            compressed = self.compress_log_output(content)
            lines.append(compressed)

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
