# Project Overview

Project overview is stated in [Project Overview](./PROJECT_OVERVIEW.md).

<!-- orchestrated-squad:claude:start -->
## Orchestrated Squad

Use the installed `squad-*` workflow commands. The root session owns orchestration and `.workflow/` is canonical state. For every LLM workflow phase, the root must invoke the platform-native specialist subagent; it may only inspect state, coordinate transitions, and run deterministic gates itself. Specialists must not delegate again. Preserve instructions outside this managed block.
<!-- orchestrated-squad:claude:end -->

## Testing

Frontend and backend unit testing **MUST** be performed for all new features and bug fixes.
All acceptance criteria must be covered by automated tests. 

Layer the testing as:
- **Unit tests**: Test individual components or functions in isolation. Use Pytest for backend and Jest for frontend.
- **Integration tests**: Test interactions between components or modules. Use Pytest for backend and Jest for frontend.
- **End-to-end tests**: Test the entire application flow from the user's perspective. Use Cypress for frontend and Behave for backend.

## Frontend pre-commit gates

Before committing any change under `dojo-app/frontend/`, run these commands from that directory and confirm they all pass. They mirror `.github/workflows/ci-frontend.yml`'s `test` job exactly (that workflow file lives on `master`, so it won't show up in a `develop`-based checkout) — skipping them locally only means CI catches it later:

```bash
npm run lint
npm run format:check   # Prettier; run `npm run format` (or `npx prettier --write <files>`) to fix
npm run build           # runs tsc then vite build
npm test -- --coverage --watchAll=false --passWithNoTests
```