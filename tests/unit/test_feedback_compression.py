import pytest

from veridical.verifier.feedback import FeedbackGenerator


@pytest.mark.unit
class TestFeedbackCompression:
    def test_compress_python_pytest(self) -> None:
        """Test compression of pytest output."""
        output = [f"Line {i}" for i in range(100)]
        output[50] = "E   AssertionError: assert 1 == 2"
        output[51] = "FAILED test_foo.py::test_bar"
        raw_output = "\n".join(output)

        gen = FeedbackGenerator()
        compressed = gen.compress_log_output(raw_output)

        assert "AssertionError" in compressed
        assert "FAILED" in compressed
        # Check head/tail
        assert "Line 0" in compressed
        assert "Line 99" in compressed
        # Check elision
        assert "..." in compressed
        assert "Line 20" not in compressed

    def test_compress_go_panic(self) -> None:
        """Test compression of Go panic output."""
        output = [f"Log {i}" for i in range(100)]
        output[50] = "panic: runtime error: invalid memory address"
        output[51] = "[signal SIGSEGV: segmentation violation code=0x1 addr=0x0 pc=0x123456]"
        raw_output = "\n".join(output)

        gen = FeedbackGenerator()
        compressed = gen.compress_log_output(raw_output)

        assert "panic:" in compressed
        assert "Log 20" not in compressed

    def test_compress_js_error(self) -> None:
        """Test compression of JS error output."""
        output = [f"Log {i}" for i in range(100)]
        output[40] = "ReferenceError: foo is not defined"
        output[41] = "    at Object.<anonymous> (/app/index.js:10:1)"
        raw_output = "\n".join(output)

        gen = FeedbackGenerator()
        compressed = gen.compress_log_output(raw_output)

        assert "ReferenceError" in compressed
        assert "Log 20" not in compressed

    def test_compress_short_output(self) -> None:
        """Test no compression for short output."""
        raw_output = "\n".join([f"Line {i}" for i in range(10)])
        gen = FeedbackGenerator()
        compressed = gen.compress_log_output(raw_output)
        assert compressed == raw_output
        assert "..." not in compressed

    def test_identify_error_lines(self) -> None:
        gen = FeedbackGenerator()
        text = """\
Normal line
Error: failed
Exception: bad
Warning: ok
FATAL ERROR
"""
        indices = gen.identify_error_lines(text)
        # Lines 1, 2, 4 contain error keywords
        assert 1 in indices
        assert 2 in indices
        assert 4 in indices
        assert 0 not in indices
