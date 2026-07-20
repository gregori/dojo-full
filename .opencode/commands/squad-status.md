---
description: Show the current resumable squad run, its phase, gates, blockers, and next action.
agent: planner
subtask: false
---


# Squad status

Read `.workflow/runs/$ARGUMENTS/state.json` when a run id was supplied. Otherwise inspect `.workflow/runs/` and select the most recently updated active run. Do not change files.

Report the run id, workflow, phase, status, current cycle, next action, reservations, and open questions from the run handoff. Read `checks.json` only when it exists; when it is absent, report “no gates have run yet” rather than treating it as an error. If no run exists, say so and suggest `/squad-init` or `/squad-feature`.
