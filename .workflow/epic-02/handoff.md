# Handoff — Epic 02: Financeiro, Pré-Checkin e Relatórios

## What Was Done

- Initialized squad planning run `.workflow/runs/epic-02-plan/`.
- Reviewed canonical Epic 2 artifacts in `.planning/` and current pre-check-in integration points.
- Completed a structured requirements review and recorded the delivery plan at `.workflow/runs/epic-02-plan/plan.md`.
- Resolved the four Phase 1 decision-gate items and shipped **PR-1 (Pré-Checkin)**: `PreCheckIn` model, event minimum-belt eligibility, reversible migration, public confirm/cancel/list endpoints, instructor count/roster endpoints, `/precheckin` public page, transactional conversion on physical check-in, and a uniqueness constraint (one attendance per student/event). Details in `.workflow/epic-02/pr-1-precheckin/handoff.md`.
- Committed as `da5bd69 feat(precheckin): add pre-check-in lifecycle and fix migration baseline`.

## Key Decisions

- Corrected delivery order: Pré-Checkin → Medical/Documents → Financial Foundation → Contracts → Reports.
- Pré-checkin is distinct from attendance; physical check-in remains the official attendance event.
- Phase 1 decisions resolved: eligibility is configurable per class/event via minimum belt (general classes: none; yudansha: blue+; graduated: purple+); changes lock one hour before event start; public endpoint uses registration+PIN with IP/registration rate limiting and generic responses; pre-checkin never auto-converts to attendance — only a physical check-in does, preserving its physical method.
- During PR-1 verification, fixed a latent bug where `app/main.py` bootstrapped schema via `create_all` instead of Alembic, making the initial revision a no-op on a fresh database; Alembic is now the single source of schema truth.

## Open Questions

- Define document-storage policy, finance policy, contract template/versioning, and report projections before their respective phases (PR-2 through PR-5).

## Next Action

- Define the document-storage/access policy, then scope PR-2 (Exames Médicos + document foundation) via `squad-plan`.
