---
name: squad-next
description: Show the next safe squad action and continue it when no user decision is needed.
argument-hint: "[run-id]"
disable-model-invocation: true
---

# Squad next

Read the selected active run as for `squad-resume`. First state the recorded next action in one sentence. If it is reversible and needs no product, security, deployment, or external-publication decision, execute it and persist the result. Otherwise stop and ask for that specific decision.
