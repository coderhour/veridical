import pytest
from unittest.mock import patch, MagicMock

from veridical.cli.run import run

@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_id_long_option_accepted():
    with patch("veridical.cli.run.Supervisor"), \
         patch("veridical.cli.run.select_spec", return_value=None), \
         patch("veridical.cli.run.check_spec_status", return_value=MagicMock(needs_attention=False)):
        await run(task="Test task", session_id="test-session-123", dry_run=True)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_id_short_option_accepted():
    with patch("veridical.cli.run.Supervisor"), \
         patch("veridical.cli.run.select_spec", return_value=None), \
         patch("veridical.cli.run.check_spec_status", return_value=MagicMock(needs_attention=False)):
        await run(task="Test task", session_id="test-session-123", dry_run=True)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_without_session_id_works():
    with patch("veridical.cli.run.Supervisor"), \
         patch("veridical.cli.run.select_spec", return_value=None), \
         patch("veridical.cli.run.check_spec_status", return_value=MagicMock(needs_attention=False)):
        await run(task="Test task", dry_run=True)
