# Workflow State

## Product Context

### PRD Status
- **PRD approved:** No — draft complete, pending Requirements Reviewer
- **docs/PRD.md:** Product overview with vision, personas, goals, non-goals, belt hierarchy, epic list
- **docs/epics/epic-01-mvp.md:** Epic 1 details with scope, PR breakdown, dependency graph, acceptance criteria, story list
- **docs/stories/:** 11 story documents with user stories, acceptance criteria (Gherkin), domain models, UI/API requirements, dependencies

### PRD Structure
| File | Description |
|------|-------------|
| `docs/PRD.md` | Product overview: vision, problem, goals, personas, belt hierarchy, tech constraints |
| `docs/epics/epic-01-mvp.md` | Epic 1: MVP scope, PR breakdown (PR-0 through PR-10), dependency graph, timeline |
| `docs/stories/story-01-01-infra.md` | Infrastructure & CI/CD (PR-0) |
| `docs/stories/story-02-01-auth.md` | Authentication & Multi-Org Foundation (PR-1) |
| `docs/stories/story-02-02-students.md` | Student Management (PR-2) |
| `docs/stories/story-03-01-belts.md` | Belt System & Requirements (PR-3) |
| `docs/stories/story-04-01-classes.md` | Classes & Attendance (PR-4) |
| `docs/stories/story-05-01-graduated.md` | Graduated Training Sessions (PR-5) |
| `docs/stories/story-06-01-cleanings.md` | Cleaning Groups (PR-6) |
| `docs/stories/story-07-01-events.md` | Events Management (PR-7) |
| `docs/stories/story-08-01-exams.md` | Exams Management (PR-8) |
| `docs/stories/story-09-01-eligibility.md` | Eligibility Checking (PR-9) |
| `docs/stories/story-10-01-promotion.md` | Promotion System (PR-10) |

## Epic Summary (if epic-level)

### Epic: Dojo Manager - MVP (Gestão de Estudantes)

### PR List & Dependencies
- PR-0-infra:
  - [ ] Status: waiting
  - Blocks: ALL
  - Depends on: none
- PR-1-auth:
  - [ ] Status: waiting
  - Blocks: PR-2-students, PR-3-belts, PR-4-classes, PR-5-graduated, PR-6-cleanings, PR-7-events, PR-8-exams
  - Depends on: PR-0-infra
- PR-2-students:
  - [ ] Status: waiting
  - Blocks: PR-3-belts, PR-4-classes, PR-5-graduated, PR-6-cleanings, PR-7-events, PR-8-exams
  - Depends on: PR-0-infra, PR-1-auth
- PR-3-belts:
  - [ ] Status: waiting
  - Blocks: PR-4-classes, PR-5-graduated, PR-6-cleanings, PR-8-exams, PR-9-eligibility
  - Depends on: PR-0-infra, PR-1-auth, PR-2-students
- PR-4-classes:
  - [ ] Status: waiting
  - Blocks: PR-9-eligibility
  - Depends on: PR-0-infra, PR-1-auth, PR-2-students, PR-3-belts
- PR-5-graduated:
  - [ ] Status: waiting
  - Blocks: PR-9-eligibility
  - Depends on: PR-0-infra, PR-1-auth, PR-2-students, PR-3-belts
- PR-6-cleanings:
  - [ ] Status: waiting
  - Blocks: PR-9-eligibility
  - Depends on: PR-0-infra, PR-1-auth, PR-2-students, PR-3-belts
- PR-7-events:
  - [ ] Status: waiting
  - Blocks: PR-9-eligibility
  - Depends on: PR-0-infra, PR-1-auth, PR-2-students
- PR-8-exams:
  - [ ] Status: waiting
  - Blocks: PR-9-eligibility, PR-10-promotion
  - Depends on: PR-0-infra, PR-1-auth, PR-2-students, PR-3-belts
- PR-9-eligibility:
  - [ ] Status: waiting
  - Blocks: PR-10-promotion
  - Depends on: PR-3-belts, PR-4-classes, PR-5-graduated, PR-6-cleanings, PR-7-events, PR-8-exams
- PR-10-promotion:
  - [ ] Status: waiting
  - Blocks: none
  - Depends on: PR-8-exams, PR-9-eligibility

### Dependency Graph
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

