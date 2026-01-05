"""Log analysis using Recursive Language Model (RLM) strategy."""

import logging

from veridical.config.schema import LocalLLMConfig
from veridical.exceptions import VerificationError
from veridical.lld.client import LocalLLMClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a log analysis assistant. Your task is to analyze log output from test/build failures and identify the root cause.

Rules:
1. Quote specific line numbers or error messages from the log
2. Focus on the actual failure, not warnings or info messages
3. Be concise but precise
4. If you see a previous summary, build on it by adding new information"""

ANALYSIS_PROMPT_TEMPLATE = """Analyze this log chunk and identify any failures or errors:

{previous_summary}

Log chunk (lines {start_line}-{end_line}):
```
{chunk}
```

Provide a concise analysis focusing on:
1. What failed (test name, command, etc.)
2. The specific error message or exception
3. Line numbers where the error occurred

If this chunk contains no errors, respond with "NO ERRORS IN THIS CHUNK"."""


class LogAnalyzer:
    """Analyzes logs using recursive LLM-based summarization."""

    def __init__(self, config: LocalLLMConfig) -> None:
        """Initialize the log analyzer.

        Args:
            config: Configuration for the local LLM.
        """
        self.config = config
        self.chunk_size = config.chunk_size

    async def analyze_log(self, log_output: str, gate_name: str) -> str:
        """Analyze log output using RLM strategy.

        Implements a simplified sequential RLM pattern:
        Summary(Chunk_N) = LLM(Chunk_N + Summary(Chunk_N-1))

        Args:
            log_output: The raw log output to analyze.
            gate_name: Name of the quality gate that failed.

        Returns:
            Analyzed summary of the log.

        Raises:
            VerificationError: If analysis fails or times out.
        """
        if not log_output:
            return "(no output)"

        lines = log_output.splitlines()
        total_lines = len(lines)

        # If log is small, analyze directly
        if total_lines <= self.chunk_size:
            return await self._analyze_single_chunk(log_output, gate_name, 1, total_lines)

        # Recursive chunking
        logger.info(
            f"Analyzing {total_lines} lines in chunks of {self.chunk_size} for gate '{gate_name}'"
        )

        async with LocalLLMClient(self.config) as client:
            summary = f"Analyzing failure in gate: {gate_name}\n\n"
            chunk_count = (total_lines + self.chunk_size - 1) // self.chunk_size

            for chunk_idx in range(chunk_count):
                start_idx = chunk_idx * self.chunk_size
                end_idx = min(start_idx + self.chunk_size, total_lines)
                chunk_lines = lines[start_idx:end_idx]
                chunk_text = "\n".join(chunk_lines)

                start_line = start_idx + 1
                end_line = end_idx

                logger.debug(
                    f"Processing chunk {chunk_idx + 1}/{chunk_count} (lines {start_line}-{end_line})"
                )

                previous_summary_text = f"Previous summary:\n{summary}\n\n" if chunk_idx > 0 else ""

                prompt = ANALYSIS_PROMPT_TEMPLATE.format(
                    previous_summary=previous_summary_text,
                    start_line=start_line,
                    end_line=end_line,
                    chunk=chunk_text,
                )

                try:
                    chunk_analysis = await client.complete(
                        prompt=prompt,
                        system_prompt=SYSTEM_PROMPT,
                        temperature=0.1,
                        max_tokens=1000,
                    )

                    # Only update summary if chunk contains errors
                    if "NO ERRORS IN THIS CHUNK" not in chunk_analysis.upper():
                        summary += f"\n{chunk_analysis}"

                except VerificationError as e:
                    logger.warning(f"Failed to analyze chunk {chunk_idx + 1}: {e}")
                    # Continue with next chunk on failure
                    continue

            return summary.strip()

    async def _analyze_single_chunk(
        self, log_output: str, gate_name: str, start_line: int, end_line: int
    ) -> str:
        """Analyze a single chunk of log output.

        Args:
            log_output: The log output to analyze.
            gate_name: Name of the quality gate.
            start_line: Starting line number.
            end_line: Ending line number.

        Returns:
            Analysis summary.
        """
        async with LocalLLMClient(self.config) as client:
            prompt = ANALYSIS_PROMPT_TEMPLATE.format(
                previous_summary="",
                start_line=start_line,
                end_line=end_line,
                chunk=log_output,
            )

            try:
                analysis = await client.complete(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.1,
                    max_tokens=1000,
                )
                return f"Analysis for gate '{gate_name}':\n\n{analysis}"
            except VerificationError as e:
                logger.error(f"Failed to analyze log for gate '{gate_name}': {e}")
                raise
