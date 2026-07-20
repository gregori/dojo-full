---
name: squad-plan
description: Plan a feature through the portable squad workflow without changing application code.
---

# Squad plan

The root session owns orchestration. Initialize or resume `.workflow/runs/<run-id>/state.json`, then invoke direct specialist children for every LLM phase. Never ask a specialist child to create further children. The root may inspect state and record transitions, but never writes requirements, plans, or documentation itself.

Invoke product-manager to collect requirements, then requirements-reviewer for the structured review. Invoke tech-analyst for design or architecture decisions, and doc-writer for approved planning documents. The root incorporates their results into the run state and handoff. Do not change application code. Run `git status --short` as the deterministic planning gate.