### Consolidated Architecture
- **Backend:** Python 3.13 + FastAPI, Clean Architecture
- **Frontend:** React + TypeScript
- **Database:** MySQL (container no OKE, ARM Always Free VM)
- **Deploy:** OKE (OCI Kubernetes Service) via GitHub Actions
- **Multi-org:** `org_id` em todas as tabelas (UI de gestão de orgs no MVP = single org hardcoded)
- **Storage:** PersistentVolume via hostPath ou OCI Block Volume para MySQL

### Domain Model
- **Student:** nome, telefone, email, endereço, CPF/contratante, atestado médico (PDF), graduação anterior, faixa atual, status, foto, contato emergência, data ingresso
- **Belt:** hierarquia Kyu (6→1: branca, amarela, roxa, verde, azul, marrom) + Dan, requisitos variam por faixa
- **BeltRequirement:** tipo (training_general, training_graduated, event, cleaning, exam_as_uke), minimum_count, sem janela de tempo
- **Class:** horário fixo semanal + avulsas, cancelamento, tipo (geral/graduado)
- **Attendance:** student_id, activity_type, activity_id, date, present
- **CleaningGroup:** lista pré-definida (1 yudansha + 5-6 coloridas), gestão por instrutor, sem bloqueio de presença
- **Event:** tipo, nome, descrição, data, horário, local, max_participants, is_required
- **Exam:** data, local, examinadores, horário início/fim, candidatos, ukes, anotações da banca, resultado
- **Roles:** super-admin (global), instrutor (por dojo), aluno (por dojo)

### Belt Hierarchy
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

### Migration Chain (ordered by dependency)
- Step 1: Create orgs table (PR-1-auth)
- Step 2: Create users table with org_id (PR-1-auth)
- Step 3: Create students table (PR-2-students)
- Step 4: Create belts table (PR-3-belts)
- Step 5: Create belt_requirements table (PR-3-belts)
- Step 6: Create classes table (PR-4-classes)
- Step 7: Create attendance table (PR-4-classes)
- Step 8: Create cleaning_groups table (PR-6-cleanings)
- Step 9: Create events table (PR-7-events)
- Step 10: Create exams table (PR-8-exams)
- Step 11: Create exam_candidates table (PR-8-exams)
- Step 12: Create exam_uke table (PR-8-exams)
- Rollback sequence: 12 → 11 → 10 → 9 → 8 → 7 → 6 → 5 → 4 → 3 → 2 → 1

### Consolidated Release Notes
- (será preenchido pelo Epic Coordinator após conclusão dos PRs)

### Future Epics (Deferred)
- **Épico 2:** Financeiro (mensalidades, matrículas, inadimplência)
- **Épico 3:** Notificações e Automação (lembretes, alertas)
- **Épico 4:** Multi-Org UI (gestão de organizações, configurações por org)
- **Épico 5:** QR Code e Pré-confirmação de presença

---

## Per-PR Workflow State

## Request
- Desenvolver Dojo Manager: aplicação web para gerenciamento de dojo de Aikido
- Backend: Python 3.13 + FastAPI, Frontend: React + TypeScript
- Database: MySQL, Deploy: OKE (OCI Kubernetes Service)
- Multi-org (preparado no modelo, UI depois)

## Clarified Scope
- **MVP:** Gestão de Estudantes com faixas, aulas, treinos graduados, limpezas, eventos, exames de faixa, elegibilidade e promoção
- **Instrutores = Estudantes** (papel adicional, não entidade separada)
- **Presença:** Self-service (aluno marca), retroativa apenas para admin/instrutor
- **Faixas:** 6 Kyu + Dan, requisitos variam por faixa (sem janela de tempo)
- **Exames:** Anotações da banca, relatório de correções, ukes, horários
- **Auth:** Email/senha + Google OAuth
- **Financeiro:** Adiado para Épico 2
- **Notificações:** Adiado para Épico 3

### PR-0: Infraestrutura e CI/CD - Escopo Definido
- **Monorepo:** diretórios `backend/` e `frontend/`
- **Dockerfiles:** backend (Python 3.13), frontend (React/Node)
- **OKE:** Cluster na VM ARM Always Free (100% dos recursos)
- **Registry:** OCIR (Always Free tier)
- **Ingress:** Nginx Ingress Controller
- **HTTPS:** Let's Encrypt + cert-manager
- **MySQL:** Container no OKE com PersistentVolume (hostPath ou Block Volume)
- **MySQL Backup:** Cron job → OCI Object Storage (gratuito, 10GB Always Free)
- **CI/CD:** GitHub Actions (develop → build+test, main → deploy)
- **Staging:** Branches apenas, sem ambiente separado
- **Domínio:** IP direto / DNS dinâmico
- **OCI Credentials:** Recriar (compartment, API key, kubeconfig)

