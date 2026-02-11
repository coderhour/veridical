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

local:
  worker_command: ""
  worker_timeout: 600
  mode: subprocess
  error_env_var: VERIDICAL_ERROR_CONTEXT

verifier:
  quality_gates:
    - name: pytest
      command: pytest
      timeout: 300
      required: true
    - name: ruff-check
      command: ruff check src/
      fix_command: ruff check --fix src/
      timeout: 60
      required: true
    - name: ruff-format
      command: ruff format --check src/
      fix_command: ruff format src/
      timeout: 60
      required: true
    - name: mypy
      command: mypy src/
      timeout: 120
      required: true
  summary_max_length: 2000
  # Optional: Enable local LLM for advanced log analysis using RLM strategy
  # Requires a local OpenAI-compatible endpoint (e.g., Ollama, vLLM)
  # local_llm:
  #   base_url: http://localhost:11434/v1  # Ollama default endpoint
  #   model: qwen2.5:7b                     # Or llama3.2:8b, mistral:7b, etc.
  #   api_key: ollama                       # Optional, use 'ollama' for Ollama
  #   timeout: 30                           # Timeout per LLM request in seconds
  #   chunk_size: 500                       # Lines per chunk for recursive summarization

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
      fix_command: npx eslint --fix .
      timeout: 120
      required: true
    - name: prettier
      command: npx prettier --check .
      fix_command: npx prettier --write .
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
      fix_command: mix format
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
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
      fix_command: gofmt -w .
      timeout: 60
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
      fix_command: cargo fmt
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
      fix_command: npx eslint --fix .
      timeout: 120
      required: true
    - name: prettier
      command: npx prettier --check .
      fix_command: npx prettier --write .
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
      fix_command: bundle exec rubocop -A
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
      fix_command: ./vendor/bin/php-cs-fixer fix
      timeout: 120
      required: true
  summary_max_length: 2000

git:
  base_branch: main
  branch_prefix: veridical/iter-
  auto_cleanup: true
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
      fix_command: dotnet format
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
  auto_create_work_branch: true

worklog:
  enabled: true       # Enable work log persistence (default: true)
  directory: worklog  # Directory for work logs (default: "worklog")

log_level: info
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
