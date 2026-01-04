## MODIFIED Requirements

### Requirement: Template Registry

The system SHALL maintain a registry of language-specific configuration templates.

#### Scenario: Supported Templates

WHEN querying supported templates
THEN the system SHALL return `python`, `nodejs`, `elixir`, `java`, `go`, `rust`, `typescript`, `ruby`, `php`, `dotnet`

## ADDED Requirements

### Requirement: Go Template

The system SHALL provide a Go-specific configuration template.

#### Scenario: Go Template Content

WHEN generating a template for `go`
THEN it SHALL include quality gates for `go test ./...`, `go vet ./...`, `golangci-lint run`, and `gofmt -l .`
AND it SHALL use appropriate timeouts for Go tooling

### Requirement: Rust Template

The system SHALL provide a Rust-specific configuration template.

#### Scenario: Rust Template Content

WHEN generating a template for `rust`
THEN it SHALL include quality gates for `cargo test`, `cargo clippy -- -D warnings`, and `cargo fmt --check`
AND it SHALL use appropriate timeouts for Rust tooling

### Requirement: TypeScript Template

The system SHALL provide a TypeScript-specific configuration template.

#### Scenario: TypeScript Template Content

WHEN generating a template for `typescript`
THEN it SHALL include quality gates for `npm test`, `tsc --noEmit`, `eslint .`, and `prettier --check .`
AND it SHALL include type checking via TypeScript compiler

### Requirement: Ruby Template

The system SHALL provide a Ruby-specific configuration template.

#### Scenario: Ruby Template Content

WHEN generating a template for `ruby`
THEN it SHALL include quality gates for `bundle exec rspec` and `bundle exec rubocop`
AND it SHALL use appropriate timeouts for Ruby tooling

### Requirement: PHP Template

The system SHALL provide a PHP-specific configuration template.

#### Scenario: PHP Template Content

WHEN generating a template for `php`
THEN it SHALL include quality gates for `./vendor/bin/phpunit`, `./vendor/bin/phpstan analyse`, and `./vendor/bin/php-cs-fixer fix --dry-run --diff`
AND it SHALL use Composer-based tooling paths

### Requirement: .NET Template

The system SHALL provide a .NET-specific configuration template.

#### Scenario: .NET Template Content

WHEN generating a template for `dotnet`
THEN it SHALL include quality gates for `dotnet test`, `dotnet format --verify-no-changes`, and `dotnet build --warnaserror`
AND it SHALL use appropriate timeouts for .NET tooling
