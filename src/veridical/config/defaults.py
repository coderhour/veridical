"""Default configuration values and templates."""

from typing import Literal

ProjectType = Literal["python", "javascript"]

TEMPLATES: dict[ProjectType, str] = {
    "python": """\
# Veridical Configuration (Python)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  poll_timeout: 3600
  auto_approve_plans: true
  max_retries: 3
  retry_delay: 1.0

supervisor:
  max_iterations: 10
  max_consecutive_failures: 3
  stagnation_threshold: 3

verifier:
  quality_gates:
    - name: pytest
      command: pytest
      timeout: 300
      required: true
    - name: ruff
      command: ruff check src/
      timeout: 60
      required: true
    - name: mypy
      command: mypy src/
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
""",
    "javascript": """\
# Veridical Configuration (JavaScript)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  poll_timeout: 3600
  auto_approve_plans: true
  max_retries: 3
  retry_delay: 1.0

supervisor:
  max_iterations: 10
  max_consecutive_failures: 3
  stagnation_threshold: 3

verifier:
  quality_gates:
    - name: jest
      command: "npm test"
      timeout: 300
      required: true
    - name: eslint
      command: "npx eslint src/"
      timeout: 60
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
""",
}


def get_config_template(project_type: ProjectType = "python") -> str:
    """Return the configuration template for a given project type."""
    return TEMPLATES[project_type]
