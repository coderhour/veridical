## MODIFIED Requirements

### Requirement: Config Subcommand

The CLI SHALL provide a `config` subcommand for configuration management.

#### Scenario: Config Init with Template

WHEN running `veridical config init --template <name>`
THEN it SHALL accept template names: `python`, `nodejs`, `elixir`, `java`, `go`, `rust`, `typescript`, `ruby`, `php`, `dotnet`
AND it SHALL generate the corresponding language-specific configuration file

#### Scenario: Config Template Command with Template Option

WHEN running `veridical config template --template <name>`
THEN it SHALL accept template names: `python`, `nodejs`, `elixir`, `java`, `go`, `rust`, `typescript`, `ruby`, `php`, `dotnet`
AND it SHALL output the corresponding template content to stdout
