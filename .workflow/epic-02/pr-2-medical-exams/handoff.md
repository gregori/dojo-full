# Handoff — PR-2: Exames Médicos + Document Foundation

## What Was Done

- Implemented the Phase 2 plan (`.workflow/runs/epic-02-plan/plan.md`, "Phase 2 Implementation Plan"): `Document`/`MedicalExam` models and migration `ea64c8751ff2` (on `b39e1a4c7d20`), instructor/admin CRUD + status/dashboard endpoints, a public registration+PIN self-service upload endpoint, OCI Object Storage integration (`app/core/storage.py`), and matching frontend UI (`MedicalExamPage.tsx`, `StudentsPage.tsx` badge/upload/history, `DashboardPage.tsx` alert list).
- Deterministic gates passed: `ruff check`/`format --check`, `pytest tests/unit` (242/242, 22 new), `npm run lint`, `npm run build`. Migration verified upgrade/downgrade/upgrade against a real MySQL 8.0 container. Details in `lint-results.md` and `test-results.md`.

## Review Outcome

- **Reviewer verdict: APPROVED.** All 4 findings from the first review pass were re-verified against the current working-tree diff and confirmed fixed. Full detail (including the re-review trace) in `review.md`.
- **Fix verification summary:**
  1. **HIGH, correctness (frontend multipart) — RESOLVED.** Both `MedicalExamPage.tsx:43` and `StudentsPage.tsx:220` now use `headers: { 'Content-Type': undefined }`. Traced through the installed axios source (`AxiosHeaders.set`/`toJSON`, `Axios.js` header merge, `xhr.js`) and confirmed this genuinely removes the header from the outgoing request (not just changes its string value), letting the browser auto-compute the multipart boundary.
  2. **HIGH, security (spoofable file type) — RESOLVED.** `_validate_file` now checks magic-byte signatures (`%PDF-`, PNG, JPEG) against the declared `content_type`, applied uniformly via the single shared `record_exam` path for both instructor and public uploads. New test `test_rejects_spoofed_content_type_with_mismatched_magic_bytes` proves it.
  3. **MEDIUM (unbounded read) — RESOLVED.** New `_read_bounded` reads in 1MB chunks and aborts as soon as the running total exceeds 10MB, verified correct at the chunk boundary and by the new streaming-double test (`test_oversized_upload_is_rejected_without_reading_the_entire_stream`).
  4. **MEDIUM (supersession race) — RESOLVED for the primary scenario.** `_get_active_record(..., for_update=True)` now locks the existing active row inside the same transaction as the write/commit, genuinely serializing concurrent supersession on MySQL. One narrow, non-blocking residual edge case remains: when a student has no prior active record, two fully-concurrent first-ever submissions aren't covered by an explicit lock (relies on InnoDB gap-locking, unverified by tests since SQLite ignores `FOR UPDATE`). Documented as a follow-up suggestion in `review.md`, not required for merge.
- **Confirmed correct (from the first pass, unchanged):** AC7/AC8 scope boundaries, public-endpoint rate limiting (IP + registration) and generic non-disclosing responses matching `pre_checkins.py`, constant-time PIN check via existing `verify_password`, instructor/admin route authorization, no raw SQL, OCI credentials never logged/returned, UUID-based non-predictable storage keys, migration upgrade/downgrade symmetry, soft-delete/audit trail on supersession (no hard deletes).

## Next Agent

- **linter** — proceed to the next workflow phase; no further reviewer-blocking issues remain.
- Optional low-priority follow-up (not a merge blocker): lock the parent `Student` row in `record_exam` to close the narrow first-submission race window described above.
