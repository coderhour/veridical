# Change: Add Extended Language Templates

## Why
The current template registry supports only Python, Node.js, Elixir, and Java. Many popular languages and frameworks are missing, forcing developers to manually configure quality gates from scratch. Adding templates for Go, Rust, TypeScript, Ruby, PHP, and C#/.NET will significantly improve onboarding for polyglot teams and reduce configuration friction.

## What Changes
- Add 6 new language templates to the template registry:
  - **Go**: `go test`, `go vet`, `golangci-lint run`, `gofmt -l .`
  - **Rust**: `cargo test`, `cargo clippy -- -D warnings`, `cargo fmt --check`
  - **TypeScript**: `npm test`, `tsc --noEmit`, `eslint .`, `prettier --check .`
  - **Ruby**: `bundle exec rspec`, `bundle exec rubocop`, `bundle exec rake`
  - **PHP**: `./vendor/bin/phpunit`, `./vendor/bin/phpstan analyse`, `./vendor/bin/php-cs-fixer fix --dry-run --diff`
  - **C#/.NET**: `dotnet test`, `dotnet format --verify-no-changes`, `dotnet build --warnaserror`
- Extend `TemplateType` enum with new values: `go`, `rust`, `typescript`, `ruby`, `php`, `dotnet`
- Update `--template` option help text to list all available templates
- Update spec scenarios to reflect expanded template registry

## Impact
- Affected specs: `config`, `cli`
- Affected code: `src/veridical/config/defaults.py`, `src/veridical/cli/config.py`
- Backward compatible: existing templates unchanged, new templates additive
