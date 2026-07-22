# Requirements — Epic 2, Phase 3 (Financial Foundation, PR-3, FIN-01–FIN-07)

## Status

Draft for requirements-reviewer. Built on the epic-level policy already resolved on 2026-07-19 (`.workflow/epic-02/handoff.md` "Key Decisions"; `.workflow/runs/epic-02-plan/plan.md` "Finance (Phase 3)"). Those items are **settled inputs** and are not re-litigated below. This document breaks FIN-01–FIN-07 into concrete, testable requirements and separates them from a smaller set of **genuinely open decisions** that the settled policy list does not cover.

## Settled inputs (carried over, not re-decided here)

- Pricing: fixed plan catalog tiered by weekly class frequency, not a per-class dynamic rate.
- Billing cycle: monthly, one standardized due date for all students; proportional charge in the enrollment month.
- Overdue: flag-only in reports/dashboards; no automatic check-in block or access restriction in this epic.
- Partial/overpayment: accepted; tracked as a residual balance (owed or credit) applied to the next charge.
- Non-goals (epic-wide): no online payment processing, no email/SMS/push reminders (Epic 3), no multi-organization configuration UI (Epic 4).
- Cross-phase constraint: Phase 4 (Contracts) already commits to recording "which financial plan/version" a contract used. This means Phase 3's plan catalog must be a **versioned** entity, not an in-place-editable price list — this is treated as settled here, inherited from the Phase 4 decision, not re-opened.

## Existing anchors in the codebase (read 2026-07-20)

- `Student` (`dojo-app/backend/app/models/__init__.py`) already has `classes_per_week: int | None` (default 2) and `class_days: str | None` — both instructor-editable via the student form (`StudentsPage.tsx`) and already displayed as "N/sem (dias)". This is a **declared/contracted** value set by staff, not derived from attendance.
- `Attendance` records each physical check-in per `event_id`/`student_id`. There is no recurring-class-schedule entity — `Event` rows are individual scheduled instances, so "how many times a week a student trains" is not modeled anywhere as a stored, computed value today; it would have to be derived either from `classes_per_week` (declared) or from counting `Attendance` rows over a window (actual).
- No `Plan`, `Payment`, `Invoice`/`Mensalidade`, or any pricing/catalog table exists anywhere in the backend today (confirmed via search) — Phase 3 is greenfield for all financial data.
- `Document`/`MedicalExam` (Phase 2) already expose a per-student status (`valido`/`vencendo`/`vencido`/`sem_registro`) via `MedicalExamService.get_status`/`get_dashboard`. Phase 2 explicitly deferred "what Phase 3 does with this status" to this phase (see MED-04 note below).
- `Organization`/`Dojo` exist as multi-tenant scaffolding, but the epic's Non-Goals explicitly exclude multi-organization configuration UI. Recommendation below: keep the plan catalog single/global for this epic, consistent with that non-goal, rather than per-organization.

## Requirement-by-requirement breakdown

### FIN-01 — Sistema registra mensalidades de cada aluno

- **Actors:** System generates a monthly charge ("mensalidade") record per active student; instructor/admin can view a student's charge history. No student-facing view planned by default (see open decision D5).
- **Data:** `student_id`, reference month/year, due date, amount charged, the plan/version used to compute that amount, and a way to derive status (open/partial/paid/overdue — see open decision D4 on whether this is a stored field or computed on read).
- **Edge cases:**
  - Enrollment mid-month: proportional charge per settled policy. Exact proration formula is an open decision (D6).
  - Student deactivated (`is_active=False`) mid-cycle: no new mensalidade is generated for future months; existing unpaid ones are left as-is (not auto-cancelled). Flagged for confirmation, not blocking.
  - A student's plan/tier changes mid-month: not covered by settled policy (only enrollment-month proration was decided) — folded into D6.
- **Out of scope:** editing a mensalidade's historical amount after generation (corrections happen via a new payment/credit, not by mutating the charge); multi-organization pricing variance (see recommendation above); discounts or per-student price overrides (D10).

### FIN-02 — Sistema calcula valor da mensalidade baseado na frequência semanal

