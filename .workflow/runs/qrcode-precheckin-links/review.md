# Review — Real QR Codes for Check-In + Shareable Pre-Check-In Links (QRL-01–QRL-10)

## Verdict: APPROVED WITH FOLLOW-UPS

No High or Medium severity, and no correctness- or security-blocking findings. Three LOW/informational items noted below, none of which requires changes before merge; all are optional polish. Gate status (lint/typecheck/full Jest suite) already independently confirmed by root per `checks.json` — not re-verified in this pass per instruction, but reconfirmed by direct code read that the implementation matches what those gates would have exercised.

## Scope reviewed

Frontend-only, `dojo-app/frontend`. New: `src/utils/url.ts`+test, `src/utils/clipboard.ts`+test, `src/components/QrCodeModal.tsx`+test, `src/pages/CheckInPrintPage.tsx`+test, `src/pages/EventsPage.test.tsx`, `cypress/e2e/qrcode-precheckin.cy.ts`. Modified: `src/pages/EventsPage.tsx`, `src/pages/EventSeriesPage.tsx`, `src/App.tsx`, `src/pages/EventSeriesPage.test.tsx`, `cypress/e2e/events.cy.ts`, `package.json`/`package-lock.json` (added `qrcode.react@4.2.0`, confirmed installed via `npm ls qrcode.react`). Read every file above in full (not summaries), plus `qrcode.react`'s installed source for `dangerouslySetInnerHTML`/`innerHTML` usage (none found).

## Correctness checklist — QRL-01 through QRL-10

