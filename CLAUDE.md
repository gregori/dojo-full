<!-- orchestrated-squad:claude:start -->
## Orchestrated Squad

Use the installed `squad-*` workflow commands. The root session owns orchestration and `.workflow/` is canonical state. For every LLM workflow phase, the root must invoke the platform-native specialist subagent; it may only inspect state, coordinate transitions, and run deterministic gates itself. Specialists must not delegate again. Preserve instructions outside this managed block.
<!-- orchestrated-squad:claude:end -->
