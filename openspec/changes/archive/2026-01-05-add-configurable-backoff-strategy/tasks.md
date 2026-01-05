# Tasks: Add Configurable Backoff Strategy

## Implementation Tasks

- [x] Add `backoff_strategy` field to `JulesConfig` in `src/veridical/config/schema.py`
  - Type: `Literal["constant", "exponential"]`
  - Default: `"constant"`
  - Description: Strategy for polling interval backoff

- [x] Update `Poller.__init__` in `src/veridical/poller/monitor.py` to use configured strategy
  - Check `config.jules.backoff_strategy` value
  - Instantiate `ConstantBackoff` for `"constant"`, `ExponentialBackoff` for `"exponential"`
  - Import `ConstantBackoff` at module level

- [x] Update config templates in `src/veridical/config/defaults.py`
  - Add `backoff_strategy: constant` with comment explaining options
  - Update all language templates (python, nodejs, elixir, java, etc.)

## Testing Tasks

- [x] Add unit test for Poller with constant backoff strategy
  - Verify delays are consistent across poll attempts

- [x] Add unit test for Poller with exponential backoff strategy configured
  - Verify delays increase exponentially

- [x] Add unit test for config loading with backoff_strategy field
  - Verify both `constant` and `exponential` values parse correctly
  - Verify invalid values raise validation error

## Verification

- [x] Run `pytest tests/unit/` - all tests pass
- [x] Run `ruff check src/` - no linting errors
- [x] Run `mypy src/` - no type errors
