# Agent Guidelines for this project

This document provides essential information for AI coding agents working on this application.

# Team workflow rules

All agents participate in one workflow.

## Handoff System

Agents communicate via two mechanisms:

1. **Handoff skill** — Each agent compacts context into .workflow/epic-XX/pr-X-xxx/handoff.md before transitioning to the next agent. The handoff.md contains: what was done, decisions made, open questions, and next action.

2. **Generated documentation** — Agents produce structured documentation in .workflow/ and docs/:
   - Product Manager creates PRD in docs/PRD.md + docs/epics/ + docs/stories/
   - Tech Analyst creates implementation plan in .workflow/epic-XX/pr-X-xxx/plan.md
   - Reviewer creates findings in .workflow/epic-XX/pr-X-xxx/review.md
   - Security Reviewer creates findings in .workflow/epic-XX/pr-X-xxx/security.md
   - Tester creates results in .workflow/epic-XX/pr-X-xxx/test-results.md
   - Linter creates results in .workflow/epic-XX/pr-X-xxx/lint-results.md
   - Release Notes creates notes in .workflow/epic-XX/pr-X-xxx/release-notes.md

## Workflow Order

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

## Writing Rules
- Keep entries short and structured
- Prefer bullets over long paragraphs
- Record file paths when discussing code changes
- Record exact test commands and results
- Record unresolved questions under Open Questions in handoff.md

# Shared Workflow Rules

All agents **must** use the .workflow/ directory system for state management.

**Always** use the skill ind-skills to look for relevant skills before starting work. If a relevant skill exists, use it instead of guessing.

**Always** use the handoff skill to compact context before transitioning to the next agent.

Before starting:
- Read .workflow/epic-XX/pr-X-xxx/handoff.md (or .workflow/epic-XX/epic-summary.md for epic-level work)

After finishing:
- Update handoff.md with what was done, decisions made, and next action
- Write detailed findings to your designated output file (review.md, security.md, etc.)
- Preserve existing content unless it is outdated or clearly incorrect

When working on code, dependencies, libraries, frameworks or APIs:
- Use context7 before proposing a plan
- Use context7 before implementation if external library behavior is relevant
- Use context7 during review when checking API usage or framework conventions
- Prefer context7 over guessing library behavior from memory
- Record important findings in handoff.md

**Do not** use chat history as the only source of truth.  
.workflow/ is the canonical workflow record.

# Serena Usage Rules

Serena is the semantic code assistant for this project. Prefer Serena's MCP tools over raw grep for any code navigation.

When working with this codebase:

- Use Serena's MCP tools for semantic code navigation and edits, instead of guessing.
- Prefer Serena for:
    - finding relevant files, modules and symbols
    - understanding call graphs and relationships
    - making structured, multi-file edits
    - tracing where user input flows through the codebase
- Only fall back to raw grep/edit/apply_patch when Serena tools are clearly not applicable.

Serena tools are exposed via the MCP server. Use them by name whenever code understanding or structured refactors are needed. Record important Serena findings in handoff.md.

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
Responsible for coordinating multi-PR epics:
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
- Creates docs/PRD.md (product overview)
- Creates docs/epics/epic-XX.md (per epic details)
- Creates docs/stories/story-XX-X.md (per story with acceptance criteria)
- Uses progressive disclosure for documentation structure
- Calls Requirements Reviewer for validation
- Iterates based on feedback until PRD is approved  
Runs at the epic level, before technical planning begins.

**Getting Started with Epics:** See [.opencode/epic-guide.md](.opencode/epic-guide.md)


# Project Overview

Project overview is stated in [Project Overview](./PROJECT_OVERVIEW.md).
