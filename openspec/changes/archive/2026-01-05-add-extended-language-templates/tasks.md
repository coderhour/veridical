# Tasks: Add Extended Language Templates

## 1. Configuration Defaults
- [x] 1.1 Add `GO`, `RUST`, `TYPESCRIPT`, `RUBY`, `PHP`, `DOTNET` values to `TemplateType` enum in `src/veridical/config/defaults.py`
- [x] 1.2 Create `GO_CONFIG_TEMPLATE` constant with Go quality gates (`go test ./...`, `go vet ./...`, `golangci-lint run`, `gofmt -l .`)
- [x] 1.3 Create `RUST_CONFIG_TEMPLATE` constant with Rust quality gates (`cargo test`, `cargo clippy -- -D warnings`, `cargo fmt --check`)
- [x] 1.4 Create `TYPESCRIPT_CONFIG_TEMPLATE` constant with TypeScript quality gates (`npm test`, `tsc --noEmit`, `eslint .`, `prettier --check .`)
- [x] 1.5 Create `RUBY_CONFIG_TEMPLATE` constant with Ruby quality gates (`bundle exec rspec`, `bundle exec rubocop`)
- [x] 1.6 Create `PHP_CONFIG_TEMPLATE` constant with PHP quality gates (`./vendor/bin/phpunit`, `./vendor/bin/phpstan analyse`, `./vendor/bin/php-cs-fixer fix --dry-run --diff`)
- [x] 1.7 Create `DOTNET_CONFIG_TEMPLATE` constant with .NET quality gates (`dotnet test`, `dotnet format --verify-no-changes`, `dotnet build --warnaserror`)
- [x] 1.8 Register all new templates in `TEMPLATES` dictionary

## 2. CLI Updates
- [x] 2.1 Update `--template` option help text in `src/veridical/cli/config.py` to list all 10 available templates

## 3. Testing
- [x] 3.1 Add unit tests for each new template generation in `tests/unit/config/`
- [x] 3.2 Add CLI integration tests for `config init --template <name>` for all new templates
- [x] 3.3 Add CLI integration tests for `config template --template <name>` for all new templates

## 4. Documentation
- [x] 4.1 Update README.md with examples for new templates
