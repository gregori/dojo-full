# Requirements Review — Epic 2, Phase 4 (Contracts, CON-01–CON-04)

## Recommendation — Final (confirmation pass, 2026-07-22)

**APPROVED.** All four items from the prior "NEEDS MINOR REVISION" pass are fixed in the current `requirements-phase4.md`:

1. `StudentPlanService.assign` signature (line 18, 33) — now correctly stated as `assign(db, student)`, no `tier_id`, tier auto-derived from `classes_per_week`. Re-verified directly against `dojo-app/backend/app/services/student_plan_service.py:40` — matches exactly.
2. D7 (lines 62-64) — now states both sub-resolutions explicitly: (a) `Document` is superseded/repointed, never mutated in place, on draft regeneration; (b) the originally-captured `plan_version_id`/price is preserved, not re-derived, on regeneration.
3. D3 (line 40) — now has a concrete committed floor (the eight named fields across aluno/plano/frequência/valor), no longer "to be determined."
4. D2 (line 46) — no longer overstates `PlansPage.tsx` precedent; now explicitly notes `effective_from`/`created_by` are "proposed additions... not fields already present there."

No new issues found. Document is ready for user sign-off on D1–D7 and handoff to `tech-analyst`.

## Final Decision Gate — D1–D7 for user sign-off

| # | Decision | Recommended default |
|---|---|---|
| D1 | Trigger for "no momento da matrícula" | Combined "matricular/renovar aluno" action: one transaction that both calls `StudentPlanService.assign(db, student)` and generates the contract PDF. |
| D2 | Template authoring mechanism | Admin UI, versioned like `PlanVersion` (new fields `effective_from`/`created_by` are proposed, not precedented). |
| D3 | Merge-field/placeholder list | Committed floor: `Student.contract_name`/`contract_cpf`/address block (aluno), `PlanTier.name` (plano), `PlanTier.weekly_frequency` (frequência), `PlanVersion.price` (valor); more may be added once legal text is drafted. |
| D4 | Upload file types/size for signed contracts | Reuse Phase 2's policy unchanged (PDF/JPEG/PNG ≤10MB). |
| D5 | Student self-service access to own contract | No — instructor/admin-only, consistent with Phase 2/Phase 3 precedent. |
| D6 | Renewal history model | Append-only — new `Contract` row per signing event, previous retained as `superseded`. |
| D7 | Draft regeneration before signature | Same `Contract` row kept in `draft` status and edited in place; `Document` is superseded/repointed (never mutated) on regeneration; originally-captured `plan_version_id`/price is preserved (never silently re-priced). |

## Next Agent

Next Agent: planner

---

## Prior review (superseded, kept for history)

**NEEDS MINOR REVISION before `tech-analyst`** — not blocking in the Phase 2-review sense (no requirement is impossible to build, no missing schema concept), but there is one factual error in the "Existing anchors" ground-truth section that should be corrected before it's used as a design input, plus two real ambiguities inside D7 (draft regeneration) that should be resolved or at least explicitly named as open sub-questions before `tech-analyst` designs the `Contract`/`Document` relationship. The CON-01–CON-04 breakdown itself is otherwise clear, testable, and consistent with the epic's settled policy and established patterns (versioned-supersession precedent, Phase 2's `Document` reuse, Phase 3's admin-only default).

## Ground-truth verification

Checked against `dojo-app/backend/app/models/__init__.py`, `student_plan_service.py`, `medical_exam_service.py`, `plans.py`, `PlansPage.tsx` (read 2026-07-22):

