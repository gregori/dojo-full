---
name: squad-resume
description: Continue the most recent active squad run from its recorded next action.
argument-hint: "[run-id]"
disable-model-invocation: true
---

# Squad resume

Find the requested run, or the most recently updated active run in `.workflow/runs/`. Read its `state.json` and `handoff.md`; read `checks.json` only if it exists. Its absence means no gate has run yet, not a broken run. Continue exactly from `next_action` and the recorded phase; do not repeat completed phases.

The invoking session is the root orchestrator. Reading state is its only direct LLM work. Resolve `Next Agent` in the handoff (or derive it from the phase) and immediately invoke that native specialist subagent with the run id, phase, next action, and relevant handoff context. Use product-manager for requirements, requirements-reviewer for requirements review, tech-analyst for design, doc-writer for approved documentation, implementer or SRE for delivery, reviewer for review, tester or test-author for testing, bug-triager for diagnosis, and finisher where that platform provides it. The root must never perform a specialist phase itself and specialists must not create another subagent.

If the run is blocked, report the blocker and request only the decision needed to unblock it. Preserve `.workflow/` as the source of truth and update the run handoff and state after every phase transition.
