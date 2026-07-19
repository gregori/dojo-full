# Test Results — PR-1 Pre-Checkin

## Passed

- `cd dojo-app/frontend; npm run lint`
- `cd dojo-app/frontend; npm run build`
- `git diff --check`
- `cd dojo-app/backend; .venv\\Scripts\\python.exe -m pytest tests/unit/test_pre_checkin_service.py tests/unit/test_api_precheckins.py -q` — 8 passed
- `cd dojo-app/backend; .venv\\Scripts\\ruff.exe check app tests`
- `cd dojo-app/backend; .venv\\Scripts\\ruff.exe format --check app tests`

## Migration follow-up

- A migration smoke test remains outstanding. `alembic/versions/f5889d99aeae_initial.py` is a historical no-op, but the Docker entrypoint applies migrations before application startup. A clean database therefore lacks the base tables required by this PR's revision. Test against a representative initialized database, or repair the baseline migration separately.

## Added coverage

- Backend service lifecycle, cutoff, belt eligibility, conversion, rescheduling, and duplicate attendance: `dojo-app/backend/tests/unit/test_pre_checkin_service.py`.
- Public privacy/listing and instructor count API behavior: `dojo-app/backend/tests/unit/test_api_precheckins.py`.

## Non-blocking baseline issue

- `npm run format:check` reports existing formatting issues across 19 frontend files; no project-wide formatting rewrite was made.
