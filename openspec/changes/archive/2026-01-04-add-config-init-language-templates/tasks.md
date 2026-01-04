# Tasks: Add Language Templates to Config Init

## 1. Configuration Defaults
- [x] 1.1 Define `TemplateType` enum in `src/veridical/config/defaults.py` with values: `python`, `nodejs`, `elixir`, `java`
- [x] 1.2 Create `PYTHON_CONFIG_TEMPLATE` constant (refactor existing `DEFAULT_CONFIG_TEMPLATE`)
- [x] 1.3 Create `NODEJS_CONFIG_TEMPLATE` constant with Node.js quality gates (`npm test`, `eslint`, `prettier`)
- [x] 1.4 Create `ELIXIR_CONFIG_TEMPLATE` constant with Elixir quality gates (`mix test`, `mix credo`, `mix format`, `mix dialyzer`)
- [x] 1.5 Create `JAVA_CONFIG_TEMPLATE` constant with Java quality gates (Gradle/Maven variants with comments)
- [x] 1.6 Update `get_config_template()` to accept optional `template` parameter, returning appropriate template

## 2. Configuration Loader Updates
- [x] 2.1 Update `generate_config_template()` in `src/veridical/config/loader.py` to accept `template` parameter
- [x] 2.2 Pass template parameter to `get_config_template()` call

## 3. CLI Command Updates
- [x] 3.1 Add `--template` / `-t` option to `config init` command in `src/veridical/cli/config.py`
- [x] 3.2 Add `--template` / `-t` option to `config template` command
- [x] 3.3 Add input validation for template parameter (raise helpful error for unknown templates)

## 4. Testing
- [x] 4.1 Add unit tests for each template generation in `tests/unit/config/`
- [x] 4.2 Add CLI integration tests for `config init --template <name>` for all templates
- [x] 4.3 Add CLI integration tests for `config template --template <name>`
- [x] 4.4 Add test for default template (python) when `--template` is omitted

## 5. Documentation
- [x] 5.1 Update README.md with template examples
- [x] 5.2 Add inline help text explaining available templates
