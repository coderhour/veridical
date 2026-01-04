"""Log analysis using a local LLM."""

import logging
from typing import List

try:
    import tiktoken
except ImportError:
    tiktoken = None

from veridical.lld.client import LocalLLMClient

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_WINDOW = 16384  # 16k context window
CHUNK_OVERLAP = 1000


class LogAnalyzer:
    """Analyzes log files using a local LLM."""

    def __init__(self, client: LocalLLMClient):
        """Initialize the log analyzer.

        Args:
            client: The local LLM client.
        """
        self.client = client
        self._encoder = self._get_encoder()

    def _get_encoder(self):
        """Get the tiktoken encoder."""
        if tiktoken is None:
            return None
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning("Could not get tiktoken encoder: %s", e)
            return None

    def _get_token_count(self, text: str) -> int:
        """Get the number of tokens in a string."""
        if self._encoder is None:
            return len(text)
        return len(self._encoder.encode(text))

    async def analyze_log(self, log: str) -> str:
        """Analyze a log file using the RLM strategy.

        Args:
            log: The log file content.

        Returns:
            A summary of the log file.
        """
        current_text = log

        while self._get_token_count(current_text) > DEFAULT_CONTEXT_WINDOW:
            chunks = self._chunk_log(current_text)
            summaries = []
            for chunk in chunks:
                summary = await self._summarize(chunk)
                summaries.append(summary)
            current_text = "\\n".join(summaries)

        return await self._summarize(current_text)

    def _chunk_log(self, log: str) -> List[str]:
        """Chunk a log file into smaller pieces."""
        if self._encoder:
            tokens = self._encoder.encode(log)
            chunks = []
            start = 0
            while start < len(tokens):
                end = start + DEFAULT_CONTEXT_WINDOW
                chunks.append(self._encoder.decode(tokens[start:end]))
                start = end - CHUNK_OVERLAP
            return chunks

        # Fallback for when tiktoken is not available
        chunks = []
        start = 0
        while start < len(log):
            end = start + DEFAULT_CONTEXT_WINDOW
            chunks.append(log[start:end])
            start = end - CHUNK_OVERLAP
        return chunks

    async def _summarize(self, text: str) -> str:
        """Summarize a text using the local LLM."""
        prompt = f"""
        Analyze the following log and provide a concise summary of the key errors and their potential causes.
        Focus on the most critical information and ignore irrelevant details.

        Log:
        {text}
        """
        return await self.client.get_completion(prompt)
