---
description: Show the next safe squad action and continue it when no user decision is needed.
agent: planner
subtask: false
---


# Squad next

Read the selected active run as for `squad-resume`. First state the recorded next action in one sentence. If it is reversible and needs no product, security, deployment, or external-publication decision, invoke the specialist selected by `Next Agent` or the current phase; do not execute specialist work in the root session. Persist the result after the subagent returns. Otherwise stop and ask for that specific decision.
