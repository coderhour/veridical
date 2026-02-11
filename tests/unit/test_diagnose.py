import textwrap
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from veridical.diagnose.blame import BlameCorrelator, BlameInfo
from veridical.diagnose.localizer import Localizer
from veridical.diagnose.stack_trace import StackTraceParser


def test_stack_trace_parser_python():
    parser = StackTraceParser(Path("/tmp"))
    text = """
Traceback (most recent call last):
  File "src/app.py", line 10, in main
    func()
  File "src/utils.py", line 5, in func
    raise ValueError("error")
ValueError: error
"""
    frames = parser.parse(text)
    assert len(frames) == 2
    assert frames[0].filename == "src/utils.py"
    assert frames[0].line == 5
    assert frames[1].filename == "src/app.py"
    assert frames[1].line == 10


def test_stack_trace_parser_generic():
    parser = StackTraceParser(Path("/tmp"))
    text = "src/error.py:42: some error message"
    frames = parser.parse(text)
    assert len(frames) == 1
    assert frames[0].filename == "src/error.py"
    assert frames[0].line == 42


@patch("subprocess.run")
def test_blame_correlator(mock_run):
    # Mock git blame --porcelain output
    mock_run.return_value.stdout = textwrap.dedent("""
abcdef1234567890 1 1 1
author Brad
author-mail <brad@example.com>
author-time 1700000000
author-tz -0800
committer Brad
committer-mail <brad@example.com>
committer-time 1700000000
committer-tz -0800
summary Fix bug
\\t    return True
""").strip()
    correlator = BlameCorrelator(Path("/tmp"))
    blame = correlator.get_blame("file.py", 1)

    assert blame is not None
    assert blame.author == "Brad"
    assert blame.commit_hash == "abcdef1234567890"
    assert blame.timestamp == datetime.fromtimestamp(1700000000)


def test_localizer_ranking():
    repo_path = Path("/tmp")
    localizer = Localizer(repo_path)

    # Mock stack parser and blame correlator
    localizer.stack_parser.parse = MagicMock(
        return_value=[
            MagicMock(filename="src/error.py", line=10, function="fail"),
            MagicMock(filename="src/main.py", line=5, function="run"),
        ]
    )

    localizer.blame_correlator.get_blame = MagicMock(
        side_effect=[
            BlameInfo(author="me", timestamp=datetime.now(), commit_hash="123", line_content=""),
            BlameInfo(
                author="them", timestamp=datetime(2020, 1, 1), commit_hash="456", line_content=""
            ),
        ]
    )

    report = localizer.localize("some error")
    assert len(report.entries) == 2
    # First entry should have higher confidence due to being deeper in stack AND recently changed
    assert report.entries[0].file == "src/error.py"
    assert report.entries[0].confidence > report.entries[1].confidence

    feedback = report.to_feedback_string()
    assert "Root cause likely in src/error.py:10" in feedback
