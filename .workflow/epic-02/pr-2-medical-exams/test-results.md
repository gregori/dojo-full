# Test Results — PR-2 Exames Médicos + Document Foundation

## Passed

- `cd dojo-app/backend; uv run ruff check .`
- `cd dojo-app/backend; uv run ruff format --check .`
- `cd dojo-app/backend; uv run pytest tests/unit -q` — 242 passed, 0 failed (22 new: 15 in `test_medical_exam_service.py`, 7 in `test_api_medical_exams.py`)
- `cd dojo-app/frontend; npm run lint`
- `cd dojo-app/frontend; npm run build`

## Migration verification

- `alembic upgrade head` / `downgrade -1` / `upgrade head` run against a real MySQL 8.0 container (`dojo-app/docker-compose.yml`'s `db` service). Full chain `f5889d99aeae → b39e1a4c7d20 → ea64c8751ff2` applies and reverses cleanly. A MySQL FK/index interaction on downgrade (same class of issue already documented in `b39e1a4c7d20`'s downgrade comment) was found and fixed by restoring a plain single-column index before dropping the composite one.

## Added coverage

- Status computation (`valido`/`vencendo`/`vencido`/`sem_registro`), transactional supersession (exactly one active record per student), file validation, rate limiting, and public/instructor auth: `dojo-app/backend/tests/unit/test_medical_exam_service.py`.
- Public and instructor API behavior (authorization, generic non-disclosing responses): `dojo-app/backend/tests/unit/test_api_medical_exams.py`.

## Not added (with rationale)

- No Jest specs added for the new frontend pages — the repo has zero existing Jest specs anywhere (`npm run test` reports "No tests found" both before and after this change), so there is no established pattern to extend.
- No Cypress spec added for the new public `MedicalExamPage.tsx` — Phase 1's structurally equivalent `PreCheckInPage.tsx` also has no corresponding `.cy.ts` spec, and existing Cypress specs require a live seeded backend and are not run in `ci-frontend.yml`. Consistent with Phase 1 precedent; flagged for reviewer to confirm this precedent should carry forward.

## Non-blocking baseline issue

- `npm run format:check` reports pre-existing formatting drift on 15 frontend files unrelated to this PR (see `lint-results.md`); no project-wide reformat was made.

## Follow-up items for CI / ops (not implementation gaps)

- `poetry.lock` was regenerated via `uvx poetry lock` (real Poetry 2.4.1) after adding the `oci` SDK dependency; not yet verified against the CI-pinned `poetry install --no-interaction` path.
- New `OCI_*` settings (`oci_tenancy_ocid`, `oci_user_ocid`, `oci_fingerprint`, `oci_private_key`, `oci_region`, `oci_bucket_namespace`, `documents_bucket_name`) match existing `extract-oci-creds.sh` secret naming; actual secret values/CI env wiring are outside this PR's scope.