- Looks up the price for the student's weekly-frequency tier from the versioned plan catalog and uses it as the mensalidade amount (subject to enrollment/mid-cycle proration, D6).
- **Open decision:** which "frequência semanal" feeds this lookup — the declared `classes_per_week` field or a computed attendance frequency (D1, see below — this is the central open item in this phase).
- **Open decision:** whether "the versioned plan catalog" means a **live lookup** against the catalog's current price for the student's tier, or a **pinned assignment** to the specific plan/version the student was on at enrollment/last plan change (D11) — this changes what "the price" in this requirement actually refers to over a student's lifetime.
- **Redundancy note:** as literally written, FIN-02 and FIN-07 describe the same computation ("price for this student's plan tier"). See D2.

### FIN-03 — Sistema registra pagamentos realizados com data e valor

- **Actors:** instructor/admin manually records a payment (no online processing, per Non-Goals — the dojo takes cash/pix/transfer outside the system and staff logs it).
- **Data:** `student_id`, amount, payment date, optional method (informational only, not integrated with any payment processor), `recorded_by` (user).
- **Edge cases:**
  - Overpayment: excess becomes a credit balance applied to the next charge (settled).
  - Underpayment: remaining balance stays open/overdue on the same mensalidade.
  - Payment with no currently-open mensalidade (e.g., paying ahead): becomes credit, per settled policy.
  - **Open decision (D7):** when a payment doesn't fully cover the amount due and/or a student has multiple open mensalidades, which charge(s) does it apply against? No allocation rule is specified in FIN-0X or the settled policy.
  - **Open decision:** can a recorded payment be corrected/voided after entry (data-entry error)? Not mentioned in the raw requirements; recommend the same soft-correction/audit-trail pattern already used for documents (Phase 2), rather than hard delete. Flagged as a minor open item, not blocking.

### FIN-04 — Sistema alerta alunos com pagamentos em atraso

- Per the settled policy ("flag-only in reports/dashboards; no automatic check-in or access block"; epic Non-Goals exclude email/SMS/push), this is **not** a notification sent to the student. It is the computation that marks a mensalidade/student as overdue, consumed by FIN-05's list.
- **Open decision (D8):** exact threshold for "atraso" — is a mensalidade overdue starting the day after its due date (no grace period), or after a grace window? Not specified anywhere.
- **Clarification to record explicitly:** FIN-04 (the overdue computation) and FIN-05 (the instructor-facing list) are two views of one capability, not two separate features — should be written as a single acceptance criterion rather than duplicated ones.

### FIN-05 — Instrutor pode visualizar lista de inadimplentes

