## MODIFIED Requirements

### Requirement: Config Subcommand

The system SHALL provide a `config` subcommand to manage configuration.

#### Scenario: Config Show

WHEN running `veridical config show`
THEN it SHALL display the current effective configuration
AND it SHALL indicate which values came from defaults vs config file

#### Scenario: Config Init

WHEN running `veridical config init`
THEN it SHALL create a `.veridical.yaml` template in the current directory
AND it SHALL NOT overwrite an existing file without `--force`

#### Scenario: Config Init with Template

WHEN running `veridical config init --template <name>`
THEN it SHALL accept `--template` or `-t` option with values: `python`, `nodejs`, `elixir`, `java`
AND it SHALL generate a language-specific configuration template
AND the template SHALL include appropriate quality gates for the specified language

#### Scenario: Config Init Default Template

WHEN running `veridical config init` without `--template`
THEN it SHALL default to `python` template for backward compatibility

#### Scenario: Config Init Invalid Template

WHEN running `veridical config init --template unknown`
THEN it SHALL display an error message listing valid template options
AND it SHALL exit with code 1

#### Scenario: Config Template Command with Template Option

WHEN running `veridical config template --template <name>`
THEN it SHALL print the language-specific template to stdout
AND it SHALL accept the same template values as `config init`
