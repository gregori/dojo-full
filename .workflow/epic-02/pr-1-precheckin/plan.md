# Plano — PR-1: Pré-Checkin

## Branch

- `feature/pre-checkin`, criada a partir de `origin/develop` em 2026-07-19.

## Estado do baseline

- O aplicativo ativo está em `dojo-app/`, não nos antigos esqueletos da raiz.
- `dojo-app/backend` já contém `Student`, `Event`, `Attendance`, rotas de
  check-in e migrations; `dojo-app/frontend` já contém `EventsPage` e
  `CheckInPage`.
- Esses artefatos são pontos de integração do Pré-Checkin, não dependências
  bloqueantes. Os esqueletos raiz foram removidos.

## Escopo aprovado

1. Adicionar `pre_checkins` separado da presença, com estados `confirmed`, `cancelled`, `converted`, unicidade aluno/evento e migration reversível.
2. Expor confirmação/cancelamento públicos com matrícula + PIN, limite de taxa, resposta genérica e corte de uma hora antes do início.
3. Expor somente para instrutor/admin contagem e lista de confirmados.
4. Acrescentar `/precheckin` e os indicadores/lista de confirmações na tela de eventos.
5. Durante o check-in físico, converter a confirmação válida sem criar mais de uma presença e preservar o método físico.
6. Cobrir ciclo de vida, autorização, privacidade, concorrência/idempotência, cutoff e conversão com testes.

## Decisões aplicadas

- Pré-Checkin é intenção, não presença.
- A elegibilidade é configurável por turma/evento via faixa mínima: treinos gerais não exigem faixa mínima, yudansha exigem azul+ e graduados exigem roxa+.
- Eventos cancelados, iniciados ou encerrados não aceitam confirmações.
- Em reagendamento, manter a confirmação somente se o novo horário ficar fora da janela de uma hora; caso contrário, invalidar e exigir nova ação.
- Criação, cancelamento e reconfirmação ficam bloqueados a partir de uma hora antes do início do evento.
- O endpoint público usa matrícula + PIN, limite de tentativas por IP e matrícula e respostas genéricas, sem expor dados antes da validação.
- O pré-checkin não cria nem converte automaticamente em presença; a presença oficial exige check-in físico no evento/aula/limpeza e preserva seu método físico.

## Próxima ação

Implementar os artefatos pendentes em `dojo-app/`, esclarecer se Eligibility
é uma dependência funcional ou apenas de compatibilidade futura e executar os
gates.
