## ADDED Requirements

### Requirement: Test Generation Gate Configuration
The `QualityGate` schema SHALL support the `test_generation` gate type with coverage-specific fields.

#### Scenario: Test Generation Gate Schema
- **WHEN** configuring a quality gate with `type: test_generation`
- **THEN** it SHALL accept `coverage_command: str` (default: `pytest --cov --cov-report=json`)
- **AND** it SHALL accept `coverage_threshold: int` (default: `80`, percentage of line coverage required for new functions)
- **AND** it SHALL accept `coverage_format: str` (default: `pytest-cov-json`, the format of the coverage report output)

#### Scenario: Test Generation Gate in Template
- **WHEN** generating a Python config template
- **THEN** it SHALL include a commented example of a `test_generation` gate
- **AND** the example SHALL show `coverage_command`, `coverage_threshold`, and `coverage_format` fields

#### Scenario: Test Generation Gate Validation
- **WHEN** a `test_generation` gate is configured without `coverage_command`
- **THEN** it SHALL use the default `pytest --cov --cov-report=json`
- **AND** validation SHALL pass
