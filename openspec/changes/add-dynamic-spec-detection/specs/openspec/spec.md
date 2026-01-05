# openspec Specification

## Purpose

The `openspec` module provides utilities for scanning, matching, and selecting OpenSpec changes within the project. It enables dynamic detection of which spec is being implemented.

## ADDED Requirements

### Requirement: OpenSpec Scanner

The system SHALL provide a scanner to discover OpenSpec changes with incomplete tasks.

#### Scenario: Scan for Open Specs

WHEN calling `scanner.find_open_specs(repo_path: Path)`
THEN it SHALL scan `openspec/changes/*/tasks.md` for all changes
AND it SHALL parse each tasks.md to count incomplete tasks (lines matching `- [ ]`)
AND it SHALL return a list of `OpenSpecInfo` sorted by name
AND it SHALL exclude changes with no tasks.md file

#### Scenario: OpenSpecInfo Structure

WHEN an OpenSpec change is found
THEN the returned `OpenSpecInfo` SHALL contain:
  - `name`: The change directory name (e.g., "add-configurable-backoff-strategy")
  - `path`: Full path to the change directory
  - `tasks_file`: Full path to the tasks.md file
  - `incomplete_count`: Number of incomplete tasks
  - `total_count`: Total number of tasks

#### Scenario: No Changes Directory

WHEN `openspec/changes/` does not exist
THEN it SHALL return an empty list
AND it SHALL NOT raise an error

### Requirement: Spec Matcher

The system SHALL match spec names from task descriptions.

#### Scenario: Match Explicit Spec Pattern

WHEN calling `matcher.match_spec_from_description("Implement spec add-foo", specs)`
AND "add-foo" matches a spec in the provided list
THEN it SHALL return the matching `OpenSpecInfo`

#### Scenario: Match Fuzzy Spec Name

WHEN calling `matcher.match_spec_from_description("Fix the add-foo feature", specs)`
AND "add-foo" is a substring that matches a spec name
THEN it SHALL return the matching `OpenSpecInfo`

#### Scenario: No Match Found

WHEN calling `matcher.match_spec_from_description("Fix random bug", specs)`
AND no spec name appears in the description
THEN it SHALL return None
