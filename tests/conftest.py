"""Shared pytest fixtures for all test types."""

import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    QualityGate,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_config_yaml() -> str:
    """Sample YAML configuration for testing."""
    return """\
jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  poll_timeout: 3600
  auto_approve_plans: true

supervisor:
  max_iterations: 10
  max_consecutive_failures: 3
  stagnation_threshold: 3

verifier:
  quality_gates:
    - name: pytest
      command: pytest
    - name: ruff
      command: ruff check src/
    - name: mypy
      command: mypy src/

git:
  base_branch: main
  branch_prefix: veridical/iter-
"""


@pytest.fixture
def sample_config_path(temp_dir: Path, sample_config_yaml: str) -> Path:
    """Create a sample config file and return its path."""
    config_path = temp_dir / ".veridical.yaml"
    config_path.write_text(sample_config_yaml)
    return config_path


@pytest.fixture
def mock_git_repo(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository for testing."""
    repo_path = temp_dir / "test_repo"
    repo_path.mkdir()

    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True, check=True
    )

    # Create initial commit
    readme = repo_path / "README.md"
    readme.write_text("# Test Repository\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True, check=True
    )

    yield repo_path


@pytest.fixture
def e2e_temp_repo():
    """Create a temporary git repository for E2E testing with a remote origin and main branch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test-owner/test-repo.git"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        (repo_path / "README.md").write_text("# Test Project\n")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "branch", "-M", "main"], cwd=repo_path, check=True, capture_output=True
        )
        yield repo_path


@pytest.fixture
def e2e_config(mock_git_repo):
    """Create a test configuration for E2E tests."""
    mock_git_repo.exists()
    return VeridicalConfig(
        jules=JulesConfig(
            api_base_url="https://test.example.com",
            poll_interval=1,
            poll_timeout=60,
            auto_approve_plans=True,
        ),
        supervisor=SupervisorConfig(
            max_iterations=5,
            max_consecutive_failures=3,
            stagnation_threshold=3,
        ),
        verifier=VerifierConfig(
            quality_gates=[
                QualityGate(name="test-gate", command="exit 0", timeout=10, required=True),
            ],
        ),
        git=GitConfig(
            base_branch="main",
            branch_prefix="veridical/iter-",
            auto_cleanup=True,
            auto_create_work_branch=False,
        ),
    )
