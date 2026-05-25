# Epic 1: MVP — Dojo Manager (Gestão de Estudantes)

## Epic Description

Build the foundational web application for managing an Aikido dojo, covering the complete student lifecycle from registration through belt promotion. This epic delivers all core features needed for day-to-day dojo operations.

## Business Value

- Eliminates spreadsheet/paper-based student management
- Provides accurate, automatic eligibility checking for exams and promotions
- Creates an audit trail for all dojo activities
- Reduces instructor administrative overhead by >50%
- Runs on free-tier infrastructure with zero hosting cost

## Scope

### In-Scope

| Area | Details |
|------|---------|
| Authentication | Email/password + Google OAuth, JWT sessions, role-based access (super-admin, instructor, student) |
| Multi-Org Foundation | `org_id` on all tables, single org hardcoded in MVP UI |
| Student Management | Full CRUD: name, phone, email, address, CPF/contractor, medical certificate (PDF), previous grade, current belt, status, photo, emergency contact, enrollment date |
| Belt System | Kyu hierarchy (6→1) + Dan, configurable requirements per belt (training_general, training_graduated, event, cleaning, exam_as_uke) |
| Classes & Attendance | Weekly scheduled classes + ad-hoc classes, cancellation, class type (general/graduated), self-service attendance, retroactive for admin/instructor |
| Graduated Training | Separate class type for graduados (≥ Roxa), attendance tracking |
| Cleaning Groups | Pre-defined groups (1 yudansha + 5-6 coloridas), managed by instructor, no attendance blocking |
| Events | Required/optional events with name, description, date, time, location, max participants, attendance tracking |
| Exams | Record exam date, location, examiners, start/end time, candidates, ukes, board notes, correction reports, results |
| Eligibility Checking | Automatic calculation based on belt requirements (no time window, just minimum counts) |
| Promotion | Manual confirmation by instructor after eligibility verified |

### Out-of-Scope (MVP)

| Area | Reason | Deferred To |
|------|--------|-------------|
| Financial management | High complexity, doesn't block other modules | Epic 2 |
| Notifications/reminders | Requires message queue, email provider | Epic 3 |
| Multi-org UI | Single org sufficient for MVP | Epic 4 |
| QR code attendance | Nice-to-have | Epic 5 |
| Pre-confirmation of attendance | Nice-to-have | Epic 5 |
| Public-facing website | Not needed for internal operations | Future |
| Mobile app | Web app sufficient for MVP | Future |

## PR Breakdown

| PR | Title | Description | Depends On | Blocks |
|----|-------|-------------|------------|--------|
| PR-0 | Infrastructure & CI/CD | Monorepo, Dockerfiles, OKE manifests, GitHub Actions, OCI setup | None | All |
| PR-1 | Auth & Multi-Org Foundation | User model, org model, email/password + Google OAuth, JWT, RBAC | PR-0 | PR-2, PR-3, PR-4, PR-5, PR-6, PR-7, PR-8 |
| PR-2 | Student Management | Student CRUD, profile fields, medical certificate upload, belt assignment | PR-0, PR-1 | PR-3, PR-4, PR-5, PR-6, PR-7, PR-8 |
| PR-3 | Belt System & Requirements | Belt hierarchy, configurable requirements per belt, requirement types | PR-0, PR-1, PR-2 | PR-5, PR-8, PR-9 |
| PR-4 | Classes & Attendance | Class scheduling, self-service attendance, retroactive attendance for staff | PR-0, PR-1, PR-2, PR-3 | PR-9 |
| PR-5 | Graduated Training Sessions | Graduated class type, attendance tracking, eligibility (≥ Roxa) | PR-0, PR-1, PR-2, PR-3 | PR-9 |
| PR-6 | Cleaning Groups | Group management (1 yudansha + 5-6 coloridas), attendance tracking | PR-0, PR-1, PR-2, PR-3 | PR-9 |
| PR-7 | Events Management | Event CRUD, required/optional, attendance tracking | PR-0, PR-1, PR-2 | PR-9 |
| PR-8 | Exams Management | Exam recording: candidates, ukes, board notes, correction reports, schedules | PR-0, PR-1, PR-2, PR-3 | PR-9, PR-10 |
| PR-9 | Eligibility Checking | Automatic eligibility calculation across all requirement types | PR-3, PR-4, PR-5, PR-6, PR-7, PR-8 | PR-10 |
| PR-10 | Promotion System | Manual promotion confirmation, belt upgrade, audit trail | PR-8, PR-9 | None |

## Dependency Graph

```
PR-0-infra ──→ PR-1-auth ──→ PR-2-students ──→ PR-3-belts ──┬─→ PR-4-classes ──┐
                                                          │                    │
                                                          ├─→ PR-5-graduated ──┤
                                                          │                    │
                                                          ├─→ PR-6-cleanings ──┤
                                                          │                    │
                                                          ├─→ PR-7-events ─────┤
                                                          │                    │
                                                          ├─→ PR-8-exams ──────┤
                                                          │                    │
                                                          └────────────────────┴──→ PR-9-eligibility ──→ PR-10-promotion
```

