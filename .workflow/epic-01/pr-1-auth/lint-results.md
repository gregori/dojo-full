# PR-1-auth: Lint Results

## Summary
- Backend Ruff: PASS (after auto-fix, 181 remaining warnings non-blocking)
- Frontend ESLint: 0 errors, 1 warning (non-blocking)
- Frontend Prettier: 11 files need formatting

## Fixes Applied
- bcrypt pinned to 4.2.1 in pyproject.toml (5.x incompatible with passlib)
- 49 Ruff issues auto-fixed (unused imports, unsorted imports, trailing newlines, noqa directives)
- 22 files reformatted with ruff format

## Remaining Warnings (Non-Blocking)
| Category | Count | Fix |
|----------|-------|-----|
| E501 (line too long) | ~100 | Break long lines |
| PLR2004 (magic value) | ~30 | Add status code constants |
| ARG002 (unused arg) | ~28 | Prefix with _ |
| PLC0415 (import not top-level) | 5 | Move imports to top |
| B904 (except raise) | 4 | Add from e |
| BLE001 (catch-all) | 1 | Replace with specific exception |
| G004 (f-string logging) | 1 | Use lazy % formatting |
| E712 (bool comparison) | 2 | Use not/IS pattern |

## Pass/Fail Status
| Check | Status |
|-------|--------|
| Backend Ruff Check (auto-fix) | PASS |
| Backend Ruff Format | PASS |
| Backend bcrypt pin | FIXED |
| Frontend ESLint | WARNING (1 non-blocking) |
| Frontend Prettier | NEEDS FIX (11 files) |
