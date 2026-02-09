import os
import subprocess
import sys
from pathlib import Path
import textwrap

import pytest
import yaml

from veridical.config.schema import VeridicalConfig


@pytest.mark.integration
@pytest.mark.asyncio
async def test_local_mode_integration(tmp_path):
    # 1. Setup files
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / "src").mkdir()
    (project_dir / "tests").mkdir()

    # Create broken code
    (project_dir / "src/broken.py").write_text(textwrap.dedent("""
        def foo():
            return 1 + "a"
    """))

    # Create test
    (project_dir / "tests/test_broken.py").write_text(textwrap.dedent("""
        import sys
        import os
        sys.path.append(os.path.join(os.getcwd(), "src"))
        from broken import foo

        def test_foo():
            assert foo() == 2
    """))

    # Create worker script
    worker_script = project_dir / "worker.py"
    worker_script.write_text(textwrap.dedent("""
        import os
        import sys

        print("Worker running...")
        error_context = os.environ.get("VERIDICAL_ERROR_CONTEXT")

        if error_context:
            print(f"Received error context: {error_context[:50]}...")
            # Fix the bug
            with open("src/broken.py", "w") as f:
                f.write("def foo():\\n    return 1 + 1\\n")
            print("Fixed the bug!")
        else:
            print("No error context, doing nothing.")
    """))

    # Create config
    config_path = project_dir / "veridical.yaml"
    config = {
        "local": {
            "worker_command": f"{sys.executable} worker.py",
            "worker_timeout": 10,
            "mode": "subprocess",
            "error_env_var": "VERIDICAL_ERROR_CONTEXT",
        },
        "supervisor": {
            "max_iterations": 3,
        },
        "verifier": {
            "quality_gates": [
                {
                    "name": "pytest",
                    "command": f"{sys.executable} -m pytest tests/",
                    "required": True,
                }
            ]
        },
        "worklog": {
            "enabled": False
        }
    }
    config_path.write_text(yaml.dump(config))

    # 2. Run Veridical Local
    # We run it via subprocess to test the CLI fully
    cmd = [
        sys.executable, "-m", "veridical", "local",
        "Fix the broken code",
        "--config", str(config_path),
        "--verbose"
    ]

    # We need to run this inside the project dir
    # Ensure src is in PYTHONPATH so veridical can be imported
    src_path = os.path.join(os.getcwd(), "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_path}:{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        cmd,
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=env
    )

    # 3. Verify output
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    assert result.returncode == 0
    assert "SUCCESS" in result.stdout
    assert "Iterations: 2" in result.stdout # Should take 2 iterations (1 fail, 1 pass)
    assert "Verification passed!" in result.stderr or "Verification passed!" in result.stdout

    # Verify file content changed
    content = (project_dir / "src/broken.py").read_text()
    assert "return 1 + 1" in content