**Merge Order:** 0 → 1 → 2 → 3 → (4, 5, 6, 7, 8 parallel) → 9 → 10

## Epic-Level Acceptance Criteria

- [ ] Students can be registered with all defined fields (name, phone, email, address, CPF/contractor, medical certificate, previous grade, current belt, status, photo, emergency contact, enrollment date)
- [ ] Attendance can be marked by the student (self-service) for classes
- [ ] Retroactive attendance can only be recorded by admin/instructor
- [ ] System automatically validates eligibility for exams based on belt requirements
- [ ] Instructor can create and manage cleaning groups (1 yudansha + 5-6 coloridas)
- [ ] Exams record candidates, ukes, board notes, correction reports, and schedules
- [ ] Correction report is generated per exam by the board
- [ ] Promotion is manual (instructor confirmation required)
- [ ] Multi-org: data is isolated by `org_id` in all tables
- [ ] Authentication works with email/password and Google OAuth
- [ ] Roles are enforced: super-admin (global), instructor (per-dojo), student (per-dojo)
- [ ] Deployment via GitHub Actions to OKE
- [ ] Belt hierarchy follows Kyu system (6→1) + Dan with correct colors
- [ ] Belt requirements have no time window (just minimum counts)
- [ ] Yudansha eligibility requires ≥ Azul (2nd Kyu)
- [ ] Graduados eligibility requires ≥ Roxa (4th Kyu)
- [ ] Instructors are students with an additional role (not a separate entity)

## Story List

| Story | Title | Link |
|-------|-------|------|
| 01-01 | Infrastructure and CI/CD | [story-01-01-infra](../stories/story-01-01-infra.md) |
| 02-01 | Authentication and Multi-Org Foundation | [story-02-01-auth](../stories/story-02-01-auth.md) |
| 02-02 | Student Management | [story-02-02-students](../stories/story-02-02-students.md) |
| 03-01 | Belt System and Requirements | [story-03-01-belts](../stories/story-03-01-belts.md) |
| 04-01 | Classes and Attendance | [story-04-01-classes](../stories/story-04-01-classes.md) |
| 05-01 | Graduated Training Sessions | [story-05-01-graduated](../stories/story-05-01-graduated.md) |
| 06-01 | Cleaning Groups | [story-06-01-cleanings](../stories/story-06-01-cleanings.md) |
| 07-01 | Events Management | [story-07-01-events](../stories/story-07-01-events.md) |
| 08-01 | Exams Management | [story-08-01-exams](../stories/story-08-01-exams.md) |
| 09-01 | Eligibility Checking | [story-09-01-eligibility](../stories/story-09-01-eligibility.md) |
| 10-01 | Promotion System | [story-10-01-promotion](../stories/story-10-01-promotion.md) |

## Dependencies Between Stories

| Story | Depends On | Reason |
|-------|------------|--------|
| 02-01 (Auth) | 01-01 (Infra) | Needs deployed infrastructure |
| 02-02 (Students) | 02-01 (Auth) | Students are linked to user accounts |
| 03-01 (Belts) | 02-02 (Students) | Belts are assigned to students |
| 04-01 (Classes) | 02-02 (Students), 03-01 (Belts) | Attendance links to students; graduated class type requires belt data |
| 05-01 (Graduated) | 03-01 (Belts) | Eligibility depends on belt level |
| 06-01 (Cleanings) | 02-02 (Students), 03-01 (Belts) | Groups contain students; yudansha eligibility requires belt level |
| 07-01 (Events) | 02-02 (Students) | Event attendance links to students |
| 08-01 (Exams) | 03-01 (Belts) | Exams are for belt promotion |
| 09-01 (Eligibility) | 03-01, 04-01, 05-01, 06-01, 07-01, 08-01 | Aggregates all activity types |
| 10-01 (Promotion) | 08-01, 09-01 | Needs exam results and eligibility |

## Timeline / Phase Ordering

| Phase | PRs | Duration (est.) | Notes |
|-------|-----|-----------------|-------|
| Phase 1 | PR-0 | 1 week | Infrastructure setup |
| Phase 2 | PR-1 | 1 week | Auth foundation |
| Phase 3 | PR-2 | 1 week | Student management |
| Phase 4 | PR-3 | 1 week | Belt system foundation |
| Phase 5 | PR-4, PR-5, PR-6, PR-7, PR-8 | 1-2 weeks | Parallel development (all depend on PR-3) |
| Phase 6 | PR-9 | 1 week | Eligibility |
| Phase 7 | PR-10 | 1 week | Promotion |

**Total estimated duration:** 7-9 weeks