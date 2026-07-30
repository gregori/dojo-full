# Handoff — Real QR Codes for Check-In + Shareable Pre-Check-In Links (QRL)

## What Was Done

- Standalone, bounded, frontend-only feature. Scope decided directly with the user before this run started (see `requirements.md`'s "Decision already locked in"): client-side QR image generation for Event/EventSeries check-in links (modal + printable A4 page), plus copy-to-clipboard buttons for the pre-check-in link (generic + per-event). No backend changes.
- Full cycle run: product-manager (`requirements.md`, QRL-01..QRL-10) -> requirements-reviewer (`review-requirements.md`, approved with 4 non-blocking follow-ups) -> tech-analyst (`plan.md`, folded all 4 follow-ups in directly) -> implementer (code + tests) -> reviewer (`review.md`, approved with 3 LOW/informational findings). `doc-writer`/`issue-creator` steps skipped per this repo's own established precedent for bounded feature runs (see `recurring-event-series/handoff.md`).
- Implementer's first pass had 8 Jest failures (jsdom-version-specific mocking issues: `window.location` redefinition, and `navigator.clipboard` colliding with `@testing-library/user-event`'s own getter-only clipboard mock) and was missing both Cypress deliverables. Root independently ran the gates, diagnosed both root causes, and sent the implementer back with the exact fix; second pass resolved everything.
- Root independently re-confirmed (not just implementer self-report): full Jest suite 15 suites / 77 tests passed (0 regressions), ESLint clean, `tsc --noEmit` clean. Cypress specs written but not executed (needs a live app+backend, matches this run's own scope and prior runs' gate scope).

## Key Decisions

- QR library: `qrcode.react` `^4.2.0` — SVG-based (resolution-independent, scales cleanly from 240px modal to 12cm print size with no pixelation), zero non-React runtime dependencies, jsdom-safe (no canvas dependency, unlike a raster-based alternative which would need an extra `canvas` native devDependency to test).
- One shared `/checkin-print` route (not two separate Event/EventSeries routes) reading `token`+`title` from its own query string — avoids duplicating print layout for zero behavioral difference; makes no new API call (reuses data the modal already has in memory).
- Absolute-URL requirement (QRL-03) centralized in one utility module (`utils/url.ts`) so there is exactly one place to get `window.location.origin`-based URL construction right, reused by the modal, print page, and both copy buttons.
- Print trigger is an explicit on-page "Imprimir" button (not auto-`window.print()` on mount) — deterministically testable in both Jest and Cypress, and doesn't pop a real print dialog on every page visit.

## Non-blocking follow-ups left un-actioned (per review.md's own framing)

1. Event/series title travels in the `/checkin-print` URL as a plaintext query param — a documented tradeoff (avoids a second API fetch/source of truth), not a vulnerability.
2. `CheckInPrintPage` renders an empty `<h1>` if `token` is present but `title` is missing from a hand-crafted URL — untested edge case, no criterion requires a fallback.
3. Minor duplication of the `role="img"`/`aria-label` QR-image markup pattern between `QrCodeModal.tsx` and `CheckInPrintPage.tsx` — not worth extracting yet at this scope.

## Status

Feature complete, gate-clean, independently reviewed **APPROVED WITH FOLLOW-UPS** (no blocking correctness or security findings). **Not committed/pushed yet — awaiting the user's explicit go-ahead**, per this session's established pattern for prior runs (`contract-markdown-rendering`, `recurring-event-series`).

## Fix Pass (2026-07-30) — 3 LOW review findings

User asked to address all 3 LOW/informational findings from `review.md` before commit, even though none were blocking:

1. **Title-in-URL (Finding #1) + empty-title fallback (Finding #2), fixed together.** `buildCheckInPrintUrl` now takes only `token` (no `title` param) -- the `/checkin-print` URL no longer carries the title in plaintext. `QrCodeModal`'s print link's `onClick` stores the title keyed by token in browser storage; `CheckInPrintPage` reads it (falling back to `"Check-in"` if absent) and deletes it immediately after reading (read-once).
2. **Finding #3 (duplicated QR markup).** Extracted a shared `dojo-app/frontend/src/components/QrImage.tsx` (the `role="img"`/`aria-label` wrapper around `QRCodeSVG`), used by both `QrCodeModal.tsx` and `CheckInPrintPage.tsx`.

**A real bug was caught by manual browser re-verification of this fix pass, missed by all automated tests:** the first implementation used `sessionStorage`. In a real browser, `sessionStorage` is *not* shared with a tab opened via `<a target="_blank" rel="noopener ...">` -- `rel="noopener"` (kept intentionally, for security) creates a new browsing-context group with fresh storage, so the print page fell back to the generic `"Check-in"` title instead of the real one. Jest/jsdom has no concept of opener-scoped storage (single global per test) and the Cypress spec's own workaround (stripping `target` to force same-tab navigation, since Cypress can't drive a second real tab) accidentally masked the exact same bug it should have caught. Switched to `localStorage` (origin-scoped, not browsing-context-scoped, so it survives the `noopener` boundary) with explicit read-then-delete cleanup to avoid unbounded accumulation. Re-verified in a real new tab in the browser: correct title now renders, no `title` in the URL, and the storage entry is gone after being read.