- `Student.contract_name`, `contract_cpf`, `address_street/neighborhood/city/zip` — all exist exactly as described, all nullable, all otherwise unused — confirmed.
- `Document` model — confirmed as described: generic, `document_type: str` (not enum), docstring literally says "reused by medical exams and future document types," soft-delete/supersession via `status` (`active`/`superseded`/`deleted`) — confirmed.
- `PlanTier`/`PlanVersion`/`StudentPlan` — confirmed present with exactly the append-only-supersession pattern the doc describes, and `PlanVersion`'s own docstring literally states the D11 grandfathering guarantee ("a later catalog edit never reprices an already-assigned student").
- Phase 2 handoff's self-service-scoping quote — confirmed verbatim in `.workflow/epic-02/handoff.md` line 31: contracts are named as the example type that keeps the stricter admin-only default "unless separately revisited."
- MIME/size policy for D4 — confirmed exactly: `MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024`, `MIME_SIGNATURES` covers `application/pdf`, `image/png`, `image/jpeg` (magic-byte checked, not just client `Content-Type`) in `medical_exam_service.py`.
- `PlansPage.tsx` — confirmed to exist with a versioned-edit UX (editing price creates a new `PlanVersion` via a separate "Alterar Preço" form, old version implicitly superseded), supporting D2's "mirrors `PlansPage.tsx`'s pattern" framing structurally.

**One factual error found:** the "Existing anchors" section (line 18) states `StudentPlanService.assign(student_id, tier_id)` already exists. The actual signature is `StudentPlanService.assign(db: Session, student: Student) -> StudentPlan` — it takes **no `tier_id` parameter at all**. The tier is derived internally and automatically from `student.classes_per_week`; there is no operator-facing "pick a tier" step anywhere in the current code. This doesn't invalidate D1's recommended default (if anything it strengthens it — there is no separate tier-selection action to decouple from contract generation, since `assign` is already a single all-or-nothing call), but the incorrect signature should be fixed before `tech-analyst` reads it, since designing an API around a `tier_id` parameter that isn't part of the real method would be building against a fiction.

**One minor overstatement (non-blocking):** D2 says the recommended admin UI would mirror `PlansPage.tsx`'s pattern with `effective_from`/`created_by` fields. `PlansPage.tsx`'s actual form only has `weekly_frequency`, `name`, `price` — no `effective_from`/`created_by` fields exist today. This is fine as a *proposal* for the new template UI, but it should be phrased as "proposed, not present in `PlansPage.tsx` today" rather than implying those fields are part of the mirrored precedent.

## 1. CON-01–CON-04 breakdown review

| Item | Assessment |
|---|---|
| CON-01 (generate PDF "no momento da matrícula") | Clear once D1 is resolved. The three-candidate framing (student creation / plan-assignment alone / combined action) is thorough, and rejecting "student creation" is well-justified (no plan/value/frequency would exist yet, contradicting CON-02). The recommended combined action is consistent with the Phase 3 D11 breadcrumb's literal wording. |
| CON-02 (student/plan/value/frequency data) | Clear and testable — all four data points map to already-existing, named fields, with a correctly-identified nullability edge case (legal fields are unpopulated today and must be validated before generation). D3 (merge-field list) is appropriately left for later since legal copy itself is out of scope, though see gap note below. |
| CON-03 (upload signed/scanned contract) | Clear and testable. D4's default (reuse Phase 2's PDF/JPEG/PNG ≤10MB policy unchanged) is well-grounded — verified identical in code — and the "assinado/digitalizado" wording argument for not narrowing to PDF-only is sound. |
| CON-04 (store contract associated to student) | Mostly clear. The `Contract` shape mirroring `MedicalExam` is sound and well-precedented. D6 (append-only renewal history) is clear and well-grounded. D7 (draft regeneration) is where real ambiguity remains — see §3. |

No scope creep detected — the non-goals (no payment processing, no notifications, no multi-org template UI) are carried over accurately from settled policy, not smuggled in as new requirements.

## 2. Review of the seven open decisions (D1–D7)

