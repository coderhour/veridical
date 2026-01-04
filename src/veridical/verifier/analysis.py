"""Log analysis and summarization using local LLMs."""
import logging
from veridical.lld.client import LLDClient

logger = logging.getLogger(__name__)

class LogAnalyzer:
    """Analyzes log output using an RLM-based strategy."""

    def __init__(self, client: LLDClient, token_limit: int = 4096):
        """Initialize the LogAnalyzer."""
        self.client = client
        self.token_limit = token_limit

    async def analyze(self, log_content: str) -> str:
        """Analyze log content and return a summary of the root cause."""
        logger.info("Starting log analysis...")
        if not log_content.strip():
            logger.warning("Log content is empty.")
            return "Log content is empty."

        # Estimate token count (simple split is a rough proxy)
        tokens = log_content.split()
        if len(tokens) <= self.token_limit:
            logger.info("Log content is within the token limit.")
            return await self._summarize(log_content)

        logger.info("Log content exceeds token limit, starting recursive summarization.")
        return await self._recursive_summarize(log_content)

    async def _summarize(self, content: str) -> str:
        """Request a summary from the LLM."""
        prompt = f"""
Analyze the following log and identify the root cause of the failure.
Be concise and focus on the most critical error.

LOG:
{content}
"""
        return await self.client.get_completion(prompt)

    async def _recursive_summarize(self, content: str) -> str:
        """Recursively summarize content by chunking."""
        chunks = self._chunk_content(content)
        summaries = [await self._summarize(chunk) for chunk in chunks]

        if len(summaries) == 1:
            return summaries[0]

        # If summaries are still too large, recurse
        combined_summaries = "\n\n".join(summaries)
        if len(combined_summaries.split()) > self.token_limit:
            return await self._recursive_summarize(combined_summaries)

        # Final summary of summaries
        final_summary_prompt = f"""
The following are summaries of different parts of a log file.
Synthesize them into a single, coherent root cause analysis.

SUMMARIES:
{combined_summaries}
"""
        return await self.client.get_completion(final_summary_prompt)

    def _chunk_content(self, content: str) -> list[str]:
        """Chunk content into sections that fit the token limit."""
        tokens = content.split()
        chunks = []
        for i in range(0, len(tokens), self.token_limit):
            chunks.append(" ".join(tokens[i:i + self.token_limit]))
        return chunks
