# Tasks: Add Language Templates to Config Init

## 1. Configuration Defaults
- [ ] 1.1 Define `TemplateType` enum in `src/veridical/config/defaults.py` with values: `python`, `nodejs`, `elixir`, `java`
- [ ] 1.2 Create `PYTHON_CONFIG_TEMPLATE` constant (refactor existing `DEFAULT_CONFIG_TEMPLATE`)
- [ ] 1.3 Create `NODEJS_CONFIG_TEMPLATE` constant with Node.js quality gates (`npm test`, `eslint`, `prettier`)
- [ ] 1.4 Create `ELIXIR_CONFIG_TEMPLATE` constant with Elixir quality gates (`mix test`, `mix credo`, `mix format`, `mix dialyzer`)
- [ ] 1.5 Create `JAVA_CONFIG_TEMPLATE` constant with Java quality gates (Gradle/Maven variants with comments)
- [ ] 1.6 Update `get_config_template()` to accept optional `template` parameter, returning appropriate template

## 2. Configuration Loader Updates
- [ ] 2.1 Update `generate_config_template()` in `src/veridical/config/loader.py` to accept `template` parameter
- [ ] 2.2 Pass template parameter to `get_config_template()` call

## 3. CLI Command Updates
- [ ] 3.1 Add `--template` / `-t` option to `config init` command in `src/veridical/cli/config.py`
- [ ] 3.2 Add `--template` / `-t` option to `config template` command
- [ ] 3.3 Add input validation for template parameter (raise helpful error for unknown templates)

## 4. Testing
- [ ] 4.1 Add unit tests for each template generation in `tests/unit/config/`
- [ ] 4.2 Add CLI integration tests for `config init --template <name>` for all templates
- [ ] 4.3 Add CLI integration tests for `config template --template <name>`
- [ ] 4.4 Add test for default template (python) when `--template` is omitted

## 5. Documentation
- [ ] 5.1 Update README.md with template examples
- [ ] 5.2 Add inline help text explaining available templates
