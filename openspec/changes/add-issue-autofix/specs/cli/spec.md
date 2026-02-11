## ADDED Requirements

### Requirement: Heal Subcommand
The CLI SHALL provide a `heal` subcommand that fetches a GitHub issue and autonomously produces a verified fix.

#### Scenario: Heal Single Issue
- **WHEN** running `veri heal --repo owner/repo --issue 42`
- **THEN** it SHALL fetch the issue from GitHub
- **AND** it SHALL triage the issue and generate a task description
- **AND** it SHALL dispatch the task to the configured worker (Jules or local)
- **AND** it SHALL run the supervisor verify loop until success or circuit break
- **AND** on success it SHALL create a GitHub PR linking back to the issue

#### Scenario: Heal with Local Worker
- **WHEN** running `veri heal --repo owner/repo --issue 42 --local`
- **THEN** it SHALL use the `LocalSupervisor` instead of the Jules-based `Supervisor`
- **AND** all other behavior SHALL remain identical

#### Scenario: Heal Dry Run
- **WHEN** running `veri heal --repo owner/repo --issue 42 --dry-run`
- **THEN** it SHALL fetch and triage the issue
- **AND** it SHALL display the generated task description and triage result
- **AND** it SHALL NOT dispatch any work or create any PR

#### Scenario: Heal Watch Mode
- **WHEN** running `veri heal --repo owner/repo --watch`
- **THEN** it SHALL poll the repository for new issues matching configured labels (default: `veridical`, `auto-fix`)
- **AND** it SHALL process each new issue sequentially through the heal pipeline
- **AND** it SHALL continue polling until interrupted (SIGINT/SIGTERM)

#### Scenario: Heal Auto-Spec
- **WHEN** running `veri heal --repo owner/repo --issue 42 --auto-spec`
- **AND** the triage classifies the issue as `category="feature"` or `complexity="high"`
- **THEN** it SHALL auto-generate an OpenSpec proposal before dispatching
- **AND** it SHALL pass the generated `tasks.md` path to the supervisor for task_completion verification

#### Scenario: Heal Missing GitHub Token
- **WHEN** running `veri heal` without `GITHUB_TOKEN` set
- **THEN** it SHALL display an error: "GITHUB_TOKEN environment variable is required for veri heal"
- **AND** it SHALL exit with code 1

#### Scenario: Heal No API Key Required for Local
- **WHEN** running `veri heal --local`
- **THEN** it SHALL NOT require the `JULES_API_KEY` environment variable
- **AND** it SHALL only require `GITHUB_TOKEN`
