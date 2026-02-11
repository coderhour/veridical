from veridical.diagnose.call_graph import CallGraphAnalyzer


def test_get_function_at_line(tmp_path):
    code = """
def foo():
    pass

def bar():
    print("hello")
    # target line
"""
    file_path = tmp_path / "test_file.py"
    file_path.write_text(code)

    analyzer = CallGraphAnalyzer(tmp_path)
    func = analyzer.get_function_at_line("test_file.py", 6)
    assert func == "bar"

    func = analyzer.get_function_at_line("test_file.py", 2)
    assert func == "foo"


def test_find_callers(tmp_path):
    # Create a structure: src/app.py calls src/utils.py:target_func
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    utils_code = """
def target_func():
    pass
"""
    (src_dir / "utils.py").write_text(utils_code)

    app_code = """
from src.utils import target_func

def main():
    target_func()
"""
    (src_dir / "app.py").write_text(app_code)

    analyzer = CallGraphAnalyzer(tmp_path)
    callers = analyzer.find_callers("target_func")

    assert len(callers) >= 1
    caller = next(c for c in callers if c["file"] == "src/app.py")
    assert caller["function"] == "main"
