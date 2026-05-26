# Epic 1: MVP — Dojo Manager (Gestão de Estudantes)

## Epic Description
Build the foundational web application for managing an Aikido dojo, covering the complete student lifecycle from registration through belt promotion.

## Business Value
- Eliminates spreadsheet/paper-based student management
- Provides accurate, automatic eligibility checking for exams and promotions
- Creates an audit trail for all dojo activities
- Reduces instructor administrative overhead by >50%
- Runs on free-tier infrastructure with zero hosting cost

## PR List & Dependencies
| PR | Title | Status | Depends On | Blocks |
|----|-------|--------|------------|--------|
| PR-0 | Infrastructure & CI/CD | ✅ Merged | None | All |
| PR-1 | Auth & Multi-Org Foundation | ✅ Ready | PR-0 | PR-2 through PR-8 |
| PR-2 | Student Management | Pending | PR-0, PR-1 | PR-3 through PR-8 |
| PR-3 | Belt System & Requirements | Pending | PR-0, PR-1, PR-2 | PR-5, PR-8, PR-9 |
| PR-4 | Classes & Attendance | Pending | PR-0, PR-1, PR-2, PR-3 | PR-9 |
| PR-5 | Graduated Training Sessions | Pending | PR-0, PR-1, PR-2, PR-3 | PR-9 |
| PR-6 | Cleaning Groups | Pending | PR-0, PR-1, PR-2, PR-3 | PR-9 |
| PR-7 | Events Management | Pending | PR-0, PR-1, PR-2 | PR-9 |
| PR-8 | Exams Management | Pending | PR-0, PR-1, PR-2, PR-3 | PR-9, PR-10 |
| PR-9 | Eligibility Checking | Pending | PR-3 through PR-8 | PR-10 |
| PR-10 | Promotion System | Pending | PR-8, PR-9 | None |

## Dependency Graph
`
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
`

**Merge Order:** 0 → 1 → 2 → 3 → (4, 5, 6, 7, 8 parallel) → 9 → 10

## Consolidated Architecture
- **Backend:** Python 3.13 + FastAPI, Clean Architecture
- **Frontend:** React + TypeScript
- **Database:** MySQL (container no OKE, ARM Always Free VM)
- **Deploy:** OKE (OCI Kubernetes Service) via GitHub Actions
- **Multi-org:** org_id em todas as tabelas (UI de gestão de orgs no MVP = single org hardcoded)
- **Storage:** PersistentVolume via hostPath ou OCI Block Volume para MySQL

## Domain Model
- **Student:** nome, telefone, email, endereço, CPF/contratante, atestado médico (PDF), graduação anterior, faixa atual, status, foto, contato emergência, data ingresso
- **Belt:** hierarquia Kyu (6→1: branca, amarela, roxa, verde, azul, marrom) + Dan, requisitos variam por faixa
- **Class:** horário fixo semanal + avulsas, cancelamento, tipo (geral/graduado)
- **Attendance:** student_id, activity_type, activity_id, date, present
- **CleaningGroup:** lista pré-definida (1 yudansha + 5-6 coloridas), gestão por instrutor
- **Event:** tipo, nome, descrição, data, horário, local, max_participants, is_required
- **Exam:** data, local, examinadores, horário início/fim, candidatos, ukes, anotações da banca, resultado
- **Roles:** super-admin (global), instrutor (por dojo), aluno (por dojo)

## Belt Hierarchy
| Kyu | Name | Color |
|-----|------|-------|
| 6 | 6º Kyu | Branca |
| 5 | 5º Kyu | Amarela |
| 4 | 4º Kyu | Roxa |
| 3 | 3º Kyu | Verde |
| 2 | 2º Kyu | Azul |
| 1 | 1º Kyu | Marrom |
| Dan | 1º Dan+ | Preta |

**Eligibility:** Yudansha ≥ Azul, Graduados ≥ Roxa

## Migration Chain
1. Create orgs table (PR-1) → 2. Create users table (PR-1) → 3. Create students table (PR-2) → 4. Create belts table (PR-3) → 5. Create belt_requirements table (PR-3) → 6. Create classes table (PR-4) → 7. Create attendance table (PR-4) → 8. Create cleaning_groups table (PR-6) → 9. Create events table (PR-7) → 10. Create exams table (PR-8) → 11. Create exam_candidates table (PR-8) → 12. Create exam_uke table (PR-8)

**Rollback:** 12 → 11 → 10 → 9 → 8 → 7 → 6 → 5 → 4 → 3 → 2 → 1

## Future Epics (Deferred)
- **Épico 2:** Financeiro (mensalidades, matrículas, inadimplência)
- **Épico 3:** Notificações e Automação (lembretes, alertas)
- **Épico 4:** Multi-Org UI (gestão de organizações, configurações por org)
- **Épico 5:** QR Code e Pré-confirmação de presença
