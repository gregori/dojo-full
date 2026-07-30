# Requirements — Real QR Codes for Check-In + Shareable Pre-Check-In Links (QRL)

## Status

First pass. Scope was already decided directly with the user in the session that produced this document (see "Decision already locked in" below) — this document formalizes that decision into structured, testable acceptance criteria; it is not the output of a fresh requirements interview. Standalone, bounded feature — not part of Epic 2 (`.workflow/epic-02/handoff.md`, shipped) or either in-flight run (`recurring-event-series`, `contract-markdown-rendering`).

## Context

Ground truth confirmed directly against the codebase before this document was written:

- `Event` and `EventSeries` (`dojo-app/backend/app/models/__init__.py`, ~line 198 and ~line 222) each already have a `check_in_token` (UUID string), generated at creation and already exposed via their API schemas (`dojo-app/backend/app/schemas/event.py:62`, `dojo-app/backend/app/schemas/event_series.py:67`). No backend change is needed to read this value from the frontend.
- Today's "QR" affordance is **not** a QR image — it is a plain `<a href="/checkin?token=...">` link wrapped around a lucide `QrCode` icon, in both `dojo-app/frontend/src/pages/EventsPage.tsx` (~line 415-423) and `dojo-app/frontend/src/pages/EventSeriesPage.tsx` (~line 473-481). Clicking it opens `/checkin?token=...` in a new tab, handled by `CheckInPage.tsx`.
- Pre-check-in is a single public page, `/precheckin` (route registered in `App.tsx`), component `PreCheckInPage.tsx`. It accepts an optional `?event_id=` query param to preselect one event; if omitted, it lists open events via the public, unauthenticated `GET /api/v1/pre-checkins/events` and lets the student pick one. There is currently no admin-facing way to copy/share this URL — an admin would have to hand-type it.
- No QR-image-generation library exists anywhere in the repo (checked `dojo-app/frontend/package.json`, backend `pyproject.toml`) — this is entirely new for the frontend.
- No `navigator.clipboard` usage exists anywhere in the frontend today — clipboard copy is also new.
- A reusable global toast singleton already exists (`dojo-app/frontend/src/components/Toast.tsx`, `showToast(message, type)`), used elsewhere in the app for success/error feedback; this feature should reuse it rather than invent a new feedback mechanism.
- No `window.print()` / print-specific styling exists anywhere in the frontend today — the print page is also entirely new.

