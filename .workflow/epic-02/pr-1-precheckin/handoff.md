# Handoff — PR-1: Pré-Checkin

## What Was Done

- Implemented the approved Pre-Checkin slice in `dojo-app/`.
- Added `PreCheckIn`, event minimum-belt eligibility, reversible migration, public confirmation/cancellation/list endpoints, and instructor count/roster endpoints.
- Added public `/precheckin`, protected Events count badges and roster panel, and a public Axios client that does not redirect invalid public requests to login.
- Physical attendance converts a confirmed record transactionally; a database uniqueness constraint now protects one attendance per student/event.
- Added focused backend service/API tests and `docs/api/pre-checkin.md`.

## Decisions Made

- Pre-checkin remains separate from physical attendance; it converts only when a physical check-in succeeds and preserves its physical method.
- `Event.minimum_belt_id` drives configurable eligibility using `Belt.sort_order`.
- Public responses are generic before credential validation; attempts are rate-limited by IP and registration.
- Changes close one hour before start and for non-scheduled events. A reschedule into the cutoff cancels current confirmations.

## Open Questions

- None outstanding. The Alembic smoke test is done (see below).

## Verification

- Passed: frontend `npm run lint`, `npm run build`, repository `git diff --check`, full backend pytest suite (220 tests), backend Ruff check/format.
- Passed: Alembic upgrade/downgrade round-trip smoke test against a fresh MySQL 8.4 container (upgrade head -> downgrade base -> upgrade head).
- See `review.md`, `security.md`, `test-results.md`, `lint-results.md`, and `release-notes.md` in this directory.

## Root Cause Found and Fixed

- The initial Alembic revision (`f5889d99aeae`) was a historical no-op because `app/main.py` bootstrapped the schema via `Base.metadata.create_all(bind=engine)` at startup, bypassing Alembic entirely. On a genuinely fresh database, `alembic upgrade head` failed with `Table 'dojo.attendances' doesn't exist` since the pre-checkin migration assumes the baseline tables already exist.
- Fix: rewrote `f5889d99aeae_initial.py` to actually create the full baseline schema (all 13 base tables, generated via `alembic revision --autogenerate` against the pre-PR models on an empty database), and removed `Base.metadata.create_all(bind=engine)` from `app/main.py` so Alembic is now the single source of schema truth. The Docker entrypoint already runs `alembic upgrade head` before startup.
- While smoke testing, also found and fixed a real downgrade bug in `b39e1a4c7d20_add_pre_checkins.py`: MySQL replaces the auto-generated single-column FK index on `attendances.event_id` with the new composite unique index `uq_attendances_event_student`, so dropping that constraint in `downgrade()` failed with "needed in a foreign key constraint." Fixed by recreating a plain index on `event_id` before dropping the unique constraint.
- Found and fixed a pre-existing regression in `tests/unit/test_exam_service.py::test_check_eligibility_eligible`: it inserted two `Attendance` rows for the same event+student, which the PR's own new `uq_attendances_event_student` constraint now forbids. The original PR-1 test run only executed the two new pre-checkin test files, not the full suite, so this was not caught earlier. Fixed by attending two distinct events instead.

## Next Action

- Commit the PR using the recorded release notes.
