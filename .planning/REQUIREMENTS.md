# Requirements — Epic 2: Financeiro, Pré-Checkin e Relatórios

## v1 Requirements

### Pré-Checkin
- [ ] **PRE-01**: Aluno pode confirmar presença antecipada para uma aula agendada
- [ ] **PRE-02**: Aluno pode cancelar confirmação de presença antes da aula
- [ ] **PRE-03**: Instrutor vê lista de alunos confirmados para cada aula
- [ ] **PRE-04**: Instrutor pode decidir cancelar aula baseado no número de confirmações
- [ ] **PRE-05**: Sistema registra presença automaticamente para alunos que confirmaram e compareceram

### Controle de Exames Médicos
- [ ] **MED-01**: Sistema registra data do último exame médico de cada aluno
- [ ] **MED-02**: Sistema calcula validade do exame (1 ano a partir da data)
- [ ] **MED-03**: Sistema alerta quando exame está próximo do vencimento (30 dias)
- [ ] **MED-04**: Sistema bloqueia renovação de matrícula com exame vencido
- [ ] **MED-05**: Aluno/instrutor pode fazer upload do PDF do exame médico
- [ ] **MED-06**: Sistema armazena digitalização do exame associada ao aluno

### Geração de Contratos
- [ ] **CON-01**: Sistema gera contrato PDF no momento da matrícula
- [ ] **CON-02**: Contrato inclui dados do aluno, plano, valor e frequência
- [ ] **CON-03**: Sistema permite upload do contrato assinado/digitalizado
- [ ] **CON-04**: Sistema armazena contrato associado ao aluno

### Relatórios
- [ ] **REP-01**: Relatório de exame de faixa exportável por aluno
- [ ] **REP-02**: Relatório de presenças por período (aluno individual)
- [ ] **REP-03**: Relatório de presenças por turma/período (instrutor)
- [ ] **REP-04**: Relatório financeiro (pagamentos, inadimplência, projeções)
- [ ] **REP-05**: Relatórios exportáveis em PDF e CSV

### Controle Financeiro
- [ ] **FIN-01**: Sistema registra mensalidades de cada aluno
- [ ] **FIN-02**: Sistema calcula valor da mensalidade baseado na frequência semanal
- [ ] **FIN-03**: Sistema registra pagamentos realizados com data e valor
- [ ] **FIN-04**: Sistema alerta alunos com pagamentos em atraso
- [ ] **FIN-05**: Instrutor pode visualizar lista de inadimplentes
- [ ] **FIN-06**: Sistema calcula quantas vezes cada aluno treina por semana
- [ ] **FIN-07**: Sistema calcula quanto cada aluno deveria pagar baseado no plano

## v2 Requirements (Deferred)

### Notificações
- [ ] Notificações por email para exames próximos do vencimento
- [ ] Notificações por email para pagamentos em atraso
- [ ] Lembretes automáticos de aulas

### Multi-Org UI
- [ ] Gestão de organizações via interface
- [ ] Configurações por organização

## Out of Scope

- Processamento de pagamentos online — integração futura com gateway de pagamento
- Contabilidade completa — foco apenas em mensalidades e inadimplência
- Gestão de estoque — não é prioridade para o dojo

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PRE-01 to PRE-05 | Phase 1 | Planned |
| MED-01 to MED-06 | Phase 2 | Planned |
| CON-01 to CON-04 | Phase 3 | Planned |
| REP-01 to REP-05 | Phase 4 | Planned |
| FIN-01 to FIN-07 | Phase 5 | Planned |
