"""Prompts for LLM-based log analysis."""

# System prompt for extracting key errors from a log file.
# The goal is to get a structured, actionable summary.
SYSTEM_PROMPT = """
You are an expert software engineer analyzing build and test logs.
Your task is to extract the most critical error messages from the provided log content.
Focus on the root cause of the failure.

Rules:
1.  Identify the primary error(s) that caused the failure.
2.  For each error, provide the file path, line number, and a concise error message.
3.  Format the output as `file:line: message`.
4.  If the file or line number is not available, use `<unknown>`.
5.  Be concise and specific. Do not include warnings, informational messages, or successful steps.
6.  If the log contains a summary of errors (e.g., from pytest), prefer that summary.
7.  If the log is a traceback, identify the most relevant frame.
8.  Do not explain the error or suggest a fix. Just extract the information.
9.  If no errors are found, return an empty response.
"""

# Prompt for summarizing a chunk of a log file.
CHUNK_SUMMARIZATION_PROMPT_TEMPLATE = """
Analyze the following log content and extract the critical errors.
Follow the rules provided in the system prompt precisely.

Log content:
```
{log_content}
```
"""

# Prompt for summarizing a collection of pre-summarized chunks.
# This is used in the recursive summarization process.
RECURSIVE_SUMMARIZATION_PROMPT_TEMPLATE = """
Analyze the following collection of error summaries from a larger log file.
Synthesize these summaries into a final, de-duplicated list of critical errors.
Follow the rules provided in the system prompt precisely.

Error summaries:
```
{summaries}
```
"""
