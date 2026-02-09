"""Integration test for local loop."""

import sys
from unittest.mock import AsyncMock

import pytest

from veridical.config.schema import VeridicalConfig
from veridical.local.supervisor import LocalSupervisor
from veridical.models.result import GateResult, GateStatus, VerificationResult


@pytest.fixture
def repo_path(tmp_path):
    """Create a dummy repo."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "test.py").write_text("print('hello')")
    return tmp_path


@pytest.fixture
def config(repo_path):
    """Create config."""
    config = VeridicalConfig()
    config.supervisor.max_iterations = 3
    config.local.worker_timeout = 5
    config.local.mode = "subprocess"
    config.worklog.enabled = False

    # Use a dummy worker script that fixes the "code" after 1 failure
    worker_script = repo_path / "worker.py"
    worker_script.write_text("""
import os
import sys

error = os.environ.get("VERIDICAL_ERROR_CONTEXT", "")
if "FAIL" in error:
    # Fix it
    print("Fixing...")
    sys.exit(0)
else:
    # Initial run, do nothing (verifier will fail it)
    print("Initial run")
    sys.exit(0)
""")

    config.local.worker_command = f"{sys.executable} {worker_script}"
    config.verifier.quality_gates = []  # We'll mock verifier anyway
    return config


@pytest.mark.asyncio
async def test_local_loop_integration(config, repo_path):
    """Test the full loop with a worker script."""
    supervisor = LocalSupervisor(config, repo_path)

    # Mock verifier to fail first, then pass
    # We need to fail first so that error context "FAIL" is generated
    fail_result = VerificationResult(
        passed=False,
        gates=[
            GateResult(
                name="test",
                status=GateStatus.FAILED,
                output="failed",
                duration_seconds=0.1,
            )
        ],
        duration_seconds=0.1,
    )

    pass_result = VerificationResult(
        passed=True,
        gates=[
            GateResult(
                name="test",
                status=GateStatus.PASSED,
                output="passed",
                duration_seconds=0.1,
            )
        ],
        duration_seconds=0.1,
    )

    # supervisor.verifier is already instantiated.
    supervisor.verifier.run_all = AsyncMock(side_effect=[fail_result, pass_result])
    supervisor.verifier.generate_feedback = AsyncMock(return_value="FAIL")

    result = await supervisor.run("fix bug")

    assert result.success
    assert result.iterations == 2
