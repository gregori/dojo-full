# Product Requirements Document: Dojo Manager

## Product Vision

A lightweight, self-hosted web application for managing an Aikido dojo — covering student lifecycle, belt progression, class attendance, cleaning groups, events, exams, eligibility checking, and promotion. Built to run on free-tier infrastructure with minimal operational overhead.

## Problem Statement

Dojo instructors currently manage student records, belt requirements, attendance, cleaning schedules, and exam eligibility using spreadsheets, paper, or memory. This leads to:

- Lost or inconsistent student records
- Manual eligibility calculations that are error-prone
- No centralized view of who attended what
- Difficulty tracking belt requirements across multiple activity types
- No audit trail for promotions or exam results

## Goals

| Goal | Description |
|------|-------------|
| Centralize student management | Single source of truth for all student data, belts, and history |
| Automate eligibility checking | System calculates whether a student meets requirements for exams/promotion |
| Track attendance | Self-service attendance for students, retroactive for instructors |
| Manage belt progression | Track requirements per belt, record exam results, manage promotions |
| Organize dojo operations | Cleaning groups, events, graduated training sessions |
| Run on free infrastructure | Deployable on OCI Always Free ARM VM with minimal cost |

## Non-Goals (MVP)

| Non-Goal | Deferred To |
|----------|-------------|
| Financial management (fees, payments, delinquency) | Epic 2 |
| Notifications and automation (reminders, alerts) | Epic 3 |
| Multi-org UI (organization management, per-org settings) | Epic 4 |
| QR code attendance and pre-confirmation | Epic 5 |
| Mobile app | Future |
| Public-facing website | Future |

## Success Metrics

| Metric | Target |
|--------|--------|
| Student onboarding time | < 2 minutes to create a full student record |
| Eligibility check accuracy | 100% — matches manual calculation |
| Attendance marking time | < 5 seconds per student per class |
| System uptime | 99% (single-node, best-effort) |
| Instructor satisfaction | Subjective — reduces admin time by >50% |

## User Personas

### Super-Admin
- **Role:** Platform operator
- **Needs:** Manage organizations, global system access
- **MVP scope:** Single org hardcoded; super-admin exists in data model but has minimal UI

### Instructor (Sensei/Sempai)
- **Role:** Dojo manager and teacher
- **Needs:**
  - Register and manage students
  - Create and manage classes, events, cleaning groups
  - Record exam results and board notes
  - Check student eligibility for exams and promotion
  - Confirm promotions manually
  - Manage belt requirements per grade
- **Key workflows:** Student CRUD, class management, exam recording, eligibility review, promotion confirmation

### Student (Aluno)
- **Role:** Dojo member
- **Needs:**
  - Mark own attendance for classes
  - View own belt, attendance history, and eligibility status
  - View upcoming events and classes
- **Key workflows:** Self-service attendance, view personal dashboard

## High-Level Feature Summary

| Feature | Description | Priority |
|---------|-------------|----------|
| Authentication | Email/password + Google OAuth, role-based access | P0 |
| Student Management | Full CRUD with profile, belt, medical certificate, emergency contact | P0 |
| Belt System | Kyu hierarchy (6→1) + Dan, configurable requirements per belt | P0 |
| Classes & Attendance | Scheduled classes, self-service attendance, retroactive for staff | P0 |
| Graduated Training | Separate class type for graduados (≥ Roxa), attendance tracking | P1 |
| Cleaning Groups | Instructor-managed groups (1 yudansha + 5-6 coloridas) | P1 |
| Events | Required/optional events with attendance tracking | P1 |
| Exams | Record candidates, ukes, board notes, correction reports, schedules | P0 |
| Eligibility Checking | Automatic calculation based on belt requirements | P0 |
| Promotion | Manual confirmation by instructor after eligibility verified | P1 |

## Belt Hierarchy (Kyu System)

| Kyu | Name | Color |
|-----|------|-------|
| 6 | 6º Kyu | Branca (White) |
| 5 | 5º Kyu | Amarela (Yellow) |
| 4 | 4º Kyu | Roxa (Purple) |
| 3 | 3º Kyu | Verde (Green) |
| 2 | 2º Kyu | Azul (Blue) |
| 1 | 1º Kyu | Marrom (Brown) |
| Dan | 1º Dan+ | Preta (Black) |

**Eligibility thresholds:**
- Yudansha (black belt track): ≥ Azul (2nd Kyu)
- Graduados (graduated training): ≥ Roxa (4th Kyu)

## Belt Requirement Types

| Type | Description |
|------|-------------|
| `training_general` | General class attendance |
| `training_graduated` | Graduated training session attendance |
| `event` | Event participation |
| `cleaning` | Cleaning duty participation |
| `exam_as_uke` | Serving as uke in exams |

Requirements have **no time window** — the system counts the total minimum occurrences.

## Technical Constraints

| Constraint | Detail |
|------------|--------|
| Infrastructure | OCI ARM Always Free VM (4 OCPUs, 24GB RAM) |
| Database | MySQL 8.4 as unmanaged container on OKE |
| Backend | Python 3.13 + FastAPI (Clean Architecture) |
| Frontend | React 19 + TypeScript + Vite |
| Deployment | OKE via GitHub Actions |
| Multi-org | `org_id` in all tables; single org hardcoded in MVP UI |
| Notifications | None in MVP |
| Financial | None in MVP |

## Epic List

| Epic | Description | Link |
|------|-------------|------|
| Epic 1: MVP — Student Management | Core dojo management features | [epic-01-mvp](./epics/epic-01-mvp.md) |
| Epic 2: Financial | Monthly fees, enrollments, delinquency | Deferred |
| Epic 3: Notifications | Reminders, alerts, automation | Deferred |
| Epic 4: Multi-Org UI | Organization management, per-org settings | Deferred |
| Epic 5: QR Code | QR attendance, pre-confirmation | Deferred |
