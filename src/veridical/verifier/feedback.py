"""Error summarization for feedback generation."""

import asyncio
import logging

from veridical.config.schema import VerifierConfig
from veridical.exceptions import VerificationError
from veridical.lld.client import LocalLLMClient
from veridical.models.result import GateResult, VerificationResult
from veridical.verifier import prompts

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    """Generates error summaries for feedback to the next iteration."""

    def __init__(
        self,
        config: VerifierConfig,
        llm_client: LocalLLMClient | None = None,
    ) -> None:
        """Initialize the feedback generator.

        Args:
            config: Verifier configuration
            llm_client: Optional client for local LLM-based analysis
        """
        self.config = config
        self.llm_client = llm_client

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

        tasks = [self._summarize_gate(gate) for gate in failed_gates]
        sections = await asyncio.gather(*tasks)

        full_feedback = "\n\n".join(sections)

        # Truncate if necessary
        if len(full_feedback) > self.config.summary_max_length:
            full_feedback = full_feedback[: self.config.summary_max_length - 3] + "..."

        return full_feedback

    async def _summarize_gate(self, gate: GateResult) -> str:
        """Summarize a single gate failure."""
        lines = [f"## {gate.name} (exit code {gate.exit_code})"]
        content = gate.error_output or gate.output
        num_lines = len(content.splitlines())

        use_rlm = False
        if self.config.feedback_mode == "rlm":
            use_rlm = True
        elif self.config.feedback_mode == "auto":
            if num_lines > self.config.rlm_threshold:
                use_rlm = True

        if use_rlm and self.llm_client:
            try:
                logger.info(f"Using RLM analysis for gate '{gate.name}'")
                summary = await self._summarize_with_llm(content)
                lines.append(summary or "(RLM analysis returned no errors)")
            except Exception as e:
                logger.warning(
                    f"RLM analysis failed for gate '{gate.name}', falling back to heuristic: {e}"
                )
                lines.append(self.compress_log_output(content))
        else:
            lines.append(self.compress_log_output(content))

        return "\n".join(lines)

    async def _summarize_with_llm(self, content: str) -> str:
        """Summarize log content using the local LLM."""
        if not self.llm_client or not self.llm_client.config:
            raise VerificationError("LLM client not configured")

        chunk_size = self.llm_client.config.chunk_size
        lines = content.splitlines()
        num_lines = len(lines)

        if num_lines <= chunk_size:
            # If the content is small enough, summarize it directly
            prompt = prompts.CHUNK_SUMMARIZATION_PROMPT_TEMPLATE.format(log_content=content)
            return await self.llm_client.complete(prompt, system_prompt=prompts.SYSTEM_PROMPT)

        # Otherwise, use recursive summarization
        return await self._chunk_and_summarize(lines, chunk_size)

    async def _chunk_and_summarize(self, lines: list[str], chunk_size: int) -> str:
        """Recursively summarize log chunks."""
        if not self.llm_client:
            raise VerificationError("LLM client not configured for chunking")

        # Create tasks for summarizing each chunk
        tasks = []
        for i in range(0, len(lines), chunk_size):
            chunk_content = "\n".join(lines[i : i + chunk_size])
            prompt = prompts.CHUNK_SUMMARIZATION_PROMPT_TEMPLATE.format(log_content=chunk_content)
            tasks.append(self.llm_client.complete(prompt, system_prompt=prompts.SYSTEM_PROMPT))

        chunk_summaries = await asyncio.gather(*tasks)
        non_empty_summaries = [s for s in chunk_summaries if s]

        if not non_empty_summaries:
            return "(Recursive LLM analysis found no errors)"

        # If only one summary was produced, just return it
        if len(non_empty_summaries) == 1:
            return non_empty_summaries[0]

        # Combine summaries and perform a final summarization
        combined_summary = "\n".join(non_empty_summaries)
        final_prompt = prompts.RECURSIVE_SUMMARIZATION_PROMPT_TEMPLATE.format(
            summaries=combined_summary
        )
        return await self.llm_client.complete(final_prompt, system_prompt=prompts.SYSTEM_PROMPT)

    def identify_error_lines(self, output: str) -> list[int]:
        """Identify line numbers containing potential errors."""
        error_keywords = {"error", "fail", "exception", "fatal", "panic", "traceback"}
        lines = output.splitlines()
        error_indices = []
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in error_keywords):
                error_indices.append(i)
        return error_indices

    def compress_log_output(self, output: str, context_lines: int = 5) -> str:
        """Compress log output by retaining errors and context."""
        if not output:
            return "(no output)"

        lines = output.splitlines()
        if len(lines) <= 50:
            return output

        keep_indices = set()
        head_lines, tail_lines = 10, 10
        for i in range(min(head_lines, len(lines))):
            keep_indices.add(i)
        for i in range(max(0, len(lines) - tail_lines), len(lines)):
            keep_indices.add(i)

        error_indices = self.identify_error_lines(output)
        for idx in error_indices:
            start = max(0, idx - context_lines)
            end = min(len(lines), idx + context_lines + 1)
            for i in range(start, end):
                keep_indices.add(i)

        sorted_indices = sorted(list(keep_indices))
        result_lines = []
        last_idx = -1
        for idx in sorted_indices:
            if last_idx != -1 and idx > last_idx + 1:
                result_lines.append("...")
            result_lines.append(lines[idx])
            last_idx = idx

        return "\n".join(result_lines)