Re-ran full gates after the fix: Jest 15/15 suites, 79/79 tests passed; ESLint clean; `tsc --noEmit` clean. All three findings resolved without reopening the review's verdict (no new correctness/security issue introduced -- the bug was in the *fix*, not the original approved implementation, and was caught and corrected within this same fix pass before being reported as done).

## Manual Browser Verification (2026-07-30)

Per project CLAUDE.md's UI-change verification rule, root started the app via `docker compose` (dojo-app/) and drove it end-to-end in a real browser (admin@dojo.com), not just relying on automated tests:

- Created a test Event and a test EventSeries; clicked the QR icon on each -> modal opened showing the correct title and a real, scannable QR image (QRL-01, series variant included).
- Clicked "Imprimir" in the modal -> opened `/checkin-print?token=...&title=...` in a genuinely new tab (QRL-05); print page rendered title + large QR; clicking its own "Imprimir" button called `window.print()` (verified via a stubbed `window.print`, without actually triggering the native OS print dialog) (QRL-04).
- Clicked the Events page's generic toolbar copy button -> "Link copiado" toast shown, clipboard stub received the exact absolute URL `http://localhost:3000/precheckin` (QRL-06, QRL-08).
- Clicked an event row's per-event copy button -> clipboard stub received `http://localhost:3000/precheckin?event_id={that event's real id}` (QRL-07).
- Confirmed the Event Series table has no per-series copy-link button (matches the non-goal).
- Navigated directly to `/checkin-print` with no `token` query param -> rendered "Link de check-in indisponível para este item." with no crash, inside the authenticated layout (confirms `PrivateRoute` guard + QRL-09/Follow-up #4's direct-URL defensive path).

No functional issues found. (Unrelated hiccups during manual testing, not app bugs: an accidental click on the sidebar "Sair" logged out a tab mid-test, and the native multi-segment `<input type="datetime-local">`/`<input type="date">` fields were fiddly to drive via synthetic keystrokes in the create-event/create-series forms -- both were testing-tool friction, not feature defects.)

## PR #41 CI Fix (2026-07-30)

CI's "test" job failed on the Prettier `format:check` step (4 files: `QrCodeModal.test.tsx`, `CheckInPrintPage.test.tsx`, `CheckInPrintPage.tsx`, `clipboard.test.ts`) -- root's local gate pass had covered `lint`/`tsc`/`jest` but not `npm run format:check` or `npm run build`, both of which are also required by `.github/workflows/ci-frontend.yml`'s `test` job (workflow file lives on `master`, not checked out on this `develop`-based working tree, hence not discovered until CI actually ran it). Root reproduced the failure locally (`npm run format:check`), ran `npx prettier --write` on the 4 flagged files (formatting-only diff, 8 insertions/16 deletions), then re-ran the full `test` job locally end-to-end (`lint`, `format:check`, `npm run build`, `npm test -- --coverage --watchAll=false --passWithNoTests`) before committing (`29d83b5`) and pushing. Re-triggered CI confirmed both `test` and `e2e` jobs green; `build` correctly skips (guarded to `master`-branch pushes only, not PRs).

Also noted for awareness (not actioned, pre-existing CI scope, unrelated to this PR): the `e2e` job's Cypress run uses a hardcoded `--spec` list (`precheckin.cy.ts`, `medical-exam.cy.ts`, `financial.cy.ts`, `contracts.cy.ts`, `reports.cy.ts`) that does not include `events.cy.ts` or the new `qrcode-precheckin.cy.ts` -- neither this PR's new Cypress spec nor the pre-existing `events.cy.ts` currently run in CI. This is a pre-existing gap in `ci-frontend.yml`'s spec list, not something introduced by this PR.

## Next Action

Feature is implementation-complete, gate-clean (all CI jobs green on PR #41), independently reviewed, all 3 non-blocking follow-ups addressed (including a real cross-tab-storage bug caught and fixed during the fix pass itself), and manually re-verified in a real browser. Awaiting PR review/merge.