## Open Questions
- [ ] Definir shape exata da VM ARM Always Free para OKE (quantos OCPUs/RAM alocar ao node pool)
- [ ] Definir namespace strategy (default vs separar por componente)

## Constraints
- VM ARM Always Free (recursos limitados)
- MySQL como container no OKE (não gerenciado)
- Single org hardcoded no MVP
- Sem notificações no MVP
- Sem financeiro no MVP

## Acceptance Criteria
- [ ] Estudantes podem ser cadastrados com todos os campos definidos
- [ ] Presença pode ser marcada pelo aluno (self-service)
- [ ] Sistema valida elegibilidade para exame automaticamente
- [ ] Instrutor pode gerenciar grupo de limpeza
- [ ] Exames registram candidatos, ukes, anotações, horários
- [ ] Relatório de correções da banca gerado por exame
- [ ] Promoção é manual (confirmação do instrutor)
- [ ] Multi-org: dados isolados por org_id
- [ ] Auth: email/senha + Google OAuth funcional
- [ ] Deploy via GitHub Actions para OKE

## Technical Analysis

### Version Research (via context7)
- **FastAPI:** Latest stable 0.128.0+ (supports Python 3.13, requires Pydantic v2). Dropped Python 3.9 support in 0.129.0.
- **React:** Latest stable 19.1.1+ (React 19). Requires new JSX transform, TypeScript codemod available.
- **SQLAlchemy:** 2.x series (latest 2.0.44+). Supports async via `sqlalchemy[asyncio]` with aiomysql/asyncmy for MySQL.
- **Alembic:** Latest 1.14+ (compatible with SQLAlchemy 2.x). Supports async migrations via `async_engine_from_config`.
- **cert-manager:** Latest v1.14+ (Helm install). Supports Let's Encrypt ACME issuer.
- **Python:** 3.13 (confirmed compatible with FastAPI 0.128+, SQLAlchemy 2.x, Alembic 1.14+).

### Architecture Concerns
1. **ARM Always Free VM:** 4 OCPUs, 24GB RAM total. OKE node pool should reserve ~2GB for system, leaving ~22GB for workloads.
2. **MySQL in-container:** No managed service. Must configure resource limits, health probes, and persistent storage carefully.
3. **OCIR Always Free:** 500MB storage limit. Images must be slim (multi-stage builds, alpine/slim base images).
4. **No staging environment:** Only develop/main branches. Testing must happen locally or via CI before merge.
5. **hostPath vs Block Volume:** hostPath is free but ties pod to node. Block Volume costs money. For MVP + single node, hostPath is acceptable.

### Namespace Strategy
- Single namespace `dojo` for all application components.
- Separate `cert-manager` namespace for cert-manager system (standard practice).
- `ingress-nginx` namespace for Nginx Ingress Controller.

## Proposed Architecture

### Directory Structure
```
dojo-full/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Pydantic Settings (env-based config)
│   │   ├── api/                 # API routes (Clean Architecture: interface layer)
│   │   │   └── __init__.py
│   │   ├── core/                # Core logic, security, exceptions
│   │   │   └── __init__.py
│   │   ├── domain/              # Domain models, entities, value objects
│   │   │   └── __init__.py
│   │   ├── services/            # Business logic (use cases)
│   │   │   └── __init__.py
│   │   ├── repositories/        # Data access (SQLAlchemy)
│   │   │   └── __init__.py
│   │   └── schemas/             # Pydantic schemas (DTOs)
│   │       └── __init__.py
│   ├── alembic/
│   │   ├── env.py               # Async migration config
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_*.py
│   ├── Dockerfile
│   ├── pyproject.toml           # Dependencies, Ruff config, pytest config
│   ├── alembic.ini
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Page components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── services/            # API client (fetch/axios)
│   │   ├── types/               # TypeScript type definitions
│   │   └── utils/
│   ├── public/
│   ├── tests/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
├── k8s/
│   ├── namespace.yaml
│   ├── mysql-deployment.yaml    # Deployment + Service + PVC
│   ├── mysql-backup-cronjob.yaml
│   ├── backend-deployment.yaml  # Deployment + Service
│   ├── frontend-deployment.yaml # Deployment + Service
│   ├── ingress.yaml
│   └── cert-manager-issuer.yaml
├── .github/
│   └── workflows/
│       ├── ci.yml               # develop: lint + test + build
│       └── deploy.yml           # main: push OCIR + apply k8s
├── docker-compose.yml           # Dev local environment
├── .dockerignore
├── AGENTS.md
├── PROJECT_OVERVIEW.md
└── WORKFLOW_STATE.md
```

