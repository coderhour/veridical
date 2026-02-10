"""Assertion gate runner for declarative file and content checks."""

import json
import logging
import re
import time
from pathlib import Path

from veridical.config.schema import AssertionConfig, QualityGate
from veridical.models.result import GateResult, GateSeverity, GateStatus

logger = logging.getLogger(__name__)


class AssertionGateRunner:
    """Runs assertion gates that check file existence, content patterns, and schema validation."""

    def __init__(self, repo_path: Path) -> None:
        """Initialize the assertion gate runner.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path

    def run_gate(self, gate: QualityGate) -> GateResult:
        """Run an assertion gate.

        Args:
            gate: Quality gate configuration with assertions list

        Returns:
            Result of running the assertion gate
        """
        start_time = time.monotonic()
        assert gate.assertions is not None

        errors: list[str] = []
        for assertion in gate.assertions:
            errors.extend(self._evaluate_assertion(assertion))

        duration = time.monotonic() - start_time

        if errors:
            severity = GateSeverity.WARN if gate.warn_only else GateSeverity.FAIL
            status = GateStatus.WARNING if gate.warn_only else GateStatus.FAILED
            return GateResult(
                name=gate.name,
                status=status,
                severity=severity,
                error_output="\n".join(errors),
                duration_seconds=duration,
            )

        return GateResult(
            name=gate.name,
            status=GateStatus.PASSED,
            severity=GateSeverity.PASS,
            output="All assertions passed",
            duration_seconds=duration,
        )

    def _evaluate_assertion(self, assertion: AssertionConfig) -> list[str]:
        """Evaluate a single assertion config and return a list of error messages."""
        errors: list[str] = []

        if assertion.assert_file_exists is not None:
            errors.extend(self._check_file_exists(assertion.assert_file_exists))

        if assertion.assert_content_matches is not None:
            errors.extend(self._check_content_matches(assertion.assert_content_matches))

        if assertion.assert_json_schema is not None:
            errors.extend(self._check_json_schema(assertion.assert_json_schema))

        return errors

    def _check_file_exists(self, patterns: list[str]) -> list[str]:
        """Check that files matching glob patterns exist.

        Args:
            patterns: List of glob patterns relative to repo root

        Returns:
            List of error messages for missing files
        """
        errors: list[str] = []
        for pattern in patterns:
            matches = list(self.repo_path.glob(pattern))
            if not matches:
                errors.append(f"No files found matching pattern: {pattern}")
        return errors

    def _check_content_matches(self, config: dict[str, str]) -> list[str]:
        """Check that a file's content matches a regex pattern.

        Args:
            config: Dict with 'file' and 'pattern' keys

        Returns:
            List of error messages if content doesn't match
        """
        file_path = config.get("file")
        pattern = config.get("pattern")

        if not file_path or not pattern:
            return ["assert_content_matches requires 'file' and 'pattern' keys"]

        full_path = self.repo_path / file_path
        if not full_path.exists():
            return [f"File not found for content check: {file_path}"]

        try:
            content = full_path.read_text("utf-8")
        except Exception as e:
            return [f"Error reading {file_path}: {e}"]

        if not re.search(pattern, content):
            return [f"Content of {file_path} does not match pattern: {pattern}"]

        return []

    def _check_json_schema(self, config: dict[str, str]) -> list[str]:
        """Validate a JSON/YAML file against a JSON schema.

        Args:
            config: Dict with 'file' and 'schema' keys

        Returns:
            List of error messages if validation fails
        """
        file_path = config.get("file")
        schema_path = config.get("schema")

        if not file_path or not schema_path:
            return ["assert_json_schema requires 'file' and 'schema' keys"]

        full_file_path = self.repo_path / file_path
        full_schema_path = self.repo_path / schema_path

        if not full_file_path.exists():
            return [f"File not found for schema validation: {file_path}"]
        if not full_schema_path.exists():
            return [f"Schema file not found: {schema_path}"]

        try:
            data = self._load_json_or_yaml(full_file_path)
        except Exception as e:
            return [f"Error loading {file_path}: {e}"]

        try:
            schema = json.loads(full_schema_path.read_text("utf-8"))
        except Exception as e:
            return [f"Error loading schema {schema_path}: {e}"]

        try:
            import jsonschema

            jsonschema.validate(instance=data, schema=schema)
        except ImportError:
            return ["jsonschema package is required for assert_json_schema but is not installed"]
        except jsonschema.ValidationError as e:
            return [f"Schema validation failed for {file_path}: {e.message}"]

        return []

    @staticmethod
    def _load_json_or_yaml(path: Path) -> object:
        """Load a file as JSON, falling back to YAML.

        Args:
            path: Path to the file

        Returns:
            Parsed data

        Raises:
            ValueError: If the file cannot be parsed as JSON or YAML
        """
        content = path.read_text("utf-8")

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        try:
            import yaml

            return yaml.safe_load(content)
        except ImportError as e:
            raise ValueError(
                f"Cannot parse {path.name} as JSON and PyYAML is not installed for YAML fallback"
            ) from e
        except Exception as e:
            raise ValueError(f"Cannot parse {path.name} as JSON or YAML: {e}") from e
