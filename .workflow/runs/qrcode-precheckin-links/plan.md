# Technical Plan — Real QR Codes for Check-In + Shareable Pre-Check-In Links (QRL)

## Status

Architecture approved (self-reviewed — see Autocrítica below). Frontend-only change against `dojo-app/frontend`. No backend files are touched. Requirements source: `.workflow/runs/qrcode-precheckin-links/requirements.md` (QRL-01–QRL-10, approved). Review follow-ups source: `.workflow/runs/qrcode-precheckin-links/review-requirements.md` (Findings #1–#4, all non-blocking) — all four are folded into this design directly, as instructed; see "Follow-ups folded in" below.

## Ground truth re-verified before designing

- `EventsPage.tsx:415-423` and `EventSeriesPage.tsx:473-481` — today's QR affordance is `<a href="/checkin?token=${...}" target="_blank" rel="noopener noreferrer">` wrapping a lucide `QrCode` icon. `EventsPage.tsx` has **no existing Jest test file** (`EventsPage.test.tsx` does not exist — confirmed via glob). `EventSeriesPage.test.tsx:151-159` **does** have a test that asserts the current anchor-link behavior for the QR icon (`renders a plain anchor link to /checkin?token=... for the QR action`) — this test must be replaced, not just supplemented, since the behavior it asserts is being removed.
- `EventsPage.tsx` roster modal (`rosterEvent`) is actually an inline panel (`PreCheckInRosterPanel`, not an overlay), not a true modal. The real "overlay modal" precedent in this codebase is `ContractTemplatesPage.tsx`'s `viewVersion` state (lines 32, 222-245): `fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4` backdrop, `bg-white rounded-lg shadow-xl max-w-2xl w-full p-6` panel, explicit "Fechar" button only (no backdrop-click-to-close implemented there). This plan's `QrCodeModal` mirrors that exact pattern for consistency and to avoid inventing new interaction affordances.
- `Toast.tsx` — `showToast(message, type)` singleton, no per-call config needed. Already used via `jest.mock('../components/Toast', () => ({ showToast: jest.fn() }))` in `EventSeriesPage.test.tsx` — same mock will be reused.
- `App.tsx` — `/events` and `/event-series` are both wrapped in `PrivateRoute` (any authenticated user), not `AdminRoute` (admin-only). The new print route must use the same `PrivateRoute` tier, not `AdminRoute`, to match the access level of the pages it's reached from.
- `package.json` — no QR library, no `navigator.clipboard` usage, no print CSS anywhere today (confirmed).
- Cypress: `events.cy.ts` has a pre-existing test `'deve gerar QR Code para evento'` (lines 285-319) that intercepts a **nonexistent** backend endpoint `GET /api/v1/events/*/qr-code` and clicks something matching `/qr|code/i`. This endpoint does not exist anywhere in `dojo-app/backend` (grepped, zero API route matches) — this test is already stale/aspirational against a backend flow that was never built, and is unrelated to this feature's actual (client-side-only, no-network) QR design. It must be replaced, not left in place, since after this change clicking the QR icon opens a modal with **no** network call at all, so `cy.wait('@getQR')` would hang/timeout regardless of what the icon-click selector matches.

## Follow-ups folded in (from review-requirements.md)

1. **QRL-10 → Cypress, not Jest.** Assigned explicitly below to a dedicated Cypress viewport check (`cy.viewport(375, 667)` + `scrollWidth`/`clientWidth` assertion). Not attempted in Jest/jsdom.
2. **QRL-04 print size → pinned concrete value.** The print page renders the QR inside a container sized `12cm x 12cm` on the printed page (Tailwind arbitrary-value utility `print:w-[12cm] print:h-[12cm]`), using an SVG-rendered QR so there is no pixelation at any size (see library rationale). `12cm` square on A4 (21cm x 29.7cm) is comfortably legible/scannable at normal wall-posting distance and leaves generous margin. This is a concrete, assertable value (Jest can assert the class string is present).
3. **QRL-05 → new tab is firm, not optional.** The modal's print control is implemented as `<a href={printUrl} target="_blank" rel="noopener noreferrer">`, mirroring the exact `target="_blank" rel="noopener noreferrer"` convention already used by today's QR-icon anchor. Cypress asserts the `target="_blank"` attribute directly (see Test Plan).
4. **QRL-09 → extended to direct/stale-URL access of the print page.** `CheckInPrintPage` independently re-checks its own `token` search param (not just trusting the modal that linked to it) and renders the same inline "unavailable" message with no QR/print button if `token` is falsy — covering a stale bookmark, restored tab, or hand-edited URL, per Finding #4.

## One wording clarification resolved directly (non-blocking, no product ambiguity)

QRL-09's text says the defensive guard applies when the admin "opens its QR modal (QRL-01) **or** clicks its copy-link control (QRL-07)". Re-checked against QRL-07's own definition: QRL-07's copy button copies `{origin}/precheckin?event_id={event.id}` — this is built from `event.id` (the row's own primary key, always present, `NOT NULL` by construction, never a defensive case) and **never reads `check_in_token`** at all. Only the QR modal (QRL-01) and the print page it links to (QRL-04/05) actually read `check_in_token`. So the guard is implemented on the QR modal and the print page only; the per-event pre-check-in copy button (QRL-07) has no missing-token failure mode to guard against in the first place, since it never touches that field. This is a factual/structural clarification, not a scope change — flagging it here for visibility rather than re-litigating with product-manager/requirements-reviewer, per the handoff instruction to only route back for genuine scope-changing ambiguity.

