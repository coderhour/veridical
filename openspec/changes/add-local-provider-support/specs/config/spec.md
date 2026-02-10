## ADDED Requirements

### Requirement: Local Provider Configuration
The system SHALL support a `local.provider` configuration field for selecting a named local provider preset.

#### Scenario: Provider Config Field
- **WHEN** accessing `config.local`
- **THEN** it SHALL contain `provider: str | None` (default: `None`)
- **AND** when set, the provider preset SHALL auto-configure `worker_command`, `mode`, and error delivery strategy

#### Scenario: Provider Overrides Worker Command
- **WHEN** `local.provider` is set to a valid provider name (e.g., `claude-code`)
- **AND** `local.worker_command` is empty
- **THEN** the system SHALL use the provider's default command configuration
- **AND** the provider's error delivery strategy SHALL be used instead of the default env var

#### Scenario: Worker Command Takes Precedence
- **WHEN** both `local.provider` and `local.worker_command` are set
- **THEN** `local.worker_command` SHALL take precedence over the provider's default command
- **AND** the provider's error delivery strategy SHALL still be used

#### Scenario: Unknown Provider Name
- **WHEN** `local.provider` is set to an unregistered provider name
- **THEN** the system SHALL raise a `ConfigurationError` listing available providers

### Requirement: Local Provider Registry
The system SHALL maintain a registry of named local provider presets.

#### Scenario: Built-in Providers
- **WHEN** querying available providers
- **THEN** the registry SHALL include `claude-code` and `gemini-cli`
- **AND** each provider SHALL expose its detection status (whether the tool is available on PATH)

#### Scenario: Provider Registration
- **WHEN** registering a new provider
- **THEN** the registry SHALL accept a provider name and a class implementing the `LocalProvider` protocol
- **AND** duplicate names SHALL overwrite the previous registration

#### Scenario: Provider Listing
- **WHEN** listing available providers
- **THEN** the system SHALL return provider names, descriptions, and detection status
