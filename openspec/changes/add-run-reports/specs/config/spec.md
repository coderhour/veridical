## ADDED Requirements

### Requirement: Report Configuration
The system SHALL support a `report` configuration section for report generation settings.

#### Scenario: Report Config Section
- **WHEN** accessing `config.report`
- **THEN** it SHALL contain `default_format: str` (default: `terminal`, options: `terminal`, `json`, `html`)
- **AND** it SHALL contain `html_template: str | None` (default: `None`, path to custom Jinja2 template)

#### Scenario: Report Config Defaults
- **WHEN** no `report` section is specified in `.veridical.yaml`
- **THEN** the system SHALL use default values
- **AND** reports SHALL render in terminal format by default
