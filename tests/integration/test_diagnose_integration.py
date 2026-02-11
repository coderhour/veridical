import subprocess


def test_veri_diagnose_cli():
    # Test veri diagnose --error
    error_text = 'File "src/app.py", line 10, in main\n    raise ValueError("test")'
    result = subprocess.run(
        [".venv/bin/python", "-m", "veridical.cli.main", "diagnose", "--error", error_text],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Localization Report" in result.stdout
    assert "src/app.py:10" in result.stdout


def test_veri_diagnose_file(tmp_path):
    # Test veri diagnose --file
    log_file = tmp_path / "test.log"
    log_file.write_text('File "src/utils.py", line 5, in helper\n    crash()')

    result = subprocess.run(
        [".venv/bin/python", "-m", "veridical.cli.main", "diagnose", "--file", str(log_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Localization Report" in result.stdout
    assert "src/utils.py:5" in result.stdout
