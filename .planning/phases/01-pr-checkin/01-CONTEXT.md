# Phase 1: Pré-Checkin - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Alunos confirmam presença antecipada para aulas agendadas, e instrutores vêem lista de confirmados para decidir se mantêm ou cancelam o treino. Sistema registra presença automaticamente para confirmados que compareceram (via check-in físico).

**Requirements:** PRE-01, PRE-02, PRE-03, PRE-04, PRE-05

**Success Criteria:**
1. Aluno confirma presença para aula agendada
2. Aluno pode cancelar confirmação antes da aula
3. Instrutor vê lista de alunos confirmados
4. Sistema registra presença automaticamente para confirmados que compareceram

**Dependencies:** PR-0 (Infra), PR-1 (Auth), PR-2 (Students), PR-4 (Classes), PR-9 (Eligibility)

</domain>

<decisions>
## Implementation Decisions

### Data Model
- **D-01:** Nova tabela `pre_checkins` separada de `attendances` — confirmação antecipada e presença física são eventos distintos com ciclos de vida diferentes
- **D-02:** Tabela `pre_checkins` com campos: `id`, `event_id`, `student_id`, `status` (confirmed/cancelled/converted), `confirmed_at`, `cancelled_at`, `converted_at`, timestamps

### Student Confirmation Interface
- **D-03:** Página pública com matrícula + PIN (sem autenticação) — consistente com CheckInPage existente
- **D-04:** URL dedicada (ex: `/precheckin`) — separada do check-in físico (`/checkin`)

### Confirmation Window
- **D-05:** Aluno pode confirmar ou cancelar até **1 hora antes** do `start_datetime` da aula
- **D-06:** Backend valida `start_datetime - now() >= 1 hour` antes de permitir confirmar/cancelar

### Instructor Workflow
- **D-07:** Extender `EventsPage` existente com badge "X confirmados" em cada evento futuro
- **D-08:** Clicar no evento abre detalhe com lista de alunos confirmados
- **D-09:** Botão "Cancelar aula" já existente no EventsPage — instrutor pode cancelar baseado em confirmações baixas

### Auto-Attendance Conversion
- **D-10:** Pré-checkin é **intenção de comparecer**, não presença garantida
- **D-11:** Attendance real só é criada quando aluno faz check-in físico (tablet/QR/manual) no dojo
- **D-12:** Se aluno confirmou e fez check-in → cria Attendance com `check_in_method='precheckin'` (ou marca `pre_confirmed` no Attendance)
- **D-13:** Se aluno confirmou mas NÃO fez check-in → sem Attendance registrada

### OpenCode's Discretion
- Design visual da página de pré-checkin (cores, layout, espaçamento)
- Exatamente como o badge de confirmações é renderizado no EventsPage
- Mensagens de erro/sucesso específicas
- Skeleton loading states
- Ordenação da lista de confirmados (alfabética, por belt, etc.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Domain Models
- `dojo-app/backend/app/models/__init__.py` — Existing ORM models (Event, Attendance, Student, EventType)
- `dojo-app/backend/app/schemas/` — Existing Pydantic schemas

### API Routes
- `dojo-app/backend/app/api/events.py` — Event CRUD routes (extend for confirmation counts)
- `dojo-app/backend/app/api/checkin.py` — Check-in routes (pattern for new precheckin routes)

### Frontend
- `dojo-app/frontend/src/pages/EventsPage.tsx` — Events list page (extend with confirmation badges)
- `dojo-app/frontend/src/pages/CheckInPage.tsx` — Check-in page (pattern for precheckin page)
- `dojo-app/frontend/src/services/api.ts` — API service layer

### Services
- `dojo-app/backend/app/services/attendance_service.py` — Attendance business logic
- `dojo-app/backend/app/services/event_service.py` — Event business logic

### Planning
- `.planning/ROADMAP.md` — Phase 1 goal and success criteria
- `.planning/REQUIREMENTS.md` — PRE-01 to PRE-05 requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Event model**: Already has `status` enum (scheduled/in_progress/finished/cancelled) and `check_in_token` — can add pre-checkin related fields or keep separate
- **Attendance model**: Already has `check_in_method` enum — can add 'precheckin' as a method
- **Student model**: Already has `registration_number` and `pin` — used for public authentication
- **CheckInPage**: React component with registration + PIN form, error/success states, auto-clear — pattern for precheckin page
- **React Query**: `@tanstack/react-query` for server state — use for precheckin data fetching
- **Tailwind + lucide-react**: UI styling and icons — consistent with existing admin frontend

### Established Patterns
- **Clean Architecture**: API → Service → Repository → Database (primary backend) / API → Service → Model (admin backend)
- **Public endpoints**: Check-in routes don't require auth — use rate limiting instead
- **Pydantic schemas**: Request/response validation with typed schemas
- **FastAPI Depends()**: Dependency injection for database sessions and auth
- **Enum status fields**: Consistent use of SQLAlchemy enums for state machines

### Integration Points
- New `pre_checkins` table connects to existing `events` and `students` tables via foreign keys
- New precheckin API routes follow same pattern as checkin routes (public endpoints with rate limiting)
- EventsPage extension needs to fetch pre-checkin counts alongside event data
- Precheckin page uses same student lookup pattern as CheckInPage (registration_number + PIN)

</code_context>

<specifics>
## Specific Ideas

- Pré-checkin deve ser simples: aluno digita matrícula + PIN, seleciona aula futura, confirma
- Instrutor precisa ver rapidamente quantos alunos vão aparecer para decidir se vale a pena dar a aula
- Confirmação é intenção, não compromisso — aluno pode cancelar sem penalidade até 1h antes
- Check-in físico no dojo continua sendo o registro oficial de presença

</specifics>

<deferred>
## Deferred Ideas

- Notificações por email/SMS lembrando aluno de confirmar — Epic 3 (notificações)
- Estatísticas de taxa de comparecimento por aluno — futuro phase
- Configuração de janela de confirmação por dojo — futuro phase

</deferred>

---

*Phase: 01-pr-checkin*
*Context gathered: 2026-07-03*