| # | Genuinely open? | Default sound and pattern-consistent? | Blocking? |
|---|---|---|---|
| D1 (matrícula trigger) | Yes — CON-01's Portuguese text doesn't define "o momento" precisely, and three materially different triggers exist in the data model. | Yes. The combined action is the only reading that both satisfies CON-02 (data must exist before generation) and honors the D11 breadcrumb's literal instruction to trigger `StudentPlanService.assign` from within the contract workflow. Ground-truth check strengthens this: since `assign` has no `tier_id` parameter, there's no plausible "assign now, generate contract separately" split that wouldn't just be two calls to the same all-or-nothing action anyway. | No. |
| D2 (template authoring: admin UI vs. seed/config) | Yes — not addressed anywhere in CON-0X text. | Yes — admin UI matches the `PlanVersion` versioned-supersession precedent, and legal-copy edits realistically need to happen without a deploy. | No. |
| D3 (merge-field list) | Yes — CON-02 lists categories, not a placeholder syntax or field-level whitelist. | Partially — no concrete default is actually given, only "a documented list, to be finalized with the template's actual legal text." This is defensible (legal text itself is explicitly out of scope, settled), but it's weaker than the other six defaults, which are all independently buildable today. Recommend the document commit to at least a minimum viable field list now — the same four data categories CON-02 already names (contract_name, contract_cpf, address, plan name/frequency/price) — rather than leaving the whole mechanism open, so `tech-analyst` isn't blocked re-deriving it. | No (a template can't be authored without it, but generation logic and the `Contract` schema don't depend on the final list). |
| D4 (upload file policy) | Yes, not specified by CON-03. | Yes — verified identical to Phase 2's actual, shipped policy; no reason to diverge. | No. |
| D5 (student self-service access) | Yes — explicitly flagged as revisitable by the Phase 2 handoff. | Yes, and specifically checked per the task brief: Phase 2's handoff literally names contracts as the example that **keeps** the stricter admin-only default "unless separately revisited," and Phase 3's own D5 (financial self-service) independently reached the same "no" for the same reason. The Phase 4 D5 recommendation ("no — instructor/admin-only") is fully consistent with both precedents, not a deviation. Confirmed no inconsistency. | No. |
| D6 (append-only renewal history) | Yes, not specified anywhere. | Yes — matches `MedicalExam`/`StudentPlan`'s append-only-supersession pattern exactly (verified in code), and the legal/audit rationale (a dojo needs every past year's signed contract) is sound. | No. |
| D7 (draft regeneration) | Yes, not specified anywhere. | Partially — see §3. The `draft`-status concept itself is reasonable, but it is a genuinely new pattern with no precedent elsewhere in this codebase (every other versioned entity — `MedicalExam`, `StudentPlan`, `PlanVersion`, `Document` — is append-only from the instant of creation; none has a mutable pre-commit state). That's not wrong, but it's a bigger design departure than the table row's one-line framing suggests, and it leaves two sub-questions unresolved (see below). | No (build can proceed against the default), but should be flagged to the user as a deliberate new pattern, not a routine confirmation. |

## 3. Gaps and ambiguities not fully resolved in the draft