**The problem:** the dojo admin cannot print a physical, scannable QR code to post at the dojo (today's icon is just a same-tab/new-tab link, not an image), and has no quick way to hand a student the pre-check-in page URL (e.g. via WhatsApp) without manually typing it.

## Decision already locked in (do not re-litigate)

Agreed directly with the user in this session, not re-opened here:

1. QR codes are generated **client-side** (frontend only) from the existing `/checkin?token=...` link. No new backend endpoint for QR generation — `check_in_token` is already returned by both `Event` and `EventSeries` schemas.
2. The QR is shown in two places: (a) a modal opened from the existing QR icon in both the Events table and the Event Series table; (b) a dedicated print page, reachable from that modal, formatted for A4 with the event/series title and a large QR code, for the admin to print and post at the dojo.
3. Pre-check-in link sharing is done via copy-to-clipboard buttons in two places: (a) a generic button on the Events page that copies the bare `/precheckin` URL (student picks the event on the page); (b) a per-event button in the Events table that copies `/precheckin?event_id={id}` for that specific event. Event Series does **not** get a per-series pre-check-in copy button — pre-check-in is always against a concrete `Event` occurrence, not a series.
4. No backend changes of any kind are required or in scope.

This document resolves the remaining product-level specifics that decision leaves open: exact modal/print-page content, absolute-vs-relative URL handling (QR codes and copied links must work when scanned/opened outside the app's own browser tab, so this matters), clipboard-failure behavior, missing-token behavior, and responsive behavior.

## User Persona

**Dojo admin** — manages events and event series via `EventsPage.tsx` / `EventSeriesPage.tsx`. Wants to (a) print a QR code once and post it physically at the dojo so students self-check-in by scanning it with their own phone camera, and (b) quickly share a pre-check-in link with students via chat apps (e.g. WhatsApp) ahead of a class.

**Student** — the eventual consumer of both artifacts, but never interacts with any UI introduced by this feature directly: scans a printed QR with their phone's camera (outside the app), or taps a link an admin pasted into a chat. Both must therefore resolve to a working page from a fresh, unauthenticated browser context with no app state.

## Business Outcome

An admin can, without any developer involvement, print a real scannable QR code for any event or series and physically post it at the dojo, and copy a working pre-check-in link to paste into a chat with students — both self-service, both using data the backend already provides today.

## In Scope

### QRL-01 — QR code modal (Events and Event Series)

Clicking the existing QR icon (`dojo-app/frontend/src/pages/EventsPage.tsx` ~line 415, `dojo-app/frontend/src/pages/EventSeriesPage.tsx` ~line 473) no longer navigates to `/checkin?token=...` directly. Instead it opens a modal, reused/shared between both pages, that:

- Displays the event's or series' title.
- Displays a rendered QR code image (see QRL-02) encoding the check-in URL for that specific event or series.
- Provides a way to close the modal (e.g. an explicit close control and/or backdrop click), consistent with this codebase's existing modal patterns (e.g. `rosterEvent`/`viewVersion`-style modal state already used elsewhere in `EventsPage.tsx` and `ContractTemplatesPage.tsx`).
- Provides a control that opens the print page (QRL-04).

**Given** an admin on the Events page **when** they click the QR icon for an event with a non-empty `check_in_token` **then** a modal opens showing that event's title and a QR image encoding `{origin}/checkin?token={event.check_in_token}`. The equivalent holds for the Event Series page using `series.check_in_token`.

### QRL-02 — Client-side QR image generation

A QR code image is generated entirely in the browser (no network request to generate it) from the check-in URL described in QRL-03. The exact client-side library is a technical decision left to `tech-analyst`, constrained by: no backend involvement, no new heavy dependency unjustified by this feature's small scope (mirrors this repo's existing CTM-09-style "avoid overengineering" constraint), and the rendered image must be legible both on-screen in the modal and at print size (QRL-04) — i.e. it must be either a vector/SVG-based render or a raster render at a resolution high enough not to visibly pixelate at the print page's large size.

### QRL-03 — QR and copied links must use an absolute, origin-qualified URL

Both the QR-encoded check-in link (QRL-01/QRL-02) and the copied pre-check-in links (QRL-05/QRL-06) must be **absolute** URLs (including scheme and host, e.g. `https://app.example.com/checkin?token=...`), not the app-relative paths (`/checkin?token=...`, `/precheckin`) used internally by today's `<a href>`/`<Link>` elements. This is a required, testable behavior, not a cosmetic detail: a QR code is scanned by a phone camera outside any browser tab, and a copied link is typically pasted into a separate app (e.g. WhatsApp) — a relative path resolves incorrectly (or not at all) in both of those contexts, unlike today's in-app `<a href="/checkin?...">`, which only ever worked because the browser resolved it against the already-loaded app's own origin.

- The origin is derived from the browser's own current location (e.g. `window.location.origin`) at generation/copy time — no new configuration value or environment variable is introduced for this.

### QRL-04 — Dedicated print page

A dedicated, printable page/route exists, reachable only from the QR modal (QRL-01's print control), that renders:

- The event's or series' title.
- A large QR code image encoding the same absolute check-in URL as the modal (QRL-03).
- Formatting suitable for printing on A4 paper (e.g. print-oriented CSS such as `@media print` rules or equivalent, sized so the QR code is legible and scannable at typical wall-posting viewing/scanning distance once printed).

The exact route path/naming and whether it is implemented as one shared parameterized route or two separate routes (Events vs. Event Series) is a technical decision left to `tech-analyst`; this criterion states the required content and print-formatting behavior, not the URL shape. The page requires the admin to already be authenticated (consistent with every other admin-facing page in this app — this is not a new public route), and triggers the browser's native print dialog (e.g. via `window.print()`) either automatically on load or via an explicit "Print" button on the page itself — exact trigger mechanism left to `tech-analyst`, but the page must not require the admin to manually navigate the browser's own print menu to discover printing is possible (an on-page affordance or auto-trigger is required).

### QRL-05 — Print page reachable from the QR modal

The QR modal (QRL-01) contains an explicit control (e.g. a "Print" / "Imprimir" button or link) that opens the print page (QRL-04) for the same event/series currently shown in the modal — opening in a new tab is acceptable so the admin does not lose the modal's context.

### QRL-06 — Generic pre-check-in link copy button (Events page)

The Events page (`EventsPage.tsx`) gains a single copy-to-clipboard control, placed in the page's header/toolbar area (not per-row — it is not tied to any specific event), that copies the absolute URL `{origin}/precheckin` (no `event_id` — the student selects their event on the pre-check-in page itself, per today's existing `PreCheckInPage.tsx` behavior when no `event_id` query param is present).

### QRL-07 — Per-event pre-check-in link copy button (Events table)

Each row of the Events table gains a copy-to-clipboard control (alongside the existing edit/delete/QR/roster controls) that copies the absolute URL `{origin}/precheckin?event_id={event.id}`. This control exists only on the Events page/table — the Event Series page/table does not get an equivalent per-series control, since pre-check-in is always scoped to one concrete `Event` occurrence, never to a series as a whole.

### QRL-08 — Clipboard copy feedback

Every copy-to-clipboard action introduced by this feature (QRL-06, QRL-07) gives the admin visible feedback using the app's existing toast mechanism (`showToast` from `dojo-app/frontend/src/components/Toast.tsx`):

- On success: a brief success toast (e.g. "Link copiado").
- On failure (e.g. the browser denies clipboard permission, or `navigator.clipboard` is unavailable in the current context): a brief error toast (e.g. "Não foi possível copiar o link") — the failure must be caught and surfaced, never left as an unhandled promise rejection or a silent no-op.

### QRL-09 — Defensive behavior when `check_in_token` is missing or empty

`check_in_token` is a required, always-populated field on every `Event` and `EventSeries` row created through the existing backend today (confirmed in Context above), so this is a defensive guard against unexpected data, not an expected everyday case. If an event or series somehow has a falsy (`null`/empty-string) `check_in_token` at the moment the admin opens its QR modal (QRL-01) or clicks its copy-link control (QRL-07), the UI must not crash (no unhandled exception, no blank/broken QR render) — it must instead show a clear inline message that a check-in link/QR is unavailable for that item, in place of the QR image or in place of performing the copy action.

### QRL-10 — Modal responsive behavior

The QR modal (QRL-01) is usable on both desktop and narrow/mobile viewport widths, consistent with this app's existing responsive modal patterns already in use elsewhere (e.g. `EventsPage.tsx`'s roster modal, `ContractTemplatesPage.tsx`'s view modal) — the QR image and its title/print control remain fully visible and usable without horizontal overflow or requiring the admin to resize their browser window.

## Explicit Non-Goals

- Any new backend endpoint, schema field, or database change. `check_in_token` and `GET /api/v1/pre-checkins/events` already exist and are already exposed; this feature is frontend-only.
- Server-side QR image generation (e.g. a backend endpoint that returns a QR PNG). QR generation happens entirely client-side, per the locked-in decision.
- A per-series pre-check-in copy-link control on the Event Series page/table (QRL-07 explicitly scopes this to Events only — see rationale there).
- Any change to `CheckInPage.tsx`'s or `PreCheckInPage.tsx`'s existing check-in/pre-check-in confirmation logic — this feature only changes how their URLs are surfaced/shared (via QR image and copy button) and how the existing QR icon behaves (modal instead of direct navigation), not what those destination pages do once reached.
- QR-code customization (colors, logo embedding, error-correction level as an admin-configurable setting) — a plain, scannable, legible QR is sufficient; no styling options are exposed to the admin.
- Rotating, regenerating, or expiring `check_in_token`s — token lifecycle is unchanged and out of scope for this feature.
- Any offline/PWA-style "works without internet" consideration for the print page or QR modal — this app has no such precedent today and none is introduced here.

## Constraints

- Frontend-only change; no backend code, schema, or endpoint is touched by this feature.
- QR generation must happen client-side, in the browser, from data already present on the `Event`/`EventSeries` objects the frontend already fetches — no new API call is introduced to generate or fetch a QR image.
- Any new frontend dependency (QR library) must be small and directly justified by this feature's narrow scope — mirrors this repo's existing precedent of preferring lightweight dependencies for narrowly-scoped features (see `.workflow/runs/contract-markdown-rendering/requirements.md`'s CTM-09).
- All URLs encoded into a QR code or copied to the clipboard must be absolute (QRL-03) — this is a correctness requirement, not a style preference, since both artifacts are consumed outside the app's own browser tab.
- Clipboard-copy failures must be caught and surfaced to the admin (QRL-08) — never a silent failure or an unhandled promise rejection.
- Per `CLAUDE.md`'s repository-wide testing mandate, every QRL-0X criterion above must be covered by automated tests: Jest unit/component tests for the QR modal (both Events and Event Series variants, including the missing-token defensive path, QRL-09), the print page's content and print-trigger behavior, the copy-link buttons' clipboard-invocation and absolute-URL construction (QRL-03, mockable via `navigator.clipboard`), and the toast feedback on both success and simulated clipboard-denial paths (QRL-08); Cypress end-to-end coverage for the full admin flow (open QR modal from the Events table and the Event Series table, open the print page from the modal, click both copy-link buttons and assert the expected clipboard content). Exact test file/case breakdown is left to `tech-analyst`'s implementation plan.

## Open Questions

None blocking. The two items the task explicitly flagged as worth surfacing are resolved directly in this document rather than left open: absolute-vs-relative URL handling is a required behavior (QRL-03), and clipboard-permission-denial / missing-token behavior are each required, testable criteria (QRL-08, QRL-09) rather than unspecified edge cases. Two narrow items remain genuinely left to `tech-analyst`, but neither is product-ambiguous — they are implementation choices explicitly deferred in the criteria that mention them:

- Exact client-side QR-generation library (QRL-02) — constrained (lightweight, no backend involvement) but not named.
- Exact print-page route naming/shape, one shared route vs. two (QRL-04) — constrained (content and print-formatting behavior) but not named.

If `tech-analyst` surfaces a genuine scope-changing ambiguity while designing against this document, route it back to the user at that point rather than treating any of the above as re-litigable without cause.

## Next Agent

Next Agent: requirements-reviewer