### Technology Stack & Rationale

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Backend Framework | FastAPI | 0.128+ | Async-native, auto OpenAPI docs, Python 3.13 compatible |
| ORM | SQLAlchemy | 2.0.44+ | Industry standard, async support, Alembic integration |
| Migrations | Alembic | 1.14+ | Official SQLAlchemy migration tool, async support |
| DB Driver | aiomysql | 0.2+ | Pure Python async MySQL driver, no C extensions (ARM compatible) |
| Validation | Pydantic | 2.x | FastAPI native, type-safe settings via pydantic-settings |
| Testing | pytest + httpx | 8.x + 0.27+ | Async test support, FastAPI TestClient |
| Linting | Ruff | 0.8+ | Fast, replaces flake8+isort+black, Python 3.13 support |
| Frontend | React | 19.1+ | Latest stable, concurrent features |
| Frontend Build | Vite | 6.x | Fast HMR, native TypeScript, small bundle |
| Frontend Language | TypeScript | 5.6+ | Type safety, React 19 codemod support |
| Frontend Linting | ESLint + Prettier | 9.x + 3.x | Standard React tooling |
| Frontend Testing | Jest + React Testing Library | 29.x + 16.x | Standard React testing |
| Container Base (backend) | python:3.13-slim | - | Small image (~150MB), ARM64 compatible |
| Container Base (frontend build) | node:22-alpine | - | Small, ARM64 compatible |
| Container Base (frontend serve) | nginx:1.27-alpine | - | Minimal static file server |
| Database | MySQL | 8.4 LTS | ARM64 image available, long-term support |
| Ingress | Nginx Ingress Controller | 1.11+ | Standard, well-documented, free |
| TLS | cert-manager | 1.14+ | Automated Let's Encrypt, Kubernetes native |
| Container Registry | OCIR | - | OCI Always Free (500MB) |
| Object Storage | OCI OSS | - | Always Free (10GB), backup target |
| Orchestration | OKE | - | ARM Always Free VM, single node |

### Kubernetes Resource Limits (ARM Always Free: 4 OCPUs, 24GB RAM)

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas |
|-----------|------------|-----------|----------------|--------------|----------|
| MySQL | 500m | 1000m | 512Mi | 1Gi | 1 |
| Backend | 250m | 500m | 256Mi | 512Mi | 1 |
| Frontend | 100m | 250m | 128Mi | 256Mi | 1 |
| Backup CronJob | 250m | 500m | 256Mi | 512Mi | 1 (scheduled) |
| **Total Reserved** | **1100m** | **2250m** | **1152Mi** | **2432Mi** | |

Remaining for system: ~2900m CPU, ~21GB RAM (ample for kubelet, containerd, nginx ingress, cert-manager).

### Data Flow
```
Client → Nginx Ingress (TLS termination) → Frontend Service (static SPA)
                                     → Backend Service (FastAPI API)
                                                    → MySQL Service (SQLAlchemy async)
```

### Backup Flow
```
CronJob (scheduled) → mysqldump → OCI CLI → Object Storage bucket
                    → gzip compress → pre-signed URL verification
```

### CI/CD Flow
```
develop branch:
  1. Checkout
  2. Backend: Ruff lint + pytest
  3. Frontend: ESLint + Jest
  4. Build Docker images (multi-platform: linux/arm64)
  5. (No push to registry)

main branch:
  1. Checkout
  2. Backend: Ruff lint + pytest
  3. Frontend: ESLint + Jest
  4. Build Docker images (linux/arm64)
  5. Push to OCIR
  6. Configure kubectl (kubeconfig from secrets)
  7. Apply k8s manifests (kubectl apply -f k8s/)
  8. Wait for rollout
```

