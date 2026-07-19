# Phase 1: Pré-Checkin - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-07-03
**Phase:** 01-pr-checkin
**Mode:** discuss
**Areas discussed:** 5

## Discussion Summary

### 1. Data Model — Tabela nova vs. flag na Attendance
- **Options:** Tabela nova `pre_checkins` vs. flag `pre_confirmed` na Attendance
- **Decision:** Tabela nova `pre_checkins`
- **Rationale:** Confirmação antecipada e presença física são eventos distintos com ciclos de vida diferentes. Clean Architecture — cada domínio com seu model.

### 2. Student UI — Onde confirmar presença?
- **Options:** Página pública com matrícula+PIN vs. Portal do aluno com auth vs. Estender CheckInPage
- **Decision:** Página pública com matrícula + PIN
- **Rationale:** Consistente com CheckInPage existente, sem auth necessária, rápido de implementar.

### 3. Timing — Quando pode confirmar/cancelar?
- **Options:** Até 1h antes vs. 30min antes vs. Até horário de início
- **Decision:** Até 1 hora antes da aula
- **Rationale:** Tempo razoável para instrutor ver números e decidir se cancela.

### 4. Instructor UI — Onde vê confirmados e cancela?
- **Options:** Extender EventsPage vs. Nova página dedicada vs. Dashboard widget
- **Decision:** Extender EventsPage com badge de confirmações
- **Rationale:** Reusa página existente, contexto natural, menos código.

### 5. Auto-attendance — Quando confirmação vira presença?
- **Options:** Confirmação + check-in físico vs. Auto-converter no início vs. Instrutor confirma manualmente
- **Decision:** Confirmação + check-in físico = presença
- **Rationale:** Pré-checkin é intenção, não presença garantida. Attendance real só com check-in físico no dojo.

## Deferred Ideas
- Notificações por email/SMS — Epic 3
- Estatísticas de taxa de comparecimento — futuro phase
- Janela de confirmação configurável por dojo — futuro phase
