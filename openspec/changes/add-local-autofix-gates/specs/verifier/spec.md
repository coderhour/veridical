## ADDED Requirements

### Requirement: Local Autofix for Tool-Fixable Gates

The verifier SHALL support automatically running a fix command when a quality gate fails and has a `fix_command` configured, but only when autofix is enabled.

#### Scenario: Autofix Succeeds

- **GIVEN** a quality gate configured with `fix_command: "ruff format src/"`
- **AND** `autofix_enabled` is `true` on the Verifier
- **WHEN** the gate fails during verification
- **THEN** the verifier SHALL execute the `fix_command`
- **AND** re-run the failed gate exactly once
- **AND** if the gate now passes, the gate result SHALL be updated to passed

#### Scenario: Autofix Fails

- **GIVEN** a quality gate configured with `fix_command: "ruff format src/"`
- **AND** `autofix_enabled` is `true` on the Verifier
- **WHEN** the gate fails and the `fix_command` is executed
- **AND** the gate still fails after re-running
- **THEN** the original failure SHALL be reported to the LLM worker as normal

#### Scenario: Autofix Command Errors

- **GIVEN** a quality gate with a `fix_command` that exits with non-zero code
- **AND** `autofix_enabled` is `true` on the Verifier
- **WHEN** the fix command fails
- **THEN** the verifier SHALL log a warning with the fix command and exit code
- **AND** the gate failure SHALL proceed as if no `fix_command` was configured

#### Scenario: Autofix Disabled

- **GIVEN** a quality gate configured with `fix_command`
- **AND** `autofix_enabled` is `false` on the Verifier
- **WHEN** the gate fails
- **THEN** the verifier SHALL NOT execute the `fix_command`
- **AND** the failure SHALL be reported normally

#### Scenario: No Fix Command Configured

- **GIVEN** a quality gate without a `fix_command` field
- **WHEN** the gate fails
- **THEN** the verifier SHALL NOT attempt any autofix
- **AND** behavior SHALL be identical to the current implementation

### Requirement: Verify Fix Flag

The `veri verify` command SHALL enable autofix by default and support a `--no-fix` flag to disable it.

#### Scenario: Verify Default (Autofix Enabled)

- **WHEN** the user runs `veri verify`
- **AND** a gate with `fix_command` fails
- **THEN** the fix command SHALL be executed
- **AND** the gate SHALL be re-verified

#### Scenario: Verify With No-Fix Flag

- **WHEN** the user runs `veri verify --no-fix`
- **THEN** autofix SHALL NOT be enabled
- **AND** gates SHALL only report failures without attempting fixes
