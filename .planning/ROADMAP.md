# Roadmap — Epic 2: Financeiro, Pré-Checkin e Relatórios

## Phase 1: Pré-Checkin
**Goal:** Alunos podem fazer pré-checkin para aulas via QR code, e instrutores podem escanear na chegada para registrar presença automaticamente.

**Requirements:** PRE-01, PRE-02, PRE-03, PRE-04, PRE-05

**Success Criteria:**
1. Aluno gera QR code para aula agendada
2. Instrutor escaneia QR code e presença é registrada
3. Sistema confirma visualmente o pré-checkin
4. Presença registrada aparece no histórico do aluno

**Dependencies:** PR-0 (Infra), PR-1 (Auth), PR-2 (Students), PR-4 (Classes), PR-9 (Eligibility)

**UI hint:** yes — QR code generation, scanning interface, confirmation UI

## Phase 2: Controle de Exames Médicos
**Goal:** Sistema rastreia validade de exames médicos (1 ano), alerta vencimento próximo, permite upload de PDFs, e bloqueia renovação com exame vencido.

**Requirements:** MED-01, MED-02, MED-03, MED-04, MED-05, MED-06

**Success Criteria:**
1. Data do último exame registrada por aluno
2. Alerta visual quando exame está a 30 dias do vencimento
3. Upload de PDF do exame funciona e é armazenado
4. Sistema bloqueia renovação com exame vencido
5. Digitalização do exame associada ao aluno

**Dependencies:** PR-0 (Infra), PR-1 (Auth), PR-2 (Students)

**UI hint:** yes — Exam date picker, upload interface, expiry alerts, document viewer

## Phase 3: Geração de Contratos
**Goal:** Sistema gera contrato PDF no momento da matrícula, permite upload do contrato assinado, e armazena documentos associados ao aluno.

**Requirements:** CON-01, CON-02, CON-03, CON-04

**Success Criteria:**
1. Contrato PDF gerado automaticamente na matrícula
2. Contrato inclui dados do aluno, plano, valor e frequência
3. Upload do contrato assinado funciona
4. Contrato armazenado e acessível por aluno

**Dependencies:** PR-0 (Infra), PR-1 (Auth), PR-2 (Students), Phase 2 (Document storage pattern)

**UI hint:** yes — Contract preview, upload interface, document list

## Phase 4: Relatórios
**Goal:** Sistema gera relatórios exportáveis (PDF/CSV) de exames de faixa, presenças e financeiro.

**Requirements:** REP-01, REP-02, REP-03, REP-04, REP-05

**Success Criteria:**
1. Relatório de exame de faixa exportável por aluno
2. Relatório de presenças individual e por turma
3. Relatório financeiro com pagamentos e inadimplência
4. Exportação em PDF e CSV funciona

**Dependencies:** PR-0 (Infra), PR-1 (Auth), PR-2 (Students), PR-4 (Classes), PR-8 (Exams), Phase 2 (Medical data), Phase 5 (Financial data)

**UI hint:** yes — Report selection, export buttons, preview

## Phase 5: Controle Financeiro
**Goal:** Sistema gerencia mensalidades, calcula valores baseados em frequência, registra pagamentos, alerta inadimplência, e calcula frequência semanal.

**Requirements:** FIN-01, FIN-02, FIN-03, FIN-04, FIN-05, FIN-06, FIN-07

**Success Criteria:**
1. Mensalidade registrada por aluno
2. Valor calculado baseado na frequência semanal
3. Pagamentos registrados com data e valor
4. Alertas de inadimplência visíveis
5. Lista de inadimplentes acessível ao instrutor
6. Frequência semanal calculada corretamente

**Dependencies:** PR-0 (Infra), PR-1 (Auth), PR-2 (Students), PR-4 (Classes/Attendance)

**UI hint:** yes — Financial dashboard, payment form, overdue list, frequency calculator

## Phase Summary

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Pré-Checkin | QR code checkin para aulas | 5 (PRE-01 to PRE-05) | 4 |
| 2 | Exames Médicos | Rastrear validade e upload | 6 (MED-01 to MED-06) | 5 |
| 3 | Contratos | Gerar e armazenar contratos | 4 (CON-01 to CON-04) | 4 |
| 4 | Relatórios | Exportar relatórios diversos | 5 (REP-01 to REP-05) | 4 |
| 5 | Financeiro | Mensalidades e inadimplência | 7 (FIN-01 to FIN-07) | 6 |

**Total:** 5 phases | 27 requirements | Ready to build ✓
