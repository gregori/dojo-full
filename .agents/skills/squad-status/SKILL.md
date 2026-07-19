---
name: squad-status
description: Show the current resumable squad run, its phase, gates, blockers, and next action.
argument-hint: "[run-id]"
disable-model-invocation: true
---

# Squad status

Read `.workflow/runs/$ARGUMENTS/state.json` when a run id was supplied. Otherwise inspect `.workflow/runs/` and select the most recently updated active run. Do not change files.

Report the run id, workflow, phase, status, current cycle, next action, failed or pending gates from `checks.json`, reservations, and open questions from the run handoff. If no run exists, say so and suggest `/squad-init` or `/squad-feature`.
