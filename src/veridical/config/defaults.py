"""Default configuration values and templates."""

from typing import Literal

TemplateName = Literal["python", "nodejs", "elixir", "java"]

_SHARED_CONFIG_HEAD = """\
# Veridical Configuration
# See https://github.com/veridical/veridical for documentation

# Jules API Configuration
jules:
  # Base URL for the Jules API
  api_base_url: https://jules.googleapis.com/v1alpha

  # Polling interval in seconds when waiting for session completion
  poll_interval: 30

  # Maximum time (in seconds) to wait for a session to complete
  poll_timeout: 3600

  # Automatically approve plans without human intervention
  auto_approve_plans: true

  # Maximum retry attempts for failed API calls
  max_retries: 3

  # Base delay between retries (exponential backoff applied)
  retry_delay: 1.0

# Supervisor Loop Configuration
supervisor:
  # Maximum number of fix iterations before giving up
  max_iterations: 10

  # Number of consecutive failures before circuit breaker trips
  max_consecutive_failures: 3

  # Number of identical diffs before detecting stagnation
  stagnation_threshold: 3
"""

_SHARED_CONFIG_TAIL = """\
# Git Configuration
git:
  # Base branch to create iteration branches from
  base_branch: main

  # Prefix for iteration branch names
  branch_prefix: veridical/iter-

  # Automatically delete iteration branches after successful merge
  auto_cleanup: true
"""

CONFIG_TEMPLATES: dict[TemplateName, str] = {
    "python": f"""\
{_SHARED_CONFIG_HEAD}
# Verifier Configuration
verifier:
  # Quality gates to run for verification
  quality_gates:
    - name: pytest
      command: pytest
      timeout: 300
      required: true

    - name: ruff-check
      command: ruff check src/
      timeout: 60
      required: true

    - name: ruff-format
      command: ruff format --check src/
      timeout: 60
      required: true

    - name: mypy
      command: mypy src/
      timeout: 120
      required: true

  # Maximum length of error summaries sent back to Jules
  summary_max_length: 2000
{_SHARED_CONFIG_TAIL}
""",
    "nodejs": f"""\
{_SHARED_CONFIG_HEAD}
# Verifier Configuration
verifier:
  # Quality gates to run for verification
  quality_gates:
    - name: npm-test
      command: npm test
      timeout: 300
      required: true

    - name: eslint
      command: npx eslint .
      timeout: 120
      required: true

    - name: prettier
      command: npx prettier --check .
      timeout: 120
      required: true

  # Maximum length of error summaries sent back to Jules
  summary_max_length: 2000
{_SHARED_CONFIG_TAIL}
""",
    "elixir": f"""\
{_SHARED_CONFIG_HEAD}
# Verifier Configuration
verifier:
  # Quality gates to run for verification
  quality_gates:
    - name: mix-test
      command: mix test
      timeout: 300
      required: true

    - name: credo
      command: mix credo --strict
      timeout: 120
      required: true

    - name: mix-format
      command: mix format --check-formatted
      timeout: 120
      required: true

    - name: dialyzer
      command: mix dialyzer
      timeout: 300
      required: false  # Dialyzer can be slow, often not required

  # Maximum length of error summaries sent back to Jules
  summary_max_length: 2000
{_SHARED_CONFIG_TAIL}
""",
    "java": f"""\
{_SHARED_CONFIG_HEAD}
# Verifier Configuration
verifier:
  # Quality gates to run for verification
  quality_gates:
    # --- Gradle (recommended) ---
    - name: gradle-test
      command: ./gradlew test
      timeout: 300
      required: true

    - name: gradle-check
      command: ./gradlew check  # Runs checkstyle, pmd, etc.
      timeout: 120
      required: true

    # --- Maven ---
    # - name: mvn-test
    #   command: mvn test
    #   timeout: 300
    #   required: true
    #
    # - name: mvn-checkstyle
    #   command: mvn checkstyle:check
    #   timeout: 120
    #   required: true

  # Maximum length of error summaries sent back to Jules
  summary_max_length: 2000
{_SHARED_CONFIG_TAIL}
""",
}


def get_config_template(name: TemplateName = "python") -> str:
    """Return the named configuration template.

    Args:
        name: The name of the template to return.

    Returns:
        The configuration template as a string.

    Raises:
        KeyError: if the template name is not found.
    """
    return CONFIG_TEMPLATES[name]