- **Actor:** instructor/admin (mirrors the existing dashboard pattern from Phase 2's medical-exam alerts).
- **Data per row:** student name/registration, amount owed, how many mensalidades are open/overdue, days since the oldest overdue due date.
- **Open decision (D5):** should a student be able to check their own payment status/balance via the same public registration+PIN self-service pattern Phase 2 established for medical exams (a precedent that reversed the earlier "no student self-service" default)? Not requested by any FIN-0X item and not covered by settled policy. Recommend defaulting to **instructor/admin-only**, no student self-service financial view, in this phase — but flag explicitly since Phase 2 set a precedent the user may want to extend.

### FIN-06 — Sistema calcula quantas vezes cada aluno treina por semana

- This is the phase's central open decision (D1). Two materially different readings exist:
  1. **Declared/contracted frequency:** read the existing `Student.classes_per_week` field (already present, already staff-editable). Under this reading, FIN-06 isn't really a new calculation — it's the same value FIN-02/07 use to price the plan tier.
  2. **Actual/observed frequency:** count `Attendance` rows per student over a trailing window (e.g., last 4 weeks) to measure how often they actually show up, independent of what they're nominally enrolled for. This is a materially bigger scope: it requires choosing a window length, deciding whether it's purely informational or feeds any action (e.g., flagging a mismatch between declared plan and actual attendance), and it does not fit cleanly into "fixed plan catalog, stable monthly billing" if it were used as the billing input (actual attendance varies week to week; using it directly would make bills unpredictable, which conflicts with the settled monthly/fixed-tier billing policy).
- **Recommended default:** use reading (1) — `classes_per_week` — as the single frequency value driving both FIN-02/FIN-07 pricing and FIN-06's "calculation" (in effect, FIN-06 becomes "read and expose the student's contracted weekly frequency for pricing," not a new attendance-derived metric). This is simplest, reuses existing data, and keeps billing stable and predictable as the settled policy intends. If the user actually wants an attendance-derived "actual visits/week" metric (e.g., for utilization insight, or to flag students attending more/less than their contracted tier), that is a separate, larger feature that should be scoped explicitly (window length, whether it's informational-only or triggers any tier-mismatch flag) rather than folded silently into Phase 3 pricing.

### FIN-07 — Sistema calcula quanto cada aluno deveria pagar baseado no plano

- As written, this duplicates FIN-02 (both describe "look up the price for this student's plan/tier"). See D2: recommend merging FIN-02 and FIN-07 into one acceptance criterion — "the system computes the expected monthly amount for a student from their plan tier" — used both to generate the mensalidade (FIN-01/02) and to show expected-vs-paid in the overdue list (FIN-05) and any reconciliation view.
- If FIN-07 was actually intended to mean something distinct (e.g., an audit tool comparing what a student *should* pay under their **actual** attendance frequency vs. what they are currently billed under their **declared** tier), that depends entirely on resolving D1 above in favor of reading (2), and should be called out as its own acceptance criterion rather than assumed.

## Open decisions requiring user confirmation

| # | Decision | Recommended default | Why it's open |
|---|---|---|---|
| D1 | Does "frequência semanal" (FIN-02/06/07) mean the student's **declared** `classes_per_week` field, or an **attendance-derived** actual weekly frequency? | Declared `classes_per_week` drives pricing; FIN-06 = expose/read this value, not a new computation. | Central pricing input; the two readings lead to materially different scope and risk destabilizing billing if actual attendance is used directly. |
| D2 | FIN-02 and FIN-07 read as the same capability. Merge them? | Yes — one "price-for-tier" capability, reused by billing generation and by any expected-vs-paid view. | Redundant wording in the raw requirements; needs an explicit call so build/test don't duplicate the same logic under two names. |
| D3 | **This is a conscious narrowing of an earlier commitment, not a routine confirmation.** The Phase 2 handoff didn't just leave this open — it committed to more: "Blocking enforcement is deferred to Phase 3 (Financial foundation), which will define **the renewal/billing action that consults this status**" (`.workflow/epic-02/handoff.md`, MED-04). That wording implies Phase 3 was expected to define some action — plausibly the monthly mensalidade-generation cycle itself, the only recurring "renewal" touchpoint that exists anywhere in this system — that actually consults the medical-exam status. | No blocking action; surface the medical-exam status as an additional flag alongside the overdue-payment flag in the same instructor dashboard/list (FIN-05) — the status is displayed, but nothing (mensalidade generation, payment recording, etc.) is gated by it. **The user must explicitly confirm this is what they intended**, since "passive dashboard flag" is narrower than "the renewal/billing action that consults this status" might suggest — the alternative (e.g., mensalidade generation pauses or is flagged when a student's exam is `vencido`) is a real, different answer the earlier commitment left room for. | Explicitly left open by the Phase 2 handoff; needs an explicit answer, not silence, and should not be rubber-stamped as a continuation of settled policy — it is a new, narrower decision being proposed here. |
| D4 | Is mensalidade status (open/partial/paid/overdue) a **stored state machine** per record, or **computed on read** from linked payments and today's date vs. due date? | Computed on read from the mensalidade amount, its linked payments, and the due date — avoids a state machine to keep in sync, consistent with how Phase 2 computed medical-exam status on read rather than storing it. | Not addressed by settled policy; materially affects the data model tech-analyst will design next. |
| D5 | Should students get a self-service read-only view of their own balance/overdue status (registration+PIN), mirroring the Phase 2 medical-exam precedent? | No — instructor/admin only in this phase. | Not requested by any FIN-0X item; Phase 2 set a precedent for extending self-service that the user may or may not want repeated here. |
| D6 | Exact proration formula for enrollment-month (and, if in scope, mid-cycle plan-tier change) charges. | Daily pro-rata: `plan_price * (remaining_days_in_month_including_enrollment_day / total_days_in_month)`, rounded to the cent; same formula applied to a mid-cycle tier change, effective the day of change. | Settled policy says "proportional" but not the formula; mid-cycle tier-change proration isn't mentioned by settled policy at all. |
| D7 | When a payment doesn't cover the full amount owed, or a student has multiple open mensalidades, which charge(s) does it apply to? | Oldest open mensalidade first (FIFO), any remainder applied to the next-oldest, excess becomes credit. | Not specified by FIN-03 or settled policy; needed before payment-application logic can be built or tested. |
| D8 | Exact "atraso" threshold (grace period before a mensalidade is flagged overdue). | Overdue starting the day after the due date; no grace period. | Not specified anywhere; small but needed for a testable acceptance criterion on FIN-04/05. |
| D9 | Is the plan catalog global (one catalog for the whole system) or per-organization/dojo? | Global/single catalog for this epic, consistent with the epic Non-Goal excluding multi-organization configuration UI. | `Organization`/`Dojo` multi-tenant scaffolding exists in the schema, so this needs an explicit call rather than an assumption, even though the recommended default is straightforward. |
| D10 | Discount/scholarship policy. `plan.md`'s own framing of what Phase 3 needs to define lists "discounts" alongside billing cycle, due dates, and pricing — but the settled 2026-07-19 decisions and this draft's first pass covered everything on that list except discounts. | No discounts or per-student price overrides modeled in this phase — the catalog is fixed-price only, consistent with the epic's fixed-tier, no-dynamic-rate philosophy. | Not addressed anywhere in the raw FIN-0X requirements or the settled epic decisions; silently omitting it would drop a use case the epic's own plan explicitly flagged as needing a definition. |
| D11 | Price-locking vs. re-pricing: when an admin edits a catalog tier's price (creating a new catalog version, per the settled versioning constraint), does an **existing** student's mensalidade auto-reprice to the new version, or does the student stay locked to the plan/version active at their enrollment/contract signature? These are materially different schemas — a live "current tier price" lookup (just `Student.classes_per_week` + "current" catalog rows) versus a pinned `student_plan_id`/`plan_version_id` assignment set at enrollment and changed only by an explicit re-enrollment/plan-change action. | Locked/grandfathered pricing: a student keeps the plan/version price they signed up under until an explicit re-enrollment or plan-change action moves them to a different version. | Not addressed anywhere in the draft's first pass despite being a real schema fork. It also has a legal dimension: Phase 4 prints "which financial plan/version" into a signed contract at enrollment; if pricing isn't locked, a signed contract can drift out of sync with what a student is actually billed later — a question a dojo owner or their lawyer would want to weigh in on, not one that should be decided by implementation default. |

