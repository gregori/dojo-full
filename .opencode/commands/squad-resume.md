---
description: Continue the most recent active squad run from its recorded next action.
---


# Squad resume

Find the requested run, or the most recently updated active run in `.workflow/runs/`. Read its `state.json`, `handoff.md`, and gate results before acting. Continue exactly from `next_action` and the recorded phase; do not repeat completed phases.

If the run is blocked, report the blocker and request only the decision needed to unblock it. Preserve `.workflow/` as the source of truth and update the run handoff and state after every phase transition.
