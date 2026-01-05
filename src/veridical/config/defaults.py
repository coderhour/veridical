"""Default configuration values and templates."""

from enum import Enum


class TemplateType(str, Enum):
    """Enum for the available configuration template types."""

    PYTHON = "python"
    NODEJS = "nodejs"
    ELIXIR = "elixir"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    TYPESCRIPT = "typescript"
    RUBY = "ruby"
    PHP = "php"
    DOTNET = "dotnet"


PYTHON_CONFIG_TEMPLATE = """\
# Veridical Configuration (Python)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""

NODEJS_CONFIG_TEMPLATE = """\
# Veridical Configuration (Node.js)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""

ELIXIR_CONFIG_TEMPLATE = """\
# Veridical Configuration (Elixir)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
    - name: mix-test
      command: mix test
      timeout: 300
      required: true
    - name: mix-credo
      command: mix credo
      timeout: 120
      required: true
    - name: mix-format
      command: mix format --check-formatted
      timeout: 120
      required: true
    - name: mix-dialyzer
      command: mix dialyzer
      timeout: 600
      required: false # Dialyzer can be slow, so it's optional by default
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""

JAVA_CONFIG_TEMPLATE = """\
# Veridical Configuration (Java with Gradle)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
    # --- Gradle ---
    - name: gradle-test
      command: ./gradlew test
      timeout: 300
      required: true
    - name: gradle-checkstyle
      command: ./gradlew checkstyleMain
      timeout: 120
      required: true
    # --- Maven ---
    # - name: maven-test
    #   command: mvn test
    #   timeout: 300
    #   required: true
    # - name: maven-checkstyle
    #   command: mvn checkstyle:check
    #   timeout: 120
    #   required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""

GO_CONFIG_TEMPLATE = """\
# Veridical Configuration (Go)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
    - name: go-test
      command: go test ./...
      timeout: 300
      required: true
    - name: go-vet
      command: go vet ./...
      timeout: 120
      required: true
    - name: golangci-lint
      command: golangci-lint run
      timeout: 300
      required: false # Optional, as it may require a separate installation
    - name: gofmt
      command: gofmt -l .
      timeout: 60
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""

RUST_CONFIG_TEMPLATE = """\
# Veridical Configuration (Rust)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
    - name: cargo-test
      command: cargo test
      timeout: 300
      required: true
    - name: cargo-clippy
      command: cargo clippy -- -D warnings
      timeout: 300
      required: true
    - name: cargo-fmt
      command: cargo fmt --check
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""

TYPESCRIPT_CONFIG_TEMPLATE = """\
# Veridical Configuration (TypeScript)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
    - name: npm-test
      command: npm test
      timeout: 300
      required: true
    - name: tsc
      command: npx tsc --noEmit
      timeout: 120
      required: true
    - name: eslint
      command: npx eslint .
      timeout: 120
      required: true
    - name: prettier
      command: npx prettier --check .
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""

RUBY_CONFIG_TEMPLATE = """\
# Veridical Configuration (Ruby)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
    - name: rspec
      command: bundle exec rspec
      timeout: 300
      required: true
    - name: rubocop
      command: bundle exec rubocop
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""

PHP_CONFIG_TEMPLATE = """\
# Veridical Configuration (PHP)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
    - name: phpunit
      command: ./vendor/bin/phpunit
      timeout: 300
      required: true
    - name: phpstan
      command: ./vendor/bin/phpstan analyse
      timeout: 120
      required: true
    - name: php-cs-fixer
      command: ./vendor/bin/php-cs-fixer fix --dry-run --diff
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""

DOTNET_CONFIG_TEMPLATE = """\
# Veridical Configuration (C#/.NET)
# See https://github.com/veridical/veridical for documentation

jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  backoff_strategy: constant  # Strategy for polling backoff: constant or exponential
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
    - name: dotnet-test
      command: dotnet test
      timeout: 300
      required: true
    - name: dotnet-format
      command: dotnet format --verify-no-changes
      timeout: 120
      required: true
    - name: dotnet-build
      command: dotnet build --warnaserror
      timeout: 300
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
"""


TEMPLATES = {
    TemplateType.PYTHON: PYTHON_CONFIG_TEMPLATE,
    TemplateType.NODEJS: NODEJS_CONFIG_TEMPLATE,
    TemplateType.ELIXIR: ELIXIR_CONFIG_TEMPLATE,
    TemplateType.JAVA: JAVA_CONFIG_TEMPLATE,
    TemplateType.GO: GO_CONFIG_TEMPLATE,
    TemplateType.RUST: RUST_CONFIG_TEMPLATE,
    TemplateType.TYPESCRIPT: TYPESCRIPT_CONFIG_TEMPLATE,
    TemplateType.RUBY: RUBY_CONFIG_TEMPLATE,
    TemplateType.PHP: PHP_CONFIG_TEMPLATE,
    TemplateType.DOTNET: DOTNET_CONFIG_TEMPLATE,
}


def get_config_template(template: TemplateType = TemplateType.PYTHON) -> str:
    """Return the specified configuration template."""
    return TEMPLATES[template]