## Proposed acceptance criteria (pending D1–D11 confirmation)

1. Admin can define and version a plan catalog of weekly-frequency tiers with a price each; each mensalidade and (later, Phase 4) contract records which plan/version it used. Per D10, the catalog is fixed-price only — no discount, scholarship, or per-student price override is modeled in this phase.
2. The system generates one mensalidade per active student per month, on the standardized due date, with the amount computed from the student's assigned plan/version (per D11, the version pinned at enrollment/last plan change, not a live lookup against the current catalog); the enrollment month (and, if D6 confirms mid-cycle changes are in scope, any tier-change month) is prorated using the agreed formula.
3. Instructor/admin can record a payment (date, amount) against a student; overpayment becomes credit applied to the next charge, underpayment leaves a residual balance, per the agreed allocation rule (D7).
4. The system computes, on read, whether each mensalidade is open, partially paid, paid, or overdue, without a separate stored status field (per D4), using the agreed overdue threshold (D8).
5. Instructor/admin can view a list of students with overdue mensalidades, showing amount owed and days overdue; per D3, the list also flags each listed student's current medical-exam status without blocking any action.
6. FIN-06's weekly-frequency value (per D1) is the same value used to price a student's plan in items 1–2; no separate attendance-derived frequency metric is introduced unless the user overrides D1.
7. No online payment processing, no email/SMS/push overdue notifications, and no automatic check-in or access restriction are introduced by this phase (carried over Non-Goals).

## Next Agent

Next Agent: requirements-reviewer
