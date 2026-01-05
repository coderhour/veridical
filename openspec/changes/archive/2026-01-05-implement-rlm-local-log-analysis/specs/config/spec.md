## MODIFIED Requirements
### Requirement: Configuration Schema
The system SHALL define a `VeridicalConfig` Pydantic model.

#### Scenario: Config Structure
- **WHEN** loading configuration
- **THEN** `VeridicalConfig` SHALL contain the following sections:
  - `jules`: Jules API configuration
  - `supervisor`: Loop control settings
  - `verifier`: Quality gate configuration
  - `git`: Git operation settings
  - `local_llm`: Local LLM settings (Optional)

#### Scenario: Rules Config Section
- **WHEN** accessing `config.jules`
- **THEN** it SHALL contain `api_base_url: str` (default: `https://jules.googleapis.com/v1alpha`)
- **AND** it SHALL contain `poll_interval: int` (default: 30)
- **AND** it SHALL contain `poll_timeout: int` (default: 3600)
- **AND** it SHALL contain `auto_approve_plans: bool` (default: True)

#### Scenario: Supervisor Config Section
- **WHEN** accessing `config.supervisor`
- **THEN** it SHALL contain `max_iterations: int` (default: 10)
- **AND** it SHALL contain `max_consecutive_failures: int` (default: 3)
- **AND** it SHALL contain `stagnation_threshold: int` (default: 3)

#### Scenario: Verifier Config Section
- **WHEN** accessing `config.verifier`
- **THEN** it SHALL contain `quality_gates: list[QualityGate]`
- **AND** each `QualityGate` SHALL have `name: str` and `command: str`
- **AND** it SHALL contain `feedback_mode: str` (default: `auto`)

#### Scenario: Git Config Section
- **WHEN** accessing `config.git`
- **THEN** it SHALL contain `base_branch: str` (default: `main`)
- **AND** it SHALL contain `branch_prefix: str` (default: `veridical/iter-`)

## ADDED Requirements
### Requirement: Local LLM Configuration
The system SHALL support configuring a local LLM endpoint.

#### Scenario: Local LLM Section
- **WHEN** accessing `config.local_llm`
- **THEN** it SHALL support `base_url: str` (default: `http://localhost:11434/v1`)
- **AND** it SHALL support `model: str` (default: `qwen2.5-coder`)
- **AND** it SHALL support `timeout: int` (default: 60)
