---
name: squad-feature
description: Execute a bounded feature through direct Codex specialists and deterministic gates.
---

# Squad feature

The root session owns the run and creates specialists directly; `agents.max_depth = 1` prohibits delegation chains. It is an orchestrator, not a substitute for a specialist: requirements go to product-manager then requirements-reviewer, design to tech-analyst, implementation to implementer or SRE, documentation to doc-writer, review to reviewer, and test work to the platform's tester or test-author. Assign non-overlapping write scopes to writers. Keep reviewers and analysts read-only.

After reading state, invoke the native subagent for every LLM phase immediately. The root may only inspect state, coordinate results, update transitions, and run deterministic gates; it must not perform requirements, design, implementation, review, documentation, or test-authoring itself.

After implementation, invoke `node scripts/workflow-gates.mjs` for lint and test commands. Persist each gate result, request an independent reviewer only after deterministic gates, and update the handoff before finishing.