- **QRL-01 (modal)** — Confirmed. Both `EventsPage.tsx` and `EventSeriesPage.tsx` replace the old `<a href="/checkin?token=...">` with a `<button onClick={() => setQrItem({title, token})}>`; `QrCodeModal` renders title, QR, close button, print link. Covered by `QrCodeModal.test.tsx`, `EventsPage.test.tsx`, `EventSeriesPage.test.tsx`, and the Cypress spec.
- **QRL-02 (client-side generation)** — Confirmed. `QRCodeSVG` from `qrcode.react` (zero runtime deps, SVG-based, no `dangerouslySetInnerHTML` anywhere in the library's installed source), no network call involved in rendering.
- **QRL-03 (absolute URL)** — Confirmed genuinely enforced, not just claimed. `url.ts`'s `toAbsoluteUrl` is the single place `window.location.origin` is read. Grepped the entire `src/` tree for the literal path strings (`/checkin?token`, `/precheckin?`, `/checkin-print`) — every occurrence outside `url.ts` itself is in a test file or the `App.tsx` route registration; every actual link/QR-value call site (`QrCodeModal`, `CheckInPrintPage`, both copy buttons in `EventsPage.tsx`) imports and calls `buildCheckInUrl`/`buildCheckInPrintUrl`/`buildPreCheckInUrl` — no raw relative path bypasses the helper anywhere.
- **QRL-04 (print page)** — Confirmed. `/checkin-print` route, one shared parameterized page reading `?token=`/`?title=`, renders title + QR + explicit "Imprimir" button calling `window.print()` (not auto-triggered, matches plan's stated rationale), `print:w-[12cm] print:h-[12cm]` sizing present and asserted by `CheckInPrintPage.test.tsx`.
- **QRL-05 (print reachable, new tab)** — Confirmed. Modal's print control is `<a target="_blank" rel="noopener noreferrer" href={buildCheckInPrintUrl(...)}>`, asserted in `QrCodeModal.test.tsx` and exercised end-to-end in the Cypress spec (assert `target="_blank"` + independently `cy.visit()` the href, a reasonable workaround for Cypress's single-tab limitation, called out honestly in the plan rather than silently skipped).
- **QRL-06 (generic copy button)** — Confirmed. Toolbar button in `EventsPage.tsx` calls `copyToClipboardWithToast(buildPreCheckInUrl())` → bare `{origin}/precheckin`. Not present on `EventSeriesPage.tsx` (correct, no non-goal violation — grepped and confirmed zero `Copy`/`copyToClipboard`/`buildPreCheckInUrl` references in `EventSeriesPage.tsx`).
- **QRL-07 (per-event copy button)** — Confirmed. Per-row button calls `copyToClipboardWithToast(buildPreCheckInUrl(event.id))` → `{origin}/precheckin?event_id={id}`, `event.id` passed through `encodeURIComponent` inside `buildPreCheckInUrl`. Events-table-only, as required.
- **QRL-08 (clipboard feedback)** — Confirmed. Single `copyToClipboardWithToast` in `clipboard.ts`: success → `showToast('Link copiado','success')`; failure → caught (bare `catch {}`, no rethrow) → `showToast('Não foi possível copiar o link','error')`. `clipboard.test.ts` explicitly asserts the failure path resolves (never rejects) the returned promise — no unhandled rejection. Both `EventsPage.test.tsx` (denial case) and the Cypress spec exercise the wiring end-to-end, not just the isolated unit.
- **QRL-09 (missing-token defense)** — Confirmed thoroughly, including the specific stale-URL case called out in the task. `QrCodeModal` computes `hasToken = Boolean(token)` and renders the inline "Link de check-in indisponível para este item." message for both `''` and `null`, no throw (tested via `it.each`). `CheckInPrintPage` independently re-derives `token` from its own `useSearchParams()` call — it is never passed a token as a prop from a parent, so the direct/stale-bookmark-URL case and the modal-linked case are literally the same code path, not two; `CheckInPrintPage.test.tsx` explicitly covers the `?title=Aula` (no `token`) case and asserts no QR/no print button/no crash. This correctly matches the plan's Follow-up #4 and the task's specific ask to verify the print page doesn't just trust an assumed-valid prop.
- **QRL-10 (modal responsive behavior)** — Correctly deferred to Cypress per Follow-up #1 (not attempted in Jest/jsdom, which has no real layout engine — right call). `qrcode-precheckin.cy.ts` has two dedicated mobile-viewport (`375×667`) tests (Events and Event Series variants) asserting visibility of title/QR/print-link and `scrollWidth <= clientWidth`.

**`EventSeriesPage.test.tsx` diff specifically checked** (per task's explicit ask): the old test `'renders a plain anchor link to /checkin?token=... for the QR action'` was genuinely **replaced**, not left alongside a new one — `git diff` shows a clean removal of the old assertion and its replacement with `'clicking the QR icon opens the QR modal showing the series title'` plus a new falsy-token test. No dead/stale assertion survives in the suite.

**Cypress selector sanity-check**: `[title="Ver QR code de check-in"]` matches the actual `title` attribute on the QR button in both `EventsPage.tsx`/`EventSeriesPage.tsx`; `[role="img"][aria-label^="QR code de check-in"]` matches the `role="img"`/`aria-label` pattern used in both `QrCodeModal.tsx` and `CheckInPrintPage.tsx`. Selectors are plausible against the real DOM, not aspirational.

## Security checklist

- **XSS via title/token** — No unescaped user-controlled data reaches any injection-capable sink. `title` (admin-entered free text) is only ever rendered as JSX text content (`{title}`) or inside a JSX-attribute template string (`aria-label={...title...}`) — both are auto-escaped by React, never `dangerouslySetInnerHTML` or raw DOM writes (grepped `src/` for `dangerouslySetInnerHTML`/`innerHTML` — zero matches anywhere in the codebase, not just this feature). URL construction (`url.ts`) applies `encodeURIComponent` to both `token` and `title` before interpolating into query strings, confirmed by `url.test.ts`'s explicit space/`&`/`/`-containing test cases.
- **`QRCodeSVG` value prop** — Confirmed the installed `qrcode.react` package contains no `dangerouslySetInnerHTML`/`innerHTML` usage; it renders QR modules as SVG `<rect>`/`<path>` elements computed from the encoded bit matrix, not by injecting the `value` string as markup. The `value` fed to it is always `buildCheckInUrl(token)` — token only, never the raw admin-entered `title` — so even a maliciously-crafted title could not end up inside the QR-encoded payload itself.
- **`/checkin-print` route auth** — Confirmed genuinely behind `PrivateRoute` in `App.tsx` (same tier as `/events`/`/event-series`, not a new public route), matching QRL-04's requirement.
- **`navigator.clipboard.writeText` usage** — Both call sites only ever pass strings built by `url.ts`'s own helpers (`buildPreCheckInUrl(...)`) — no user-controlled/external string is ever written to the clipboard. Failures are caught inside `copyToClipboardWithToast`'s `try/catch` (bare `catch {}`, no rethrow) — confirmed no unhandled promise rejection path exists, and no clipboard error detail is logged or surfaced to the console/user beyond the generic toast message (no leak of any denial reason/permission state).

No High/Medium security findings.

## Findings (all LOW / informational, non-blocking)

### 1. [LOW — informational, minor privacy/URL-hygiene] Event/series title now travels in the `/checkin-print` URL as a plaintext query parameter

Before this feature, the check-in link only ever carried a token (`?token=...`). `buildCheckInPrintUrl` now also embeds the admin-entered `title` in cleartext in the query string (`?token=...&title=...`), which lands in browser history, and — because the print link opens in a new tab via `target="_blank"` — could be visible in that tab's own address bar if an admin screenshots or shares it. The title itself isn't sensitive (it's already visible in the Events/Series table to anyone with the same access), and this is a deliberate, plan-documented tradeoff to avoid a second API call from the print page (see `plan.md`'s rationale for the shared-route, query-param-only design). Not a vulnerability — flagging purely for awareness. No fix required.

### 2. [LOW — correctness/UX edge case, untested] `CheckInPrintPage` renders an empty `<h1>` if `token` is present but `title` is missing from the query string

`const title = searchParams.get('title') ?? ''` — a hand-edited or partially-malformed URL with a valid `token` but no `title` param would render a blank heading above the QR code rather than a fallback label (e.g. "Check-in") or omitting the heading. This combination isn't covered by `CheckInPrintPage.test.tsx` (which only tests "both present" and "token missing" — not "title missing, token present"). Low likelihood in practice since the only real path to this page is via `QrCodeModal`'s print link, which always supplies both; only reachable via a hand-crafted URL. No QRL criterion explicitly requires a fallback title, so this doesn't block approval — worth a one-line follow-up (`searchParams.get('title') ?? 'Check-in'` or similar) if convenient, not required.

### 3. [LOW — maintainability nit] The `role="img"` / `aria-label={`QR code de check-in: ${title}`}` pattern is duplicated verbatim between `QrCodeModal.tsx` and `CheckInPrintPage.tsx`

Two call sites, both small, both already covered by tests that key off this exact string — not worth extracting given the "avoid overengineering" convention for a two-line pattern, but noting it in case a third QR-rendering call site is ever added, at which point extracting a tiny shared `QrImage` wrapper would become worthwhile.

## What was explicitly NOT found (checked for, absent)

- No raw relative check-in/pre-check-in URL bypassing `url.ts` anywhere in application code.
- No stale/leftover test asserting the old anchor-link QR behavior.
- No per-series pre-check-in copy button (non-goal correctly honored).
- No `dangerouslySetInnerHTML`/`innerHTML` usage anywhere touched by this feature (or the codebase generally).
- No unhandled promise rejection path in the clipboard flow.
- No public/unauthenticated route introduced.

## Next Agent

Next Agent: linter (review passed; the three findings above are optional polish, not blocking — no need to route back to implementer/sre unless the team wants to pick up Finding #2 opportunistically).
