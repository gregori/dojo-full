# Lint Results — PR-2 Exames Médicos + Document Foundation

- Backend Ruff check (`uv run ruff check .`): passed.
- Backend Ruff format check (`uv run ruff format --check .`): passed, 78 files already formatted.
- Frontend ESLint (`npm run lint`, `--max-warnings 0`): passed.
- Frontend TypeScript/Vite production build (`npm run build`): passed, 0 TypeScript errors.
- Frontend Prettier full check (`npm run format:check`): fails on 15 pre-existing files, all unrelated to this PR. Verified via `git stash` that the same 15 files were already flagged before this change (Windows `core.autocrlf=true` CRLF checkout vs. Prettier's expected LF; CI runs on Ubuntu with LF checkouts, so not a real CI issue). None of the 5 new/changed PR-2 files (`StudentsPage.tsx`, `DashboardPage.tsx`, `App.tsx`, `MedicalExamPage.tsx`, `MedicalExamBadge.tsx`) are in the flagged list. Tracked as pre-existing baseline formatting debt, same as PR-1.
