import ast
from pathlib import Path


class CallGraphAnalyzer:
    """Traces from crash site to potential root causes using AST."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def get_function_at_line(self, filename: str, line: int) -> str | None:
        """Find which function contains the given line."""
        try:
            full_path = self.repo_path / filename
            if not full_path.exists():
                return None

            with full_path.open() as f:
                tree = ast.parse(f.read(), filename=str(full_path))

            for node in ast.walk(tree):
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and node.lineno <= line <= (getattr(node, "end_lineno", line)):
                    return node.name
            return None
        except Exception:
            return None

    def find_callers(self, target_func: str) -> list[dict]:
        """Find functions that call the target function across the codebase."""
        callers = []
        # Very basic implementation: search all .py files in repo
        for py_file in self.repo_path.glob("src/**/*.py"):
            try:
                with py_file.open() as f:
                    content = f.read()
                    if target_func not in content:
                        continue
                    tree = ast.parse(content, filename=str(py_file))

                relative_path = py_file.relative_to(self.repo_path)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Check if this function calls target_func
                        for subnode in ast.walk(node):
                            if (
                                isinstance(subnode, ast.Call)
                                and isinstance(subnode.func, ast.Name)
                                and subnode.func.id == target_func
                            ):
                                callers.append(
                                    {
                                        "file": str(relative_path),
                                        "function": node.name,
                                        "line": subnode.lineno,
                                    }
                                )
            except Exception:
                continue
        return callers
