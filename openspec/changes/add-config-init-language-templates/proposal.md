# Change: Add Language Templates to Config Init

## Why
The current `veridical config init` command generates a Python-specific configuration template with `pytest`, `ruff`, and `mypy` as quality gates. Projects using other languages (Node.js, Elixir, Java) cannot use the generated template without significant manual modification. Adding language-specific templates will improve developer experience and reduce configuration friction for polyglot teams.

## What Changes
- Add `--template` / `-t` parameter to `veridical config init` (options: `python`, `nodejs`, `elixir`, `java`)
- Create language-specific configuration templates with appropriate quality gates:
  - **Python**: `pytest`, `ruff check`, `ruff format --check`, `mypy` (current default)
  - **Node.js**: `npm test`, `eslint`, `prettier --check`
  - **Elixir**: `mix test`, `mix credo`, `mix format --check-formatted`, `mix dialyzer`
  - **Java**: `./gradlew test` or `mvn test`, `./gradlew checkstyle` or `mvn checkstyle:check`
- Default to `python` when no template is specified (backward compatible)
- Add `veridical config template --template <name>` variant that outputs template to stdout

## Impact
- Affected specs: `cli`, `config`
- Affected code: `src/veridical/cli/config.py`, `src/veridical/config/defaults.py`, `src/veridical/config/loader.py`
- Backward compatible: existing behavior preserved when `--template` is omitted
