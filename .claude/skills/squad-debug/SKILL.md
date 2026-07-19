---
name: squad-debug
description: Diagnose a bug with evidence and a resumable handoff before making changes.
argument-hint: "<bug report>"
disable-model-invocation: true
---

# Squad debug

Create or resume a bug-triage run for `$ARGUMENTS`. Reproduce or otherwise gather evidence, inspect the relevant code and history, and record hypotheses, likely cause, affected files, and a safe remediation scope in `.workflow/`.

Do not edit product code in diagnosis mode. If a fix is requested after diagnosis, hand off the recorded scope to `squad-execute`.
