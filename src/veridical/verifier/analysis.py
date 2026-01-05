"""Recursive log analysis and summarization using a local LLM."""

import asyncio
from typing import cast

import tiktoken

from veridical.lld.client import LLDClient

# Default model context window size (conservative)
MODEL_CONTEXT_WINDOW = 8192
# Tokens reserved for the prompt, model instructions, and other overhead
PROMPT_RESERVATION = 2048
# Maximum tokens to allow in a single text chunk for summarization
MAX_CHUNK_TOKENS = MODEL_CONTEXT_WINDOW - PROMPT_RESERVATION

# System prompt for initial log summarization
SUMMARIZATION_PROMPT = """\
You are an expert software engineer analyzing a build or test log. Your task is to \
summarize the provided log snippet, focusing exclusively on identifying the root cause of any \
errors.

- Extract critical error messages, stack traces, and failed test names.
- Identify the specific commands that failed.
- Preserve key details like file paths, line numbers, and exception types.
- Be concise and objective. Do not offer solutions or speculate on fixes.
- If no errors are present, state that the log shows a successful operation.
"""

# System prompt for combining previous summaries
COMBINATION_PROMPT = """\
You are a senior software engineer synthesizing failure summaries from a large log file. \
You will be given a series of summaries from consecutive log chunks. Your task is to combine \
them into a single, cohesive root cause analysis.

- Identify the primary error or failure that caused the subsequent issues.
- Consolidate redundant information.
- Maintain a logical flow, starting from the initial failure.
- Be concise and focus on the most critical information that a developer would need to \
diagnose the problem.
- Do not add introductory phrases like "This is a summary...".
"""


class LogAnalyzer:
    """Analyzes log files using an RLM-based recursive summarization strategy."""

    def __init__(self, client: LLDClient) -> None:
        """Initialize the LogAnalyzer.

        Args:
            client: An initialized LLDClient instance.
        """
        self._client = client
        try:
            # Using cl100k_base as a standard tokenizer for modern models.
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback for environments where a specific tokenizer is not available.
            self._tokenizer = tiktoken.encoding_for_model("gpt-4")

    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a string.

        Args:
            text: The text to count tokens for.

        Returns:
            The number of tokens.
        """
        return len(self._tokenizer.encode(text))

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks based on token limits.

        Args:
            text: The text to split.

        Returns:
            A list of text chunks.
        """
        lines = text.splitlines()
        chunks: list[str] = []
        current_chunk_lines: list[str] = []
        current_tokens = 0

        for line in lines:
            line_tokens = self._count_tokens(line) + 1  # +1 for newline

            # If a single line is too long, it becomes its own chunk.
            # This is a fallback; ideally, logs have reasonable line lengths.
            if line_tokens > MAX_CHUNK_TOKENS:
                if current_chunk_lines:
                    chunks.append("\n".join(current_chunk_lines))
                    current_chunk_lines = []
                    current_tokens = 0
                chunks.append(line)
                continue

            if current_tokens + line_tokens > MAX_CHUNK_TOKENS and current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = [line]
                current_tokens = line_tokens
            else:
                current_chunk_lines.append(line)
                current_tokens += line_tokens

        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))

        return chunks

    async def analyze_log(self, log_content: str) -> str:
        """Perform recursive analysis of log content.

        Args:
            log_content: The full content of the log file.

        Returns:
            A concise summary of the root cause of failure.
        """
        if self._count_tokens(log_content) <= MAX_CHUNK_TOKENS:
            # If the log fits, summarize it directly.
            return await self._client.summarize_text(log_content, SUMMARIZATION_PROMPT)

        # Chunk the text and summarize each chunk in parallel.
        chunks = self._chunk_text(log_content)
        summarization_tasks = [
            self._client.summarize_text(chunk, SUMMARIZATION_PROMPT) for chunk in chunks
        ]
        summaries = await asyncio.gather(*summarization_tasks)

        # Filter out any empty summaries that may have resulted from errors.
        valid_summaries = cast(list[str], [s for s in summaries if s])

        # Recursively combine the summaries.
        return await self._combine_summaries(valid_summaries)

    async def _combine_summaries(self, summaries: list[str]) -> str:
        """Recursively combine a list of summaries.

        Args:
            summaries: A list of summaries to combine.

        Returns:
            A single, combined summary.
        """
        combined_text = "\n\n---\n\n".join(summaries)

        if self._count_tokens(combined_text) <= MAX_CHUNK_TOKENS:
            # If the combined text fits, produce the final summary.
            return await self._client.summarize_text(combined_text, COMBINATION_PROMPT)

        # If it's still too large, chunk the combined summaries and recurse.
        # This handles extremely large logs where even summaries are too long.
        chunks = self._chunk_text(combined_text)
        combination_tasks = [
            self._client.summarize_text(chunk, COMBINATION_PROMPT) for chunk in chunks
        ]
        new_summaries = await asyncio.gather(*combination_tasks)
        valid_new_summaries = cast(list[str], [s for s in new_summaries if s])

        return await self._combine_summaries(valid_new_summaries)
