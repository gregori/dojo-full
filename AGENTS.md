# Agent Guidelines for this project

This document provides essential information for AI coding agents working on this application.

# Team workflow rules

All agents participate in one workflow.

Shared handoff file:
- Read `WORKFLOW_STATE.md` before starting work
- Update `WORKFLOW_STATE.md` before finishing work
- Never overwrite another section unnecessarily
- Preserve decisions, assumptions, blockers and next steps

Workflow order:

### Per PR
1. Planner  
2. Requirements Reviewer  
3. Tech Analyst (PR-level)  
4. Architecture Reviewer  
5. Implementer  
6. Reviewer  
7. Security Reviewer  
8. Tester  
9. Doc Writer (incremental)  
10. Migration Planner (incremental)  
11. Linter  
12. Release Notes (incremental)  
13. Commit-message  

### Per Epic
- Epic Coordinator calls Product Manager to refine epic requirements into PRD
- Product Manager creates hierarchical PRD (docs/PRD.md + epics/ + stories/)
- Product Manager hands off to Requirements Reviewer for validation
- After PRD approved, Epic Coordinator divides into PRs and calls Planner for each
- Epic Coordinator consolidates:
  - architecture
  - documentation
  - migrations
  - release notes
- Epic Coordinator detects conflicts between PRs
- Epic Coordinator hands off to Release Notes for final epic-level release


Writing rules:
- Keep entries short and structured
- Prefer bullets over long paragraphs
- Record file paths when discussing code changes
- Record exact test commands and results
- Record unresolved questions under "Open Questions"

# Shared workflow rules

All agents **must** use `WORKFLOW_STATE.md` as the shared handoff file.

**Always** use the skill `find-skills` to look for relevant skills before starting work. If a relevant skill exists, use it instead of guessing.

Before starting:
- Read `WORKFLOW_STATE.md`

After finishing:
- Update only the sections relevant to your role
- Preserve existing content unless it is outdated or clearly incorrect
- Add a short handoff note for the next agent

When working on code, dependencies, libraries, frameworks or APIs:
- Use context7 before proposing a plan
- Use context7 before implementation if external library behavior is relevant
- Use context7 during review when checking API usage or framework conventions
- Prefer context7 over guessing library behavior from memory
- Record important findings in `WORKFLOW_STATE.md`

**Do not** use chat history as the only source of truth.  
`WORKFLOW_STATE.md` is the canonical workflow record.

# Serena usage rules

Serena is the semantic code assistant for this project. Prefer Serena's MCP tools over raw grep for any code navigation.

When working with this codebase:

- Use Serena's MCP tools for semantic code navigation and edits, instead of guessing.
- Prefer Serena for:
    - finding relevant files, modules and symbols
    - understanding call graphs and relationships
    - making structured, multi-file edits
    - tracing where user input flows through the codebase
- Only fall back to raw grep/edit/apply_patch when Serena tools are clearly not applicable.

Serena tools are exposed via the MCP server. Use them by name whenever code understanding or structured refactors are needed. Record important Serena findings in `WORKFLOW_STATE.md`.

# Additional Agents

## Doc Writer
Responsible for updating documentation after implementation and review:
- API docs
- Domain models
- Business workflows
- Frontend components
- Infrastructure changes  
Runs after Tester and before Commit-message.

## Release Notes
Generates semantic release notes and updates CHANGELOG.md:
- Categorizes changes (features, fixes, docs, infra, tests)
- Produces user-facing release notes  
Runs before Commit-message.

## Migration Planner
Triggered only when schema changes are detected:
- Analyzes ORM models and DB structure
- Produces forward and backward migration plans
- Identifies risks and mitigation strategies  
Runs after Reviewer/Security Reviewer and before Linter.

## Epic Coordinator
Responsible for coordinating multi‑PR epics:
- Calls Product Manager to refine epic requirements into PRD
- Consolidates architecture decisions across PRs
- Aggregates documentation updates
- Merges migration plans into a safe ordered chain
- Aggregates release notes
- Detects conflicts between PRs
- Maps and validates PR dependencies

Runs at the epic level, not per PR.

## Product Manager
Responsible for refining epic and user story requirements into a hierarchical PRD:
- Creates `docs/PRD.md` (product overview)
- Creates `docs/epics/epic-XX.md` (per epic details)
- Creates `docs/stories/story-XX-X.md` (per story with acceptance criteria)
- Uses progressive disclosure for documentation structure
- Calls Requirements Reviewer for validation
- Iterates based on feedback until PRD is approved  
Runs at the epic level, before technical planning begins.

**Getting Started with Epics:** See [.opencode/epic-guide.md](.opencode/epic-guide.md)


# Project Overview

Project overview is stated in [Project Overview](./PROJECT_OVERVIEW.md).
