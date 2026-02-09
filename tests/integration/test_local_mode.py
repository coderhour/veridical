import os
import sys
from pathlib import Path
from typer.testing import CliRunner

import pytest

from veridical.cli.main import app

@pytest.fixture
def run_dir(tmp_path):
    """Create a temporary directory for running tests."""
    cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(cwd)

def test_local_loop_basic(run_dir):
    runner = CliRunner()

    # Create worker script
    worker_py = run_dir / "worker.py"
    worker_py.write_text("""
import os
import sys

target = "code.txt"
error = os.environ.get("VERIDICAL_ERROR_CONTEXT", "")

print(f"Worker running. Error context: {error}")

if not os.path.exists(target):
    with open(target, "w") as f:
        f.write("wrong")
    print("Created wrong code")
    sys.exit(0)

if "correct" in error or "grep" in error: # grep failure message usually contains command
    with open(target, "w") as f:
        f.write("correct")
    print("Fixed code")
    sys.exit(0)

print("No fix applied")
""")

    # Create veridical.yaml
    config_yaml = run_dir / ".veridical.yaml"
    config_yaml.write_text(f"""
local:
  worker_command: "{sys.executable} worker.py"
  worker_timeout: 5
  mode: subprocess

supervisor:
  max_iterations: 5

verifier:
  quality_gates:
    - name: check-correctness
      type: command
      command: grep "correct" code.txt
      required: true
      timeout: 2
""")

    # Run command
    result = runner.invoke(app, ["local", "Fix the code", "--verbose"])

    print(result.stdout)

    if result.exit_code != 0:
        print(result.exception)

    assert result.exit_code == 0
    assert "Verification passed! Task completed." in result.stdout
    assert "Iterations: 2" in result.stdout or "Iterations: 2" in result.output

    # Verify file content
    assert (run_dir / "code.txt").read_text().strip() == "correct"
