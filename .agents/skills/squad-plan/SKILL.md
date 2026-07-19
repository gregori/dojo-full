---
name: squad-plan
description: Plan a feature through the portable squad workflow without changing application code.
---

# Squad plan

The root session owns orchestration. Initialize or resume `.workflow/runs/<run-id>/state.json`, then create direct specialist children only when needed. Never ask a planner child to create further children.

Collect requirements, obtain one structured requirements review, and request a direct tech-analysis child only for ambiguous architecture. Write the approved plan and handoff. Do not change application code. Run `git status --short` as the deterministic planning gate.
