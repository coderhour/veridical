import subprocess

import pytest

from veridical.config.schema import VeridicalConfig
from veridical.synchronizer.patch import Synchronizer


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary git repository."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    def run_git(*args):
        subprocess.run(["git", *args], cwd=repo_path, check=True, capture_output=True)

    run_git("init")
    run_git("config", "user.email", "test@example.com")
    run_git("config", "user.name", "Test User")
    run_git("config", "commit.gpgsign", "false")

    (repo_path / "README.md").write_text("Hello")
    run_git("add", "README.md")
    run_git("commit", "-m", "Initial commit")
    run_git("branch", "-M", "main")

    return repo_path


@pytest.mark.asyncio
async def test_auto_create_work_branch_flow(temp_repo):
    """Test the full flow of creating and merging to a work branch."""
    config = VeridicalConfig()
    config.git.auto_create_work_branch = True

    synchronizer = Synchronizer(config, temp_repo)

    # 1. Setup work branch
    synchronizer.setup_work_branch("Add a feature")
    assert synchronizer.starting_branch == "main"

    # Verify work branch exists and we are on it
    result = subprocess.run(
        ["git", "branch", "--show-current"], cwd=temp_repo, capture_output=True, text=True
    )
    assert result.stdout.strip() == "feat/add-a-feature"

    # 2. Create iteration branch
    iter_branch = synchronizer.create_iteration_branch(1)
    assert iter_branch == "veridical/iter-1"

    # 3. Simulate changes in iteration branch
    (temp_repo / "feature.txt").write_text("New content")

    # 4. Merge iteration branch (this should merge into the work branch)
    synchronizer.merge_to_main(iter_branch, task_description="Add a feature")

    # 5. Verify we are back on main
    result = subprocess.run(
        ["git", "branch", "--show-current"], cwd=temp_repo, capture_output=True, text=True
    )
    assert result.stdout.strip() == "main"

    # 6. Verify work branch has the changes
    subprocess.run(
        ["git", "checkout", "feat/add-a-feature"], cwd=temp_repo, check=True, capture_output=True
    )
    assert (temp_repo / "feature.txt").exists()
    assert (temp_repo / "feature.txt").read_text() == "New content"

    # 7. Verify main does NOT have the changes
    subprocess.run(["git", "checkout", "main"], cwd=temp_repo, check=True, capture_output=True)
    assert not (temp_repo / "feature.txt").exists()


@pytest.mark.asyncio
async def test_target_branch_override(temp_repo):
    """Test overriding the target branch via --target-branch."""
    config = VeridicalConfig()

    synchronizer = Synchronizer(config, temp_repo)

    # Create the target branch first
    subprocess.run(["git", "checkout", "-b", "develop"], cwd=temp_repo, check=True)
    subprocess.run(["git", "checkout", "main"], cwd=temp_repo, check=True)

    # Setup work branch with override
    synchronizer.setup_work_branch("Some task", target_branch="develop")

    # Verify we are on develop
    result = subprocess.run(
        ["git", "branch", "--show-current"], cwd=temp_repo, capture_output=True, text=True
    )
    assert result.stdout.strip() == "develop"

    # Create iteration branch
    iter_branch = synchronizer.create_iteration_branch(1)
    (temp_repo / "dev.txt").write_text("dev")

    # Merge
    synchronizer.merge_to_main(iter_branch, task_description="Dev task")

    # Back on main
    result = subprocess.run(
        ["git", "branch", "--show-current"], cwd=temp_repo, capture_output=True, text=True
    )
    assert result.stdout.strip() == "main"

    # Changes are in develop
    subprocess.run(["git", "checkout", "develop"], cwd=temp_repo, check=True)
    assert (temp_repo / "dev.txt").exists()