### Design Patterns
- **Clean Architecture:** Backend organized in layers (api → services → repositories → domain)
- **Dependency Injection:** FastAPI's `Depends()` for services, repositories, DB sessions
- **Repository Pattern:** Abstract data access behind interfaces (testable, swappable)
- **DTO Pattern:** Pydantic schemas separate from domain models
- **Multi-stage Docker:** Separate build and runtime stages for minimal images
- **GitOps-lite:** kubectl apply from CI (full GitOps with ArgoCD deferred)

## Technical Tasks

### PR-0: Infraestrutura e CI/CD

#### Task 1: Monorepo Structure & Backend Setup (medium)
- Create `backend/` directory structure per Proposed Architecture
- Create `backend/pyproject.toml` with dependencies:
  - `fastapi>=0.128.0`, `uvicorn[standard]>=0.34.0`
  - `sqlalchemy[asyncio]>=2.0.44`, `aiomysql>=0.2.0`
  - `alembic>=1.14.0`, `pydantic-settings>=2.7.0`
  - `python-jose[cryptography]>=3.3.0`, `passlib[bcrypt]>=1.7.4`
  - `pytest>=8.3.0`, `httpx>=0.27.0`, `pytest-asyncio>=0.24.0`
  - `ruff>=0.8.0`
- Create `backend/app/main.py` with minimal FastAPI app + health endpoint
- Create `backend/app/config.py` with Pydantic Settings (DB_URL, SECRET_KEY, etc.)
- Create `backend/app/__init__.py` and layer `__init__.py` files
- Create `backend/alembic.ini` and `backend/alembic/env.py` (async config)
- Create `backend/.env.example`
- Configure Ruff in `pyproject.toml`
- **Files:** `backend/**/*` (new)

#### Task 2: Frontend Setup (medium)
- Create `frontend/` directory structure per Proposed Architecture
- Initialize with Vite + React + TypeScript template
- Configure `package.json` with dependencies:
  - `react@^19.1.0`, `react-dom@^19.1.0`
  - `typescript@^5.6.0`, `vite@^6.0.0`
  - `@types/react@^19.0.0`, `@types/react-dom@^19.0.0`
  - `@vitejs/plugin-react@^4.3.0`
  - `jest@^29.7.0`, `@testing-library/react@^16.0.0`, `@testing-library/jest-dom@^6.0.0`
  - `eslint@^9.0.0`, `prettier@^3.0.0`
- Create `frontend/src/main.tsx` with React 19 `createRoot`
- Create `frontend/src/App.tsx` with minimal app
- Create `frontend/vite.config.ts`
- Create `frontend/tsconfig.json`
- Create `frontend/.env.example`
- **Files:** `frontend/**/*` (new)

#### Task 3: Docker Configuration (medium)
- Create `backend/Dockerfile` (multi-stage: python:3.13-slim, ARM64 compatible)
  - Stage 1: Install deps, copy app
  - Stage 2: Slim runtime, non-root user, uvicorn
- Create `frontend/Dockerfile` (multi-stage: node:22-alpine build → nginx:1.27-alpine serve)
  - Stage 1: Node build with Vite
  - Stage 2: Nginx serve with SPA fallback config
- Create `docker-compose.yml` for local dev:
  - Services: backend, frontend, mysql
  - Volumes: MySQL data, hot-reload for dev
  - Networks: isolated dev network
- Create `.dockerignore` (root, backend, frontend)
- **Files:** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `.dockerignore`

#### Task 4: Kubernetes Manifests (large)
- Create `k8s/namespace.yaml` (namespace: dojo)
- Create `k8s/mysql-deployment.yaml`:
  - Deployment with resource limits (500m CPU, 1Gi memory)
  - Service (ClusterIP, port 3306)
  - PersistentVolumeClaim (hostPath for MVP, 5Gi)
  - Environment variables from Secret
  - Readiness/liveness probes
- Create `k8s/mysql-backup-cronjob.yaml`:
  - CronJob (daily at 2AM)
  - Container: mysql client + OCI CLI
  - mysqldump → gzip → OCI Object Storage (via `oci os object put`)
  - ServiceAccount with OCI instance principal or API key secret
- Create `k8s/backend-deployment.yaml`:
  - Deployment with resource limits (500m CPU, 512Mi memory)
  - Service (ClusterIP, port 8000)
  - Environment variables from ConfigMap/Secret
  - Readiness/liveness probes (/health)
