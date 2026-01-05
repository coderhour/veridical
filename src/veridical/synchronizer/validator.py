"""Scope validation for synchronizer patches."""

import fnmatch
import logging
from dataclasses import dataclass, field

from veridical.config.schema import ScopeValidationConfig

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a scope validation check."""

    is_valid: bool = True
    violations: list[str] = field(default_factory=list)


class ScopeValidator:
    """Validator for checking if a patch is within the allowed scope."""

    def __init__(self, config: ScopeValidationConfig):
        """Initialize the validator.

        Args:
            config: Scope validation configuration
        """
        self.config = config

    def validate_patch(self, patch_data: str) -> ValidationResult:
        """Validate a patch against the configured scope.

        Args:
            patch_data: Unified diff patch content

        Returns:
            Validation result with any violations found
        """
        if not patch_data.strip():
            return ValidationResult()

        modified_files = self._parse_modified_files(patch_data)
        logger.debug(f"Validating modified files: {modified_files}")

        violations: list[str] = []
        for file_path in modified_files:
            if self._is_denied(file_path):
                violations.append(f"Modification of '{file_path}' is denied by denylist.")
            elif self.config.allowlist and not self._is_allowed(file_path):
                violations.append(f"Modification of '{file_path}' is not in allowlist.")

        if violations:
            return ValidationResult(is_valid=False, violations=violations)

        return ValidationResult()

    def _parse_modified_files(self, patch_data: str) -> set[str]:
        """Parse file paths from a unified diff.

        Args:
            patch_data: Unified diff content

        Returns:
            Set of unique file paths modified in the diff
        """
        files: set[str] = set()
        for line in patch_data.splitlines():
            if line.startswith("+++ b/"):
                files.add(line[6:])
            elif line.startswith("--- a/"):
                # Handle file deletions
                path = line[6:]
                if path != "dev/null":
                    files.add(path)
        return files

    def _is_denied(self, file_path: str) -> bool:
        """Check if a file path is explicitly denied.

        Handles glob patterns and directory prefixes (e.g., '.github/').

        Args:
            file_path: Path to the file

        Returns:
            True if the file is denied, False otherwise
        """
        if not self.config.denylist:
            return False
        for pattern in self.config.denylist:
            if pattern.endswith("/"):
                if file_path.startswith(pattern):
                    return True
            elif fnmatch.fnmatch(file_path, pattern):
                return True
        return False

    def _is_allowed(self, file_path: str) -> bool:
        """Check if a file path is explicitly allowed.

        Assumes an allowlist is configured.

        Args:
            file_path: Path to the file

        Returns:
            True if the file is allowed, False otherwise
        """
        if not self.config.allowlist:
            # If no allowlist, everything is allowed by default (denylist still applies)
            return True
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.config.allowlist)
