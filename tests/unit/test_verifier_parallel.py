"""Unit tests for parallel quality gate execution in the Verifier."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from veridical.config.schema import QualityGate
from veridical.models.result import GateResult, GateStatus
from veridical.verifier.quality_gate import Verifier


@pytest.fixture
def mock_config():
    """Fixture for a mock VeridicalConfig."""
    config = MagicMock()
    config.verifier.parallel_timeout = 10
    return config


@pytest.fixture
def verifier(mock_config):
    """Fixture for a Verifier instance with a mock config."""
    return Verifier(config=mock_config, repo_path=MagicMock())


def test_group_gates_logic(verifier):
    """Test the gate grouping logic with various combinations."""
    gates = [
        QualityGate(name="s1", command="cmd", parallel=False),
        QualityGate(name="p1", command="cmd", parallel=True),
        QualityGate(name="p2", command="cmd", parallel=True),
        QualityGate(name="s2", command="cmd", parallel=False),
        QualityGate(name="p3", command="cmd", parallel=True),
    ]
    batches = verifier._group_gates(gates)
    assert len(batches) == 4
    assert [g.name for g in batches[0]] == ["s1"]
    assert [g.name for g in batches[1]] == ["p1", "p2"]
    assert [g.name for g in batches[2]] == ["s2"]
    assert [g.name for g in batches[3]] == ["p3"]


def test_group_gates_empty(verifier):
    """Test grouping with an empty list of gates."""
    assert verifier._group_gates([]) == []


def test_group_gates_all_sequential(verifier):
    """Test grouping with only sequential gates."""
    gates = [
        QualityGate(name="s1", command="cmd", parallel=False),
        QualityGate(name="s2", command="cmd", parallel=False),
    ]
    batches = verifier._group_gates(gates)
    assert len(batches) == 2
    assert [g.name for g in batches[0]] == ["s1"]
    assert [g.name for g in batches[1]] == ["s2"]


def test_group_gates_all_parallel(verifier):
    """Test grouping with only parallel gates."""
    gates = [
        QualityGate(name="p1", command="cmd", parallel=True),
        QualityGate(name="p2", command="cmd", parallel=True),
    ]
    batches = verifier._group_gates(gates)
    assert len(batches) == 1
    assert [g.name for g in batches[0]] == ["p1", "p2"]


@pytest.mark.asyncio
async def test_run_parallel_batch_success(verifier):
    """Test a successful parallel batch run."""
    gates = [
        QualityGate(name="p1", command="cmd", parallel=True, required=True),
        QualityGate(name="p2", command="cmd", parallel=True, required=False),
    ]
    async def side_effect(gate):
        if gate.name == "p1":
            return GateResult(name="p1", status=GateStatus.PASSED, output="", duration_seconds=1.0)
        return GateResult(name="p2", status=GateStatus.PASSED, output="", duration_seconds=1.0)

    verifier._run_gate_logic = AsyncMock(side_effect=side_effect)
    results = await verifier._run_parallel_batch(gates)
    assert len(results) == 2
    assert all(r.passed for r in results)
    assert verifier._run_gate_logic.call_count == 2


@pytest.mark.asyncio
async def test_run_parallel_batch_required_failure(verifier):
    """Test fail-fast when a required gate fails in a parallel batch."""
    gates = [
        QualityGate(name="p1", command="cmd", parallel=True, required=True),
        QualityGate(name="p2", command="cmd", parallel=True, required=True),
        QualityGate(name="p3", command="cmd", parallel=True, required=True),
    ]

    completed_gates = []

    async def side_effect(gate):
        if gate.name == "p1":
            await asyncio.sleep(0.01)  # Fail fast
            completed_gates.append(gate.name)
            return GateResult(name="p1", status=GateStatus.FAILED, output="fail", duration_seconds=0.01)

        await asyncio.sleep(0.1)  # Others take longer
        completed_gates.append(gate.name)
        return GateResult(name=gate.name, status=GateStatus.PASSED, output="", duration_seconds=0.1)

    verifier._run_gate_logic = AsyncMock(side_effect=side_effect)
    results = await verifier._run_parallel_batch(gates)

    # Verify results
    assert len(results) == 3
    failed_gate = next((r for r in results if r.name == "p1"), None)
    assert failed_gate is not None
    assert not failed_gate.passed

    cancelled_gates = [r for r in results if r.status == GateStatus.CANCELLED]
    assert len(cancelled_gates) == 2

    # Assert that only the first gate's logic completed
    assert completed_gates == ["p1"]


@pytest.mark.asyncio
async def test_run_parallel_batch_optional_failure(verifier):
    """Test that an optional failure does not cancel other gates."""
    gates = [
        QualityGate(name="p1", command="cmd", parallel=True, required=False),
        QualityGate(name="p2", command="cmd", parallel=True, required=True),
    ]

    async def side_effect(gate):
        if gate.name == "p1":
            return GateResult(name="p1", status=GateStatus.FAILED, output="fail", duration_seconds=1.0)
        return GateResult(name="p2", status=GateStatus.PASSED, output="", duration_seconds=1.0)

    verifier._run_gate_logic = AsyncMock(side_effect=side_effect)
    results = await verifier._run_parallel_batch(gates)
    assert len(results) == 2
    assert verifier._run_gate_logic.call_count == 2


@pytest.mark.asyncio
async def test_run_parallel_batch_timeout(verifier):
    """Test parallel batch timeout."""
    gates = [QualityGate(name="p1", command="cmd", parallel=True)]
    verifier.config.verifier.parallel_timeout = 0.01

    async def long_running_gate(*args, **kwargs):
        await asyncio.sleep(0.1)
        return GateResult(name="p1", status=GateStatus.PASSED, output="", duration_seconds=0.1)

    verifier._run_gate_logic = AsyncMock(side_effect=long_running_gate)
    results = await verifier._run_parallel_batch(gates)
    assert len(results) == 1
    assert results[0].status == GateStatus.TIMEOUT


@pytest.mark.asyncio
async def test_run_all_orchestration(verifier):
    """Test the main `run_all` method with mixed parallel/sequential gates."""
    gates = [
        QualityGate(name="s1", command="cmd", parallel=False, required=True),
        QualityGate(name="p1", command="cmd", parallel=True, required=True),
        QualityGate(name="p2", command="cmd", parallel=True, required=False),
        QualityGate(name="s2", command="cmd", parallel=False, required=True),
    ]
    verifier.config.verifier.quality_gates = gates

    mock_results = {
        "s1": GateResult(name="s1", status=GateStatus.PASSED, duration_seconds=1.0),
        "p1": GateResult(name="p1", status=GateStatus.PASSED, duration_seconds=1.0),
        "p2": GateResult(name="p2", status=GateStatus.PASSED, duration_seconds=1.0),
        "s2": GateResult(name="s2", status=GateStatus.PASSED, duration_seconds=1.0),
    }

    async def side_effect(gate):
        return mock_results[gate.name]

    verifier._run_gate_logic = AsyncMock(side_effect=side_effect)

    result = await verifier.run_all()
    assert result.passed
    assert len(result.gates) == 4
    assert verifier._run_gate_logic.call_count == 4


@pytest.mark.asyncio
async def test_run_all_stops_after_required_failure(verifier):
    """Test that `run_all` stops after a required gate fails."""
    gates = [
        QualityGate(name="s1", command="cmd", parallel=False, required=True),
        QualityGate(name="p1", command="cmd", parallel=True, required=True),
        QualityGate(name="p2", command="cmd", parallel=True, required=True),
        QualityGate(name="s2", command="cmd", parallel=False, required=True),
    ]
    verifier.config.verifier.quality_gates = gates

    # s1 fails, so p1, p2, and s2 should not run
    verifier._run_gate_logic = AsyncMock(
        return_value=GateResult(name="s1", status=GateStatus.FAILED, duration_seconds=1.0)
    )

    result = await verifier.run_all()
    assert not result.passed
    assert len(result.gates) == 1
    assert result.gates[0].name == "s1"
    assert verifier._run_gate_logic.call_count == 1
