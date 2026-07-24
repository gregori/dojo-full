# Independent + Security Review — PR-4: Contracts

## Verdict: NOT APPROVED (first pass) — 2 HIGH correctness findings (both empirically reproduced), plus Medium/Low items

Both HIGH findings directly undermine the plan's own stated D1/D6 invariants ("single transaction... matches D1's atomically requirement"; "at most one draft-or-signed contract per student... service-enforced"). Neither is caught by the 321 passing backend tests because no test exercises "generation fails after `assign` succeeds" or "a third `matricular` call while a signed + draft pair coexists."

## Reviewed

Backend: `app/models/__init__.py` (`ContractTemplateVersion`, `Contract`), `alembic/versions/56d1afc5972f_add_contracts.py`, `app/schemas/contract.py`, `app/schemas/contract_template.py`, `app/core/uploads.py`, `app/core/storage.py`, `app/services/contract_pdf_service.py`, `app/services/contract_template_service.py`, `app/services/contract_service.py`, `app/services/student_plan_service.py`, `app/services/medical_exam_service.py` (post-extraction), `app/api/contracts.py`, `app/api/contract_templates.py`, `app/main.py`. Frontend: `SignaturePad.tsx`, `ContractTemplatesPage.tsx`, `StudentsPage.tsx`. All new tests. Two findings below were empirically verified by running the code (not just reading it) via scratch reproduction scripts.

## Findings (ranked, most severe first)

### 1. [HIGH — Correctness, breaks D1/AC1] `generate_for_matricula` is not actually atomic

`StudentPlanService.assign` (`student_plan_service.py:77`) commits internally. `ContractService.generate_for_matricula` (`contract_service.py:71-112`) calls `assign` first, then `validate_merge_fields`/active-template-lookup afterward — both of which can raise `HTTPException(400)` *after* the plan reassignment is already durably committed.

Empirically reproduced (SQLite scratch script): a student missing `phone` → `StudentPlan` row count goes from 0 to 1 even though `generate_for_matricula` raises and no `Contract`/PDF is ever created. Same result for the "no active contract template" path.

**Failure scenario:** instructor clicks "Matricular/Renovar" for a student with an unfilled legal field (very plausible day-one state, since these fields are new/nullable) — the student's plan is silently reassigned/re-priced, the 400 is shown, and the *first* `StudentPlan` row is now permanent history mismatched from the eventual contract. This is exactly the drift-risk gap this phase was designed to close (plan.md:272), just reachable via a failed attempt instead of the old bare endpoint.

**Fix guidance:** run `validate_merge_fields`/active-template lookup *before* calling `assign` (neither depends on its result) — closes both concretely reachable failure modes.

### 2. [HIGH — Correctness, breaks D6/D7 invariant] `get_active_or_draft` has no deterministic ordering, can't distinguish draft vs signed when both legitimately coexist (mid-renewal)

`contract_service.py:21-28`: no `order_by`, returns whichever of a coexisting `draft`+`signed` pair the DB happens to return first. This state is not an edge case — it's the exact state D1's own renewal path creates (plan.md:360: "the previous signed row is *not* touched yet").

Empirically reproduced: matricula → sign → matricula-again (renewal) leaves one `signed` + one `draft` row; `get_active_or_draft` returns the **signed** row, not the draft. A third `matricular` call then creates a *second* duplicate draft (orphaning the first) because the code read `existing.status == "signed"` instead of finding the real draft.

**Failure scenario:** any student mid-renewal shows the *old signed* contract as "current" (`GET .../contracts/current`), hiding the actual draft needing review/signature; retrying creates a redundant draft row and orphans a rendered PDF `Document`.

**Fix guidance:** make the lookup prefer `status == "draft"` first, falling back to `signed` only if no draft exists. Add regression tests for "renewal in progress, matricular called a third time" and "current contract during a renewal returns the draft."

### 3. [MEDIUM — Correctness/robustness] On-screen signature payload has no size limit; malformed base64 causes an unhandled exception

