---
name: squad-yolo
description: Drive a bounded squad feature through every safe phase with minimal interruptions.
argument-hint: "<feature request or run-id>"
disable-model-invocation: true
---

# Squad yolo

Treat `$ARGUMENTS` as either a feature request or an existing run id. For a new request, create a resumable `squad-feature` run. For an existing run, resume it.

Advance requirements, review, design, implementation, deterministic checks, independent review, verification, and handoff without pausing for routine confirmations. Invoke a native specialist subagent for every LLM phase; the root only coordinates and runs deterministic gates. Respect write scopes and the two-review-cycle limit. Stop only for a material product ambiguity, destructive or irreversible action, security risk, missing authority, failed gate requiring a decision, or external publication. Persist phase, evidence, next action, and open questions in `.workflow/` after each phase.