## QR library decision (QRL-02)

**Chosen: `qrcode.react` `^4.2.0`** (latest published version, confirmed via `npm view qrcode.react version` → `4.2.0`; zero runtime dependencies; peer dep `react: ^16.8.0 || ^17.0.0 || ^18.0.0 || ^19.0.0`, compatible with this repo's React 19).

Rationale, against this repo's existing lightweight-dependency precedent (CTM-09 in `contract-markdown-rendering/requirements.md`: "prefer a lightweight solution given the deliberately small scope"):

- **Zero non-React runtime dependencies** (verified via `npm view qrcode.react dependencies` → empty). Unpacked package size ~112KB (mostly type declarations + docs); actual bundled JS contribution is a few KB gzipped — a proportionate cost for a feature whose entire job is "render a QR code."
- **Renders real SVG** (`QRCodeSVG` export), not canvas/raster. This directly satisfies QRL-02's "vector/SVG-based render... not visibly pixelate" clause without any resolution tuning: the same SVG element scales cleanly from the modal's 240px on-screen size up to the print page's 12cm print size, because SVG is resolution-independent by construction.
- **jsdom compatibility, concretely, not just plausibly:** this repo's Jest config (`jest.config.cjs`) uses `testEnvironment: 'jsdom'`, which has no `HTMLCanvasElement.getContext` implementation. A canvas/raster-based QR library (e.g. the `qrcode` npm package's default canvas renderer, or `qrcode.react`'s own `QRCodeCanvas` alternate export) would throw or silently no-op under Jest without an additional `canvas` native-binding devDependency (a real, avoidable complexity/dependency-weight cost). `QRCodeSVG` sidesteps this entirely — it's plain DOM/SVG, renders correctly under jsdom with no extra devDependency.
- **React-idiomatic API** (`<QRCodeSVG value={url} size={240} />`), fitting directly into `QrCodeModal`/`CheckInPrintPage` as JSX rather than requiring imperative canvas-drawing glue code — less code, less surface area to test, consistent with "avoid overengineering."
- Rejected alternative: the `qrcode` npm package (no React wrapper, canvas/SVG/data-URL string API) — viable but would require either (a) writing our own thin SVG-string-to-`dangerouslySetInnerHTML` wrapper (extra code, extra XSS-shaped surface even though the input is our own trusted URL) or (b) using its canvas API and hitting the same jsdom gap above. `qrcode.react` avoids both with an equally small footprint.

**Add to `dojo-app/frontend/package.json` dependencies:** `"qrcode.react": "^4.2.0"`.

## Component architecture

### New: `dojo-app/frontend/src/utils/url.ts`

Pure functions, no React/DOM dependency beyond `window.location.origin` (satisfies QRL-03's "no new config value" requirement — origin is read live, never stored).

```ts
export function toAbsoluteUrl(pathWithQuery: string): string {
  return `${window.location.origin}${pathWithQuery}`
}

export function buildCheckInUrl(token: string): string {
  return toAbsoluteUrl(`/checkin?token=${encodeURIComponent(token)}`)
}

export function buildCheckInPrintUrl(token: string, title: string): string {
  return toAbsoluteUrl(
    `/checkin-print?token=${encodeURIComponent(token)}&title=${encodeURIComponent(title)}`
  )
}

export function buildPreCheckInUrl(eventId?: string): string {
  return eventId
    ? toAbsoluteUrl(`/precheckin?event_id=${encodeURIComponent(eventId)}`)
    : toAbsoluteUrl('/precheckin')
}
```

This is the single place QRL-03's absolute-URL requirement is implemented; every call site (`QrCodeModal`, `CheckInPrintPage`, both copy buttons) imports from here rather than re-deriving `window.location.origin` locally, so there is exactly one thing to get right and test.

### New: `dojo-app/frontend/src/utils/clipboard.ts`

```ts
import { showToast } from '../components/Toast'

export async function copyToClipboardWithToast(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    showToast('Link copiado', 'success')
  } catch {
    showToast('Não foi possível copiar o link', 'error')
  }
}
```

Single reusable implementation of QRL-08 (both the generic and per-event copy buttons call this directly — no duplicated try/catch/toast logic at either call site). The `catch` has no parameter and does nothing but call `showToast` — deliberately not logging or rethrowing, since QRL-08's only requirement is that the failure is caught and surfaced to the admin via toast, not diagnosed further; adding more here would be defensive-programming for its own sake.

### New: `dojo-app/frontend/src/components/QrCodeModal.tsx`

Shared between `EventsPage.tsx` and `EventSeriesPage.tsx`. Follows `ContractTemplatesPage.tsx`'s `viewVersion` overlay pattern exactly (backdrop + panel + explicit close button, no backdrop-click-to-close, matching existing precedent rather than adding a second, untested interaction path).

```tsx
import { X } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { buildCheckInUrl, buildCheckInPrintUrl } from '../utils/url'

interface QrCodeModalProps {
  title: string
  token: string | null | undefined
  onClose: () => void
}

export default function QrCodeModal({ title, token, onClose }: QrCodeModalProps) {
  const hasToken = Boolean(token)

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="rounded p-1 text-slate-500 hover:bg-gray-100 hover:text-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {hasToken ? (
          <>
            <div
              role="img"
              aria-label={`QR code de check-in: ${title}`}
              className="flex justify-center py-4"
            >
              <QRCodeSVG value={buildCheckInUrl(token as string)} size={240} />
            </div>
            <a
              href={buildCheckInPrintUrl(token as string, title)}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Imprimir
            </a>
          </>
        ) : (
          <p className="py-4 text-sm text-rose-700">
            Link de check-in indisponível para este item.
          </p>
        )}
      </div>
    </div>
  )
}
```

`w-full max-w-sm p-4/p-6` on a flex-centered, viewport-covering backdrop is the same responsive shape already relied on by `ContractTemplatesPage`'s modal (`max-w-2xl w-full p-6` inside a `p-4` backdrop) — narrower `max-w-sm` here since QR-modal content (title + one square image + one button) is inherently narrower than a contract-body modal. No fixed pixel widths anywhere, so it naturally reflows at mobile widths without horizontal overflow (QRL-10 — asserted concretely in Cypress, see Test Plan; not claimed via Jest, per Follow-up #1).

### New: `dojo-app/frontend/src/pages/CheckInPrintPage.tsx`

Route: **`/checkin-print`**, one shared parameterized route reading `?token=` and `?title=` from its own query string — **not** two separate routes for Event vs. EventSeries.

Rationale for one shared route over two: the print page's job is identical regardless of whether the token came from an `Event` or an `EventSeries` — render a title and a QR encoding a check-in URL, formatted for A4. Neither the route nor the component needs to know or care which kind of record it came from; splitting into `/events/checkin-print` and `/event-series/checkin-print` would duplicate the entire print layout for zero behavioral difference, which is exactly the kind of unjustified complexity the "avoid overengineering" instruction rules out. Passing `token` + `title` via query params (rather than re-fetching the event/series by id) also means the print page makes **no new API call** — it only ever needs data the modal already has in memory, consistent with QRL-02's "no network request" framing extended sensibly to the print page too, and avoids a second source of truth that could show a different title than the modal the admin just saw.

```tsx
import { useSearchParams } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { buildCheckInUrl } from '../utils/url'

export default function CheckInPrintPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const title = searchParams.get('title') ?? ''
  const hasToken = Boolean(token)

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-white p-8 print:p-0">
      {hasToken ? (
        <>
          <h1 className="text-center text-2xl font-bold text-gray-900">{title}</h1>
          <div
            role="img"
            aria-label={`QR code de check-in: ${title}`}
            className="flex h-[300px] w-[300px] items-center justify-center print:h-[12cm] print:w-[12cm]"
          >
            <QRCodeSVG value={buildCheckInUrl(token as string)} size={300} className="h-full w-full" />
          </div>
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 print:hidden"
          >
            Imprimir
          </button>
        </>
      ) : (
        <p className="text-center text-rose-700">
          Link de check-in indisponível para este item.
        </p>
      )}
    </main>
  )
}
```

**Print trigger:** explicit on-page "Imprimir" button calling `window.print()`, not auto-trigger on mount. Justification: QRL-04 explicitly leaves this choice open ("either automatically on load or via an explicit... button"). An explicit button is simpler to reason about and test deterministically — `window.print()` opens an OS-native, non-scriptable dialog that cannot be reliably driven or dismissed inside Cypress; an explicit button lets both Jest (`jest.spyOn(window, 'print')`) and Cypress (`cy.stub(win, 'print')` set up **before** `cy.visit`, then a plain click) assert the trigger deterministically without the dialog ever actually opening in the test run. Auto-triggering on mount would make every automated visit to this route pop a real print dialog, which is worse for both test reliability and for an admin who opens the print page just to preview it before deciding to print.

**Tailwind print utilities**, not a new CSS file: `print:hidden` (hides the button when actually printing) and the arbitrary-value `print:w-[12cm] print:h-[12cm]` (pins the printed QR to a concrete, assertable size — Follow-up #2) are both native Tailwind `print:` variant utilities, already available with zero config changes (Tailwind ships the `print` variant by default). This avoids introducing a new global stylesheet/`@media print` block for a two-rule need — consistent with this repo's all-Tailwind styling convention elsewhere.

**Auth guard:** registered in `App.tsx` under `PrivateRoute` (same tier as `/events`/`/event-series`, not `AdminRoute`) — any authenticated admin/instructor who can already reach the Events or Event Series page can also reach this page, matching QRL-04's "requires the admin to already be authenticated... same as every other admin-facing page."

**Missing/invalid token (Follow-up #4):** handled identically whether reached via the modal's print link or a direct/stale URL — the component itself checks `searchParams.get('token')`, not a prop passed down from a parent that trusts the link was well-formed. There is no code path that reaches this component with a "trusted" token; it always re-derives from the URL itself, so the direct-access case and the modal-link case are the same code path, not two.

### Modified: `dojo-app/frontend/src/pages/EventsPage.tsx`

- Add `qrItem` state: `const [qrItem, setQrItem] = useState<{ title: string; token: string } | null>(null)`.
- Replace the `<a href="/checkin?token=...">` QR icon (lines 415-423) with `<button type="button" onClick={() => setQrItem({ title: event.title, token: event.check_in_token })} title="Ver QR code de check-in"><QrCode className="w-4 h-4" /></button>`, keeping the same `QrCode` icon and the same visual slot in the row.
- Add a per-row copy-link button (QRL-07) immediately after the QR button, before the roster (`Users`) button: `<button type="button" onClick={() => copyToClipboardWithToast(buildPreCheckInUrl(event.id))} title="Copiar link de pré-check-in" aria-label={\`Copiar link de pré-check-in de ${event.title}\`}><Copy className="w-4 h-4" /></button>` (new `Copy` icon import from `lucide-react`).
- Add a generic toolbar copy-link button (QRL-06) in the header row, next to "Novo Evento": secondary-style button (`border border-gray-300 text-gray-700 ... hover:bg-gray-50`, matching the existing "Cancelar" button style elsewhere in this file) with `Copy` icon + label "Copiar link de pré-check-in", `onClick={() => copyToClipboardWithToast(buildPreCheckInUrl())}`.
- Render `{qrItem && <QrCodeModal title={qrItem.title} token={qrItem.token} onClose={() => setQrItem(null)} />}` at the end of the component's JSX (same position `ContractTemplatesPage` renders its `viewVersion` modal — after the table's closing `</div>`).
- New imports: `Copy` from `lucide-react`; `showToast` no longer needed directly here (it's inside `copyToClipboardWithToast`); `QrCodeModal` from `../components/QrCodeModal`; `buildPreCheckInUrl` from `../utils/url`; `copyToClipboardWithToast` from `../utils/clipboard`.

### Modified: `dojo-app/frontend/src/pages/EventSeriesPage.tsx`

- Same `qrItem` state and same QR-icon → modal-button replacement as `EventsPage.tsx`, using `series.title` / `series.check_in_token`.
- **No copy-link button added** — explicit non-goal, series never gets a per-series pre-check-in control (QRL-07's own scoping, re-affirmed in Explicit Non-Goals).
- Render `{qrItem && <QrCodeModal ... />}` at the end of the component's JSX, same as `EventsPage.tsx`.

### Modified: `dojo-app/frontend/src/App.tsx`

Add one route:

```tsx
<Route
  path="/checkin-print"
  element={
    <PrivateRoute>
      <CheckInPrintPage />
    </PrivateRoute>
  }
/>
```

Plus the corresponding `import CheckInPrintPage from './pages/CheckInPrintPage'`.

### Modified: `dojo-app/frontend/package.json`

Add `"qrcode.react": "^4.2.0"` to `dependencies`.

## Test plan — mapped to each QRL criterion

Jest tests use the same mocking conventions already established in this repo: `jest.mock('../services/api', ...)` for API calls, `jest.mock('../components/Toast', () => ({ showToast: jest.fn() }))` for toast assertions (as in `EventSeriesPage.test.tsx`), and — new for this feature — `jest.mock('qrcode.react', () => ({ QRCodeSVG: ({ value }: { value: string }) => <div data-testid="qr-svg" data-value={value} /> }))` in test files that need to assert the exact encoded URL. This mirrors the existing `jest.mock('react-markdown', ...)` stub-component pattern in `ContractTemplatesPage.test.tsx` — same technique (swap a rendering library for a cheap, assertable stub), same reason (assert on the *input* to the render, not try to parse the rendered output back out).

### New: `dojo-app/frontend/src/utils/url.test.ts`
- `buildCheckInUrl` returns `{origin}/checkin?token=...` with the token URL-encoded (QRL-03).
- `buildCheckInPrintUrl` returns `{origin}/checkin-print?token=...&title=...` with both URL-encoded (QRL-03, QRL-04).
- `buildPreCheckInUrl()` (no arg) returns `{origin}/precheckin` exactly, no query string (QRL-06).
- `buildPreCheckInUrl(eventId)` returns `{origin}/precheckin?event_id=...` (QRL-07).
- Assert none of these read anything except `window.location.origin` — no new env var / config lookup (QRL-03's explicit constraint).

### New: `dojo-app/frontend/src/utils/clipboard.test.ts`
- Success path: `navigator.clipboard.writeText` mocked to resolve → `showToast` called with `('Link copiado', 'success')` (QRL-08).
- Failure path: `navigator.clipboard.writeText` mocked to reject → `showToast` called with `('Não foi possível copiar o link', 'error')`, and the returned promise from `copyToClipboardWithToast` itself resolves (never rejects) — asserting no unhandled rejection reaches the caller (QRL-08's explicit "never a silent no-op / unhandled rejection" requirement).

### New: `dojo-app/frontend/src/components/QrCodeModal.test.tsx`
- Renders the given title and a QR element whose encoded `value` equals `buildCheckInUrl(token)` for a non-empty token (QRL-01, QRL-02, QRL-03).
- Print link (`<a>`) has `href` equal to `buildCheckInPrintUrl(token, title)`, `target="_blank"`, `rel="noopener noreferrer"` (QRL-04, QRL-05, Follow-up #3).
- Close button calls `onClose` (QRL-01).
- With a falsy `token` (`''` and `null` cases): no QR element rendered, no print link rendered, inline "indisponível" message shown instead, and the component does not throw (QRL-09).

### New: `dojo-app/frontend/src/pages/CheckInPrintPage.test.tsx`
(Render with a `MemoryRouter` + `initialEntries` to control the query string, matching how other page tests wrap `QueryClientProvider`/`AuthProvider`.)
- With `?token=abc&title=Aula` present: renders the title, a QR element with the expected encoded value, and an "Imprimir" button whose container carries the `print:w-[12cm] print:h-[12cm]` sizing classes (QRL-04, Follow-up #2).
- Clicking "Imprimir" calls `window.print()` (spied via `jest.spyOn(window, 'print').mockImplementation(() => {})`) (QRL-04's print-trigger requirement).
- With `token` missing from the query string: renders the inline "indisponível" message, no QR, no "Imprimir" button, no crash (QRL-09 / Follow-up #4 — direct/stale-URL access).

### New: `dojo-app/frontend/src/pages/EventsPage.test.tsx`
(This file does not exist yet — created fresh by this feature, following `EventSeriesPage.test.tsx`'s structure: mock `../services/api` and `../components/Toast`, a `fakeToken` JWT helper, a `renderPage()` wrapper with `QueryClientProvider` + `AuthProvider`.)
- Clicking the QR icon on an event row opens `QrCodeModal` showing that event's title (QRL-01) — integration-level only; modal internals already covered by `QrCodeModal.test.tsx`.
- Clicking the toolbar's generic copy-link button calls `navigator.clipboard.writeText` (mocked on `navigator.clipboard`) with `{origin}/precheckin` and triggers the success toast (QRL-06, QRL-08 wiring).
- Clicking a row's per-event copy-link button calls `navigator.clipboard.writeText` with `{origin}/precheckin?event_id={that event's id}` (QRL-07).
- One clipboard-denial case (`navigator.clipboard.writeText` mocked to reject) asserts the error toast fires from a button click (QRL-08 wiring; the exhaustive success/failure-branch coverage itself lives in `clipboard.test.ts`, this is a thin "the button is wired to the shared function" check, avoiding duplicating branch coverage per call site).

### Modified: `dojo-app/frontend/src/pages/EventSeriesPage.test.tsx`
- **Replace** the existing test `'renders a plain anchor link to /checkin?token=... for the QR action'` (lines 151-159) — that behavior no longer exists after this change — with a test asserting the QR icon now opens `QrCodeModal` with the series' title (QRL-01), mirroring the equivalent `EventsPage.test.tsx` test.
- Add one test rendering a series with `check_in_token: ''` and asserting the modal shows the inline "indisponível" message when opened (QRL-09), closing the loop end-to-end for the series variant without re-testing `QrCodeModal`'s internals a second time.

### New: `dojo-app/frontend/cypress/e2e/qrcode-precheckin.cy.ts`
New dedicated spec file (mirrors this repo's existing convention of one feature-scoped file per area, e.g. `precheckin.cy.ts`, rather than growing `events.cy.ts`/`event-series.cy.ts` further):
- Log in, navigate to Events, click an event row's QR icon → modal opens showing the event's title and a rendered QR image (QRL-01).
- Log in, navigate to Event Series, click a series row's QR icon → modal opens showing the series' title and a rendered QR image (QRL-01, series variant).
- From an open QR modal, assert the print control is an `<a>` with `target="_blank"` and an `href` matching `/checkin-print?token=...`, then separately `cy.visit()` that `href` directly (Cypress cannot drive a second real browser tab; asserting `target="_blank"` on the anchor plus independently visiting its `href` is the concrete technique that jointly proves "opens the print page" and "would do so in a new tab" without needing an actual second tab) — assert the print page renders the title and QR (QRL-04, QRL-05, Follow-up #3).
- On the visited print page, stub `window.print` **before** the click (`cy.window().then((win) => cy.stub(win, 'print').as('printStub'))`), click "Imprimir", assert the stub was called (QRL-04's print-trigger requirement, exercised end-to-end).
- Stub `navigator.clipboard.writeText` on the Events page (`cy.window().then((win) => cy.stub(win.navigator.clipboard, 'writeText').as('copyStub'))`), click the toolbar's generic copy button, assert the stub was called with the bare `/precheckin` absolute URL and that the success toast text is visible (QRL-06, QRL-08).
- Same stub, click a row's per-event copy button, assert the stub was called with `/precheckin?event_id={id}` (QRL-07).
- **QRL-10 (Follow-up #1):** `cy.viewport(375, 667)`, open the QR modal on the Events page, assert the title, QR image, and "Imprimir" link are all `.should('be.visible')`, and assert `cy.document().then((doc) => expect(doc.documentElement.scrollWidth).to.be.at.most(doc.documentElement.clientWidth))` (no horizontal overflow introduced at mobile width). Repeat the same check for the Event Series page's modal.

### Modified: `dojo-app/frontend/cypress/e2e/events.cy.ts`
- **Replace** the stale `'deve gerar QR Code para evento'` test (lines 285-319, which intercepts a nonexistent `GET /api/v1/events/*/qr-code` backend endpoint) — remove it entirely; its intended coverage ("QR code for an event") is now correctly covered by the new `qrcode-precheckin.cy.ts` spec, which reflects the feature's actual (client-side, no-network) design instead of a network call that was never implemented.

## File-by-file change list

| File | Change |
|---|---|
| `dojo-app/frontend/package.json` | Add `qrcode.react: ^4.2.0` dependency. |
| `dojo-app/frontend/src/utils/url.ts` | **New.** `toAbsoluteUrl`, `buildCheckInUrl`, `buildCheckInPrintUrl`, `buildPreCheckInUrl`. |
| `dojo-app/frontend/src/utils/url.test.ts` | **New.** Unit tests for the above (QRL-03). |
| `dojo-app/frontend/src/utils/clipboard.ts` | **New.** `copyToClipboardWithToast` (QRL-08). |
| `dojo-app/frontend/src/utils/clipboard.test.ts` | **New.** Success/failure-path unit tests (QRL-08). |
| `dojo-app/frontend/src/components/QrCodeModal.tsx` | **New.** Shared modal (QRL-01, QRL-02, QRL-04's print link, QRL-09). |
| `dojo-app/frontend/src/components/QrCodeModal.test.tsx` | **New.** Component tests (QRL-01, 02, 03, 04, 05, 09). |
| `dojo-app/frontend/src/pages/CheckInPrintPage.tsx` | **New.** Print route (QRL-04, QRL-09/Follow-up #4). |
| `dojo-app/frontend/src/pages/CheckInPrintPage.test.tsx` | **New.** Component tests (QRL-04, QRL-09). |
| `dojo-app/frontend/src/pages/EventsPage.tsx` | Modify: QR icon → modal button; add per-row copy button (QRL-07); add toolbar copy button (QRL-06); render `QrCodeModal`. |
| `dojo-app/frontend/src/pages/EventsPage.test.tsx` | **New.** First Jest coverage for this page (QRL-01, 06, 07, 08 wiring). |
| `dojo-app/frontend/src/pages/EventSeriesPage.tsx` | Modify: QR icon → modal button; render `QrCodeModal`. No copy button added. |
| `dojo-app/frontend/src/pages/EventSeriesPage.test.tsx` | Modify: replace the stale anchor-link QR test; add falsy-token modal test (QRL-01, QRL-09). |
| `dojo-app/frontend/src/App.tsx` | Add `/checkin-print` route under `PrivateRoute`, import `CheckInPrintPage`. |
| `dojo-app/frontend/cypress/e2e/qrcode-precheckin.cy.ts` | **New.** Full e2e flow (QRL-01, 04, 05, 06, 07, 08, 10). |
| `dojo-app/frontend/cypress/e2e/events.cy.ts` | Modify: remove the stale `'deve gerar QR Code para evento'` test against a nonexistent backend endpoint. |

No backend file is touched. No file under `dojo-app/backend` appears in this list, by design.

## Risk assessment

- **Low risk overall** — this is a small, additive, frontend-only, no-new-network-call feature built entirely on data already fetched by existing queries. The main risks are test-authoring risks, not architectural ones:
  - Mocking `qrcode.react` in Jest must be done per-test-file (not globally in `setupTests.ts`), since some tests may want the real SVG render (e.g. to assert `role="img"` presence) while value-assertion tests want the stub. Mitigation: default to real rendering (no mock) except in the specific test files listed above that need to assert the exact encoded `value`.
  - Cypress cannot open or interact with a second real browser tab; the plan's `qrcode-precheckin.cy.ts` approach (assert `target="_blank"` + independently `cy.visit()` the same `href`) is a standard, well-understood Cypress workaround, not a novel technique, but it is worth calling out explicitly so whoever implements the spec doesn't attempt (and fail) to literally drive a second tab.
  - `window.print()` stubbing must happen via `cy.window().then(...)` **before** the click that triggers it, or the stub attaches too late and the real print dialog opens, likely hanging the Cypress run. Called out explicitly in the test plan above for this reason.
- **No open technical questions remain for the user.** Both items the requirements document explicitly deferred to `tech-analyst` (QR library choice, print-route shape) are resolved above with concrete rationale. The one wording inconsistency found (QRL-09 vs. QRL-07, see "One wording clarification resolved directly") is resolved on the codebase's own facts (QRL-07 never reads `check_in_token`), not a product-level ambiguity, so it is not routed back to `product-manager`/`requirements-reviewer`.

## Autocrítica (self-review)

- **Does it satisfy all acceptance criteria?** QRL-01 through QRL-10 are each traced to a specific component/behavior/test above. QRL-09's scope note (guard applies to QR modal + print page, not QRL-07) is a factual correction based on what QRL-07 actually reads, not a reduction of coverage — the *intent* of QRL-09 (never crash, never blank-render on bad data) is still fully honored everywhere `check_in_token` is actually consumed.
- **Are design patterns justified?** Every new abstraction (`QrCodeModal`, `url.ts`, `clipboard.ts`) is shared by at least two call sites (Events + Event Series pages for the modal; modal + print page + both copy buttons for the URL builders; both copy buttons for the clipboard helper) — none is a single-use wrapper introduced for its own sake. No new state-management library, no new global store, no new routing abstraction beyond one additional `<Route>` entry matching the existing flat list in `App.tsx`.
- **Is there unnecessary complexity?** Considered and rejected: two separate print routes (rejected — identical behavior, would duplicate layout code for zero benefit); backdrop-click-to-close on the modal (rejected — codebase's own existing overlay-modal precedent doesn't do this, adding it here would be inventing a new interaction pattern not asked for); auto-triggering `window.print()` on page load (rejected — worse testability, no criterion requires it, explicit button is simpler to reason about and control); a new global print stylesheet (rejected — two Tailwind `print:` utility classes are sufficient, no need for a new CSS file).
- **Is it testable and maintainable?** Every criterion has a concrete, named test (Jest and/or Cypress per the review's own layer guidance). The two new pure-function utility modules (`url.ts`, `clipboard.ts`) are trivially unit-testable in isolation from any component, and centralizing them means QRL-03 and QRL-08 each have exactly one implementation to verify rather than four scattered ones (one per call site).

## Next Agent

Next Agent: doc-writer (write ADR(s) for the QR library choice and the shared print-route decision; then issue-creator breaks this plan into implementation issues/tasks).