- Create `k8s/frontend-deployment.yaml`:
  - Deployment with resource limits (250m CPU, 256Mi memory)
  - Service (ClusterIP, port 80)
- Create `k8s/ingress.yaml`:
  - Nginx Ingress with TLS
  - Paths: `/` → frontend, `/api/` → backend
  - Annotations for cert-manager
- Create `k8s/cert-manager-issuer.yaml`:
  - ClusterIssuer (Let's Encrypt production)
  - ACME config with HTTP-01 challenge
- **Files:** `k8s/*.yaml` (all new)

#### Task 5: GitHub Actions CI/CD (large)
- Create `.github/workflows/ci.yml`:
  - Trigger: push/PR to develop
  - Jobs: backend-lint, backend-test, frontend-lint, frontend-test, docker-build
  - Cache: pip, node_modules
  - Docker build (linux/arm64, no push)
- Create `.github/workflows/deploy.yml`:
  - Trigger: push to main
  - Jobs: ci (reuse), push-to-ocir, deploy-to-k8s
  - OCIR login and push (docker/build-push-action)
  - kubectl apply via kubeconfig secret
  - Rollout status check
- Document required GitHub secrets in README:
  - `OCI_TENANCY`, `OCI_USER`, `OCI_FINGERPRINT`, `OCI_KEY` (base64)
  - `OCI_REGION`, `OCIR_NAMESPACE`
  - `KUBECONFIG` (base64)
  - `OCI_OSS_BUCKET`, `OCI_OSS_NAMESPACE`
- **Files:** `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`

#### Task 6: OCI Setup Documentation (small)
- Create `docs/oci-setup.md` with step-by-step:
  - Create compartment
  - Create API key, upload public key
  - Create OCIR auth token
  - Create Object Storage bucket
  - Create OKE cluster (ARM node pool)
  - Generate kubeconfig
  - Install Nginx Ingress Controller (Helm)
  - Install cert-manager (Helm)
- **Files:** `docs/oci-setup.md` (new)

### Task Dependencies
```
Task 1 (Backend Setup) ──┐
                          ├──→ Task 3 (Docker) ──┐
Task 2 (Frontend Setup) ──┘                       │
                                                  ├──→ Task 5 (CI/CD)
Task 4 (K8s Manifests) ──────────────────────────┘

Task 6 (OCI Docs) ──→ Independent (can be done in parallel)
```

## Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| MySQL OOM on ARM VM | High | Medium | Set memory limits (1Gi), configure `innodb_buffer_pool_size=256M`, monitor with kubectl |
| OCIR 500MB limit exceeded | Medium | Low | Use slim/alpine images, multi-stage builds, prune old images regularly |
| hostPath data loss on node failure | High | Low | Acceptable for MVP; plan OCI Block Volume migration when budget allows |
| cert-manager HTTP-01 challenge fails | Medium | Medium | Ensure port 80 is open, ingress controller properly configured, test with staging issuer first |
| GitHub Actions ARM build slow | Low | Medium | Use QEMU emulation or native ARM runners; cache layers aggressively |
| OCI API key rotation | Medium | Low | Document rotation process, use instance principals if running on OCI compute |
| No staging environment | Medium | High | Enforce CI gates (lint + test must pass), manual smoke test after deploy |
| MySQL backup fails silently | High | Medium | Add backup verification step, alert on failure (deferred to Épico 3 notifications) |
| Single point of failure (single node) | High | Certain | Acceptable for MVP; document DR procedure (manual restore from backup) |
| Python 3.13 compatibility edge cases | Low | Low | FastAPI 0.128+ and SQLAlchemy 2.0.44+ confirmed compatible; pin versions |

## Debate Notes
- HeatWave MySQL: descartado (pago, analytics, não funciona em container)
- Financeiro: adiado (complexidade alta, não bloqueia outros módulos)
- Notificações: adiado (fila de mensagens, templates, provedor de email)
- QR code: adiado (futuro)
- Multi-org: modelo preparado agora, UI depois

## Implementation Notes

### PR-0 Corrections Applied
- **Senhas hardcoded:** Removidas do `mysql-deployment.yaml`. Agora vazias, devem ser setadas via `kubectl create secret` ou CI/CD secrets.
- **Storage:** Criado `k8s/mysql-host-pv.yaml` (PersistentVolume manual com hostPath). PVC agora usa `storageClassName: manual`.
- **Código Python removido:** `backend/` agora contém apenas `Dockerfile` e `.dockerignore`. Código FastAPI será criado no PR-1 (Auth).

### Task 3: Docker Configuration ✅
- `backend/Dockerfile`: Multi-stage build usando `python:3.13-slim`, uv para deps, non-root user, health check
- `frontend/Dockerfile`: Multi-stage build usando `node:22-alpine` → `nginx:1.27-alpine`, SPA fallback nginx config
- `docker-compose.yml`: Local dev com MySQL 8.4, backend, frontend, isolated network, health checks
- `.dockerignore` files for root, backend, and frontend

### Task 4: Kubernetes Manifests ✅
- `k8s/namespace.yaml`: `dojo` namespace
- `k8s/mysql-host-pv.yaml`: PersistentVolume manual com hostPath `/mnt/data/mysql` (MVP)
- `k8s/mysql-deployment.yaml`: MySQL 8.4 com PVC (5Gi), resource limits (500m/1Gi), health probes, Secret para credenciais
- `k8s/mysql-backup-cronjob.yaml`: Daily backup at 2AM com mysqldump + gzip, OCI upload placeholder
- `k8s/backend-deployment.yaml`: Backend com ConfigMap + Secret, resource limits (500m/512Mi), health probes
- `k8s/frontend-deployment.yaml`: Frontend com resource limits (250m/256Mi), health probes
- `k8s/ingress.yaml`: Nginx Ingress com TLS, cert-manager annotations, `/api` → backend, `/` → frontend
- `k8s/cert-manager-issuer.yaml`: Both staging and production Let's Encrypt ClusterIssuers

### Task 5: GitHub Actions CI/CD ✅
- `.github/workflows/ci.yml`: develop/main triggers → backend lint+test, frontend lint+test, Docker build (arm64, no push)
- `.github/workflows/deploy.yml`: main trigger → CI reuse → push to OCIR → deploy to OKE via kubectl apply → rollout status
- Image tags use commit SHA for traceability
- Required secrets documented

### Task 6: OCI Setup Documentation ✅
- `docs/oci-setup.md`: Complete step-by-step guide covering compartment, API key, OCIR token, Object Storage, OKE cluster, kubeconfig, Nginx Ingress, cert-manager, GitHub secrets

## Review Findings
- **Dockerfiles:** ✅ Corretos. Multi-stage, non-root user, health checks, ARM64 compatible.
- **docker-compose.yml:** ✅ Válido. MySQL 8.4, backend, frontend, network isolado.
- **K8s Manifests:** ✅ Válidos após correções. hostPath PV criado, storageClassName `manual`, secrets vazios (preencher via kubectl).
- **CI/CD:** ✅ Workflows corretos. develop → CI, main → deploy. QEMU para arm64, uv para Python, npm para frontend.
- **Resource Limits:** ✅ Adequados. MySQL 500m/1Gi, backend 500m/512Mi, frontend 250m/256Mi. Total ~1100m CPU, ~2.4Gi RAM.
- **Security:** ✅ Senhas removidas. Non-root user nos containers. Secrets via kubectl/CI/CD.
- **Docs:** ✅ oci-setup.md completo.
- **Status:** PR-0 aprovado para merge.

## Current Status
- PRD created: docs/PRD.md + docs/epics/epic-01-mvp.md + 11 story documents
- Requirements Review completed: APPROVED WITH MINOR ISSUES
- 3 critical dependency graph inconsistencies fixed (C1, C2, C3):
  - PR-4 (Classes) now depends on PR-3 (Belts) - graduated class type requires belt data
  - PR-6 (Cleanings) now depends on PR-3 (Belts) - yudansha eligibility requires belt level
  - Dependency graph updated to show PR-3 → PR-4, PR-6, PR-8 arrows
- Merge order corrected: 0 → 1 → 2 → 3 → (4, 5, 6, 7, 8 parallel) → 9 → 10
- Minor issues noted (M1-M4): not blocking, to be addressed during implementation
- PR-0 reviewed and approved (infrastructure files validated)
- PRD APPROVED for technical planning

## Next Agent
- planner (PR-1-auth technical planning)

## Commit Message Draft
-
