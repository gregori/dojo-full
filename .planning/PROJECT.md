# Project: Dojo Admin — Epic 2: Financeiro, Pré-Checkin e Relatórios

## What This Is

A web application for managing an Aikido dojo, building on the completed MVP (Epic 1) which handles student lifecycle, belt system, classes, attendance, events, exams, and promotions.

**Epic 2 adds:**
- Pre-checkin system for classes (QR code or manual)
- Medical exam tracking with 1-year validity and document upload
- Report generation and contract management
- Financial management (monthly fees, payment tracking, overdue alerts)

## Context

**Completed (Epic 1):**
- Student registration and management
- Belt hierarchy (6 Kyu + Dan) with requirements
- Class scheduling and attendance tracking
- Event management
- Exam management with eligibility checking
- Promotion system
- Multi-org foundation (single org hardcoded in MVP)

**Tech Stack:**
- Backend: Python 3.13 + FastAPI, Clean Architecture
- Frontend: React + TypeScript
- Database: MySQL 8.4
- Deployment: OKE (OCI Kubernetes Service) via GitHub Actions

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Medical exams valid for 1 year | Standard practice in martial arts | Track expiry date, alert when expiring |
| Contracts generated at enrollment | Legal requirement | PDF generation + upload/scan storage |
| Financial based on training frequency | Fair pricing model | Calculate fees from weekly attendance |
| Pre-checkin via QR code | Reduce front-desk friction | Generate QR, scan at arrival |

## Requirements

### Validated

- ✓ Student management — existing (Epic 1)
- ✓ Belt system with requirements — existing (Epic 1)
- ✓ Class scheduling and attendance — existing (Epic 1)
- ✓ Event management — existing (Epic 1)
- ✓ Exam management with eligibility — existing (Epic 1)
- ✓ Promotion system — existing (Epic 1)

### Active

- [ ] Pre-checkin system for classes
- [ ] Medical exam tracking with validity alerts
- [ ] Document upload/storage (exams, contracts)
- [ ] Contract generation at enrollment
- [ ] Report generation (belt exams, attendance, financial)
- [ ] Monthly fee management
- [ ] Payment tracking and overdue alerts
- [ ] Frequency-based pricing calculation

### Out of Scope

- Multi-org UI management — deferred to Epic 4
- Push notifications — deferred to Epic 3
- Email reminders — deferred to Epic 3

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-03 after Epic 2 initialization*
