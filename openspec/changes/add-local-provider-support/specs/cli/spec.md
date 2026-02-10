## ADDED Requirements

### Requirement: Local Provider CLI Option
The `veri local` command SHALL support a `--provider` / `-p` option for selecting a named local provider.

#### Scenario: Provider Flag Usage
- **WHEN** running `veri local "Fix bug" --provider claude-code`
- **THEN** the system SHALL configure the local runner using the `claude-code` provider preset
- **AND** the provider's default command, mode, and error delivery strategy SHALL be used

#### Scenario: Provider Flag Overrides Config
- **WHEN** running `veri local --provider gemini-cli`
- **AND** `local.provider` in config is set to `claude-code`
- **THEN** the CLI `--provider` flag SHALL take precedence over the config file value

#### Scenario: Provider with Worker Flag
- **WHEN** running `veri local --provider claude-code --worker "custom-command"`
- **THEN** the custom worker command SHALL take precedence over the provider's default command
- **AND** the provider's error delivery strategy SHALL still be used

#### Scenario: Unknown Provider Flag
- **WHEN** running `veri local --provider unknown-tool`
- **THEN** the system SHALL display an error listing available providers
- **AND** it SHALL exit with code 1

### Requirement: Provider List Command
The `veri local` command SHALL support a `--list-providers` flag to display available providers.

#### Scenario: List Providers Output
- **WHEN** running `veri local --list-providers`
- **THEN** the system SHALL display a table of registered providers
- **AND** each row SHALL show provider name, description, and whether the tool is detected on PATH
- **AND** it SHALL exit with code 0 without running the loop

#### Scenario: List Providers with Detection
- **WHEN** running `veri local --list-providers`
- **AND** `claude` is available on PATH but `gemini` is not
- **THEN** `claude-code` SHALL show as "detected" or with a checkmark
- **AND** `gemini-cli` SHALL show as "not found" or with a cross mark

### Requirement: Provider Auto-Detection
The `veri local` command SHALL support auto-detecting available providers when no provider or worker is specified.

#### Scenario: Auto-Detect Single Provider
- **WHEN** running `veri local "Fix bug"` without `--provider` or `--worker`
- **AND** `local.worker_command` is empty and `local.provider` is not set
- **AND** exactly one provider is detected on PATH
- **THEN** the system SHALL auto-select that provider
- **AND** it SHALL display a message indicating which provider was auto-detected

#### Scenario: Auto-Detect Multiple Providers
- **WHEN** running `veri local "Fix bug"` without `--provider` or `--worker`
- **AND** `local.worker_command` is empty and `local.provider` is not set
- **AND** multiple providers are detected on PATH
- **THEN** the system SHALL display an interactive selection menu listing detected providers
- **AND** the user SHALL select one to proceed

#### Scenario: No Provider Detected
- **WHEN** running `veri local "Fix bug"` without `--provider` or `--worker`
- **AND** `local.worker_command` is empty and `local.provider` is not set
- **AND** no providers are detected on PATH
- **THEN** the system SHALL display an error with instructions to install a supported tool or use `--worker`
- **AND** it SHALL exit with code 1