1. **D7's "overwrite/replace" language is ambiguous about what happens to the `Document` row (non-blocking, should be sharpened before schema design).** `Contract` has a single, non-nullable-by-design `document_id` FK. `Document` itself is explicitly append-only/supersession-based (its own docstring: superseded/deleted via `status`, never mutated in place). D7's text says regenerating a draft "overwrites/replaces that same draft row (and its still-unsigned `Document`, if the PDF was already produced)" — but doesn't say *how* the `Document` side is replaced: (a) the existing `Document` row's `storage_key`/bytes are mutated in place (breaking `Document`'s own established append-only pattern for the first time), or (b) a new `Document` row is created and marked `active` while the old draft PDF's row is marked `superseded` or `deleted`, and `Contract.document_id` is repointed (consistent with `Document`'s existing pattern, while only the `Contract` row itself is what's new/mutable per D7). Recommend explicitly choosing (b), since it keeps the new "mutable draft" behavior scoped to the new `Contract` concept only, rather than also carving a first-ever exception into `Document`'s established supersession contract.

2. **D7 doesn't say whether regenerating a draft re-runs the price lookup (non-blocking, but should be one explicit sentence).** If a `Contract` draft is generated referencing `PlanVersion` X, and before it's signed the catalog is updated (a new active `PlanVersion` is created for that tier — a realistic sequence since D6/D11 don't prevent it), does "regenerate the draft" (e.g., to fix an address typo) silently re-price the draft to the new `PlanVersion`, or does it keep the originally-referenced `plan_version_id` and only change the non-price fields being edited? Both are defensible, but the document doesn't pick one, and this is exactly the kind of price-drift concern the epic has been careful about elsewhere (D11's whole rationale in Phase 3 was avoiding contract/bill mismatch). Recommend: regeneration preserves the originally-captured `plan_version_id`; only an explicit re-run of the "matricular/renovar" action (D1) re-derives the plan, matching D11's price-locking philosophy.

3. **D3's default is not yet concrete enough to be buildable (non-blocking, addressed above in §2).** Recommend the PM commit to CON-02's own four data categories as the D3 floor now, deferring only the exact placeholder syntax and any additional fields the eventual legal text needs.

4. **The "Existing anchors" `StudentPlanService.assign` signature error (see Ground-truth verification) should be corrected before hand-off**, since it's the kind of detail `tech-analyst` will otherwise design an interface around.

No other gaps found. Coverage of the canonical CON-01–CON-04 text (`.planning/REQUIREMENTS.md`) is complete: CON-01 → D1/AC1, CON-02 → AC2, CON-03 → D4/AC4, CON-04 → D6/D7/AC5-AC6.

## 4. Internal consistency

- **D5 vs. Phase 2/Phase 3 precedent:** explicitly checked per this review's brief — confirmed consistent, not a deviation. See table row above.
- **D1 vs. the actual `StudentPlanService.assign` signature:** the combined-action recommendation holds up under the corrected ground truth (see Ground-truth verification) — if anything the real signature makes the case for merging assignment and contract generation stronger, since there's no manual tier-selection step to decouple in the first place.
- **D6 vs. D7:** internally consistent with each other (draft is pre-permanence, signing is the point history becomes append-only) — the only issue is D7's own internal under-specification, not a conflict between the two.

## Decision Gate — final

The following require explicit user sign-off before `tech-analyst` finalizes the `Contract`/`Document` schema (recommended defaults exist for all, per the requirements doc, and none is individually blocking to starting analysis):

1. **D1** — matrícula trigger: combined "matricular/renovar" action (assign + generate) vs. decoupled actions.
2. **D2** — template authoring: admin UI (versioned, mirrors `PlanVersion`) vs. seed/config-only.
3. **D3** — merge-field/placeholder list: recommend committing to CON-02's four data categories as a floor now, rather than leaving fully open.
4. **D4** — upload policy: reuse Phase 2's PDF/JPEG/PNG ≤10MB unchanged (no narrowing to PDF-only).
5. **D5** — student self-service access: no (admin/instructor-only) — confirmed consistent with both Phase 2's and Phase 3's precedents.
6. **D6** — append-only renewal history (new `Contract` row per signing, previous retained as `superseded`).
7. **D7** — draft regeneration: needs the two sub-questions in §3 (items 1 and 2) resolved or explicitly deferred with a stated interim rule — this is the one item with genuine remaining ambiguity, not just a missing user confirmation.

Two corrections should be made to the document itself before it's finalized (not decision-gate items, factual fixes): the `StudentPlanService.assign` signature in "Existing anchors," and softening the `PlansPage.tsx` "mirrors" claim re: `effective_from`/`created_by` fields.

This phase is approved to proceed to `tech-analyst` once the `StudentPlanService.assign` correction is made and D7's two sub-questions are either resolved or explicitly named as still-open in the decision-gate table (rather than folded into a single one-line recommendation as currently written).

(Superseded by the final verdict at the top of this document — see "Final Decision Gate" above. Next Agent for this document as a whole: planner.)