`api/contracts.py:24-27` / `schemas/contract.py:26-29`: no `max_length` on `signature_png`, no bounded reading (unlike the sibling upload path, which reuses `read_bounded`/`validate_file`'s 10MB cap). Empirically confirmed a 200MB base64 payload decodes with no rejection. Invalid base64 (`binascii.Error`) is uncaught, producing a generic 500 instead of a clean 400 (no stack trace leaks — `debug=False` — but still an ungraceful crash).

**Fix guidance:** add `Field(max_length=...)` sized for a generous signature PNG; wrap `base64.b64decode` in `try/except (binascii.Error, ValueError)` → `HTTPException(400, "Invalid signature image data")`.

### 4. [LOW — polish] Contract download always advertises `.pdf` filename even for a JPEG/PNG-uploaded signed scan

`api/contracts.py:110`: hardcoded `filename="contract-{contract_id}.pdf"` regardless of actual `mime_type`. `Content-Type` header itself is correct — cosmetic only, not a security issue.

**Fix guidance:** derive the filename extension from `contract.document.mime_type`.

### 5. [Non-blocking, matches accepted PR-2 precedent] Template-version supersession race

`contract_template_service.py:23-39` reads-then-writes the prior active row with no row lock — same shape as the medical-exam residual finding PR-2's review already accepted as non-blocking. Not re-flagged as blocking here for consistency.

## Confirmed correct (verification points addressed, not just claimed)

1. **D3 merge-field validation** — collects *all* missing fields in one pass, no short-circuit (`contract_pdf_service.py:33-40`, regression-tested).
2. **D4 upload policy reuse** — clean, behavior-preserving extraction to `app/core/uploads.py`; `medical_exam_service.py` still uses the shared helpers; magic-byte validation (not client `Content-Type`) confirmed, avoiding PR-2's original HIGH finding.
3. **D6/D7 regeneration semantics** — correct in isolation (never re-derives `plan_version_id`/`contract_template_version_id`; `Document` superseded-not-mutated via `_supersede_document`; cross-contract supersession-on-signing via `_supersede_other_signed_contracts`) — undermined only by finding 2's lookup bug.
4. **Authorization** — every new endpoint (`contracts.py`, `contract_templates.py`) requires `get_current_instructor_or_admin`; confirmed by code and by `test_api_contracts.py::TestAuthorization` (401 on all 10 endpoints, no auth override).
5. **Download endpoint path traversal / cross-document leak** — none found. Lookup is strictly by `Contract.id` (DB PK), storage keys are UUID-based and student-namespaced, no caller-supplied key reaches `storage.py:download_document`.
6. **`StudentsPage.tsx` button repoint** — confirmed via grep: no call site posts to the old bare `/plan` endpoint anymore; only the new combined `.../contracts/matricular` endpoint is called, with a regression test asserting the old endpoint is never hit.
7. **CPF/PII exposure** — no logging of `contract_cpf`/`contract_name` anywhere; error messages name only field names, never values; response schemas never expose `storage_key` or raw file bytes outside the auth-gated download endpoint.

## Next step

Findings 1-4 sent back to implementer to fix (finding 5 accepted as non-blocking, consistent with PR-2 precedent).

---

## Re-verification pass — 2026-07-23

**Verdict: APPROVED.** All four blocking findings are genuinely fixed at the code level, each with a non-superficial regression test reproducing the originally-reported failure mode (not just a happy-path check). No new correctness or security issues introduced by the fixes. Finding 5 remains correctly unfixed and non-blocking per prior precedent.

### Finding 1 (HIGH — atomicity) — FIXED
`contract_service.py:85-93`: merge-field validation and active-template lookup now both run before `StudentPlanService.assign` (which still commits internally, unchanged). Evidence: `test_no_plan_reassignment_committed_when_student_data_missing` and `test_no_plan_reassignment_committed_when_no_active_template` (`test_contract_service.py:82-114`) assert `StudentPlan` row count stays `0` after the `HTTPException` — the exact DB-side-effect the original finding reproduced.

Residual, non-blocking, out of this finding's scope: `_render_and_store_document` (PDF render + upload) after `assign` commits could still theoretically fail (e.g. storage I/O error), leaving the same class of orphan-commit gap the original finding's own fix guidance didn't cover. Noted for awareness only.

### Finding 2 (HIGH — non-deterministic lookup) — FIXED
`contract_service.py:22-34`: now queries `status == "draft"` first, falling back to `signed` only if none exists. Evidence: `test_prefers_the_draft_when_a_signed_and_draft_contract_coexist` and `test_third_call_during_renewal_reuses_the_draft_not_a_second_orphaned_one` (`test_contract_service.py:143-177`) reproduce the exact matricula→sign→matricula→matricula renewal sequence from the original finding and assert the third call reuses the renewal draft with no orphaned second draft.

### Finding 3 (MEDIUM — signature payload) — FIXED
`schemas/contract.py:13,35`: `signature_png` bounded via `Field(max_length=700_000)`. `api/contracts.py:26-32`: `_decode_signature_png` catches `binascii.Error`/`ValueError` → clean 400. Evidence: `test_sign_on_screen_rejects_malformed_base64` (400, not 500) and `test_sign_on_screen_rejects_oversized_payload` (422) in `test_api_contracts.py:263-287`.

Non-blocking, out of scope: decoded bytes still aren't validated as an actual PNG before reaching reportlab's `Image(...)` (`contract_pdf_service.py:81`) — a valid-base64/non-PNG payload could still throw unhandled. Pre-existing, unchanged; worth a follow-up ticket if full input hardening is wanted.

### Finding 4 (LOW — filename) — FIXED
`api/contracts.py:112`: `mimetypes.guess_extension(mime_type)` replaces the hardcoded `.pdf`. Evidence: `test_download_filename_extension_matches_the_uploaded_mime_type` (`test_api_contracts.py:289-302`).

### Adjacent sanity check
Authorization unchanged (`get_current_instructor_or_admin` on all endpoints). No new injection/traversal surface (`mime_type` only ever comes from magic-byte-validated allowlist or a hardcoded literal, never attacker-controlled as a path). No new PII in error messages or logs.

### Still outstanding before Phase 4 can be marked fully complete
- Cypress e2e (`contracts.cy.ts`) exists but has not been run against a live stack.
- PR-4 has not yet been committed/merged (working tree still uncommitted on `feature/contracts`).

## Next Agent

Next Agent: planner (to schedule the Cypress e2e run and commit/merge once the user confirms).
