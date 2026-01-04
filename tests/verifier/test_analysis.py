import pytest
from unittest.mock import AsyncMock, MagicMock
from veridical.verifier.analysis import LogAnalyzer

@pytest.fixture
def mock_llm_client():
    """Fixture for a mocked LLDClient."""
    client = MagicMock()
    client.get_completion = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_analyze_within_token_limit(mock_llm_client):
    """Test analysis of log content within the token limit."""
    # Arrange
    log_content = "An error occurred."
    expected_summary = "Root cause: An error."
    mock_llm_client.get_completion.return_value = expected_summary

    analyzer = LogAnalyzer(client=mock_llm_client)

    # Act
    summary = await analyzer.analyze(log_content)

    # Assert
    assert summary == expected_summary
    mock_llm_client.get_completion.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_exceeds_token_limit(mock_llm_client):
    """Test analysis of log content that exceeds the token limit."""
    # Arrange
    log_content = "word " * 5000
    chunk1_summary = "Chunk 1 summary."
    chunk2_summary = "Chunk 2 summary."
    final_summary = "Final synthesized summary."

    # Mock the return values for each call
    mock_llm_client.get_completion.side_effect = [
        chunk1_summary,
        chunk2_summary,
        final_summary,
    ]

    analyzer = LogAnalyzer(client=mock_llm_client, token_limit=4096)

    # Act
    summary = await analyzer.analyze(log_content)

    # Assert
    assert summary == final_summary
    assert mock_llm_client.get_completion.call_count == 3

@pytest.mark.asyncio
async def test_analyze_empty_log(mock_llm_client):
    """Test analysis of empty log content."""
    # Arrange
    log_content = " "
    analyzer = LogAnalyzer(mock_llm_client, "test-model")

    # Act
    summary = await analyzer.analyze(log_content)

    # Assert
    assert summary == "Log content is empty."
    mock_llm_client.get_completion.assert_not_called()
