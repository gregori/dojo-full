# language: pt
Funcionalidade: Gestão de Eventos
  Como administrador ou instrutor
  Quero criar, visualizar e cancelar eventos
  Para organizar as atividades do dojo

  Contexto:
    Dado o banco de dados está vazio
    E existe um tipo de evento "Aula Regular" com cor "#3498db"
    E existe um tipo de evento "Treino de Graduados" com cor "#2ecc71"
    E existe um tipo de evento "Limpeza" com cor "#f39c12"
    E existe um tipo de evento "Exame de Faixa" com cor "#e74c3c"
    E existe um usuário com email "admin@dojo.com" e senha "admin123" e papel "admin"
    E estou autenticado como "admin@dojo.com" com senha "admin123"

  @critical @smoke
  Cenário: Criar evento de aula com sucesso (US-007)
    Quando eu envio uma requisição POST para "/api/v1/events" com:
      | field            | value                  |
      | title            | Aula de Aikido         |
      | event_type_id    | <event_type_id>        |
      | description      | Aula regular de terça  |
      | start_datetime   | 2026-06-02T19:00:00Z   |
      | end_datetime     | 2026-06-02T20:30:00Z   |
    Então o status da resposta deve ser 201
    E a resposta deve conter "title" com valor "Aula de Aikido"
    E a resposta deve conter "check_in_token"
    E a resposta deve conter "status" com valor "scheduled"

  Cenário: Criar evento sem título retorna erro (US-007)
    Quando eu envio uma requisição POST para "/api/v1/events" com:
      | field            | value                  |
      | event_type_id    | <event_type_id>        |
      | start_datetime   | 2026-06-02T19:00:00Z   |
      | end_datetime     | 2026-06-02T20:30:00Z   |
    Então o status da resposta deve ser 422

  Cenário: Criar evento com data final anterior à inicial retorna erro (US-007)
    Quando eu envio uma requisição POST para "/api/v1/events" com:
      | field            | value                  |
      | title            | Aula Inválida          |
      | event_type_id    | <event_type_id>        |
      | start_datetime   | 2026-06-02T20:00:00Z   |
      | end_datetime     | 2026-06-02T19:00:00Z   |
    Então o status da resposta deve ser 422

  @critical
  Cenário: Visualizar lista de eventos (US-008)
    Dado existe um evento "Aula de Aikido" com tipo "Aula Regular"
    E existe um evento "Treino Especial" com tipo "Treino de Graduados"
    Quando eu envio uma requisição GET para "/api/v1/events"
    Então o status da resposta deve ser 200
    E a resposta deve conter uma lista de eventos
    E a lista deve conter "Aula de Aikido"
    E a lista deve conter "Treino Especial"

  Cenário: Visualizar evento específico (US-008)
    Dado existe um evento "Aula de Aikido" com tipo "Aula Regular"
    Quando eu envio uma requisição GET para "/api/v1/events/<event_id>"
    Então o status da resposta deve ser 200
    E a resposta deve conter "title" com valor "Aula de Aikido"
    E a resposta deve conter "event_type"
    E a resposta deve conter "check_in_token"

  Cenário: Visualizar eventos por tipo (US-008)
    Dado existe um evento "Aula de Aikido" com tipo "Aula Regular"
    E existe um evento "Treino Especial" com tipo "Treino de Graduados"
    Quando eu envio uma requisição GET para "/api/v1/events?event_type_id=<event_type_id>"
    Então o status da resposta deve ser 200
    E a lista deve conter "Aula de Aikido"

  @critical
  Cenário: Cancelar evento (US-009)
    Dado existe um evento "Aula de Aikido" com tipo "Aula Regular"
    Quando eu envio uma requisição DELETE para "/api/v1/events/<event_id>"
    Então o status da resposta deve ser 204

  Cenário: Evento cancelado não aceita check-in
    Dado existe um evento "Aula de Aikido" com tipo "Aula Regular"
    E o evento "Aula de Aikido" foi cancelado
    E existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    Quando o aluno faz check-in com:
      | field               | value        |
      | registration_number | 2024001      |
      | pin                 | 1234         |
      | check_in_method     | tablet       |
    Então o status da resposta deve ser 400

  Cenário: Instrutor consegue criar evento (US-007)
    Dado existe um usuário com email "instructor@dojo.com" e senha "instruct123" e papel "instructor"
    E estou autenticado como "instructor@dojo.com" com senha "instruct123"
    Quando eu envio uma requisição POST para "/api/v1/events" com:
      | field            | value                  |
      | title            | Aula do Sensei         |
      | event_type_id    | <event_type_id>        |
      | description      | Aula ministrada        |
      | start_datetime   | 2026-06-03T19:00:00Z   |
      | end_datetime     | 2026-06-03T20:30:00Z   |
    Então o status da resposta deve ser 201

  @slow
  Cenário: Gerar QR Code para evento (US-010)
    Dado existe um evento "Aula de Aikido" com tipo "Aula Regular"
    Quando eu envio uma requisição GET para "/api/v1/events/<event_id>/qr-code"
    Então o status da resposta deve ser 200
    E a resposta deve conter "check_in_token"

  Cenário: QR Code é único por evento (US-010)
    Dado existe um evento "Aula de Aikido" com tipo "Aula Regular"
    E existe um evento "Treino Especial" com tipo "Treino de Graduados"
    Quando eu envio uma requisição GET para "/api/v1/events/<event_id>/qr-code"
    Então o status da resposta deve ser 200
    E o token do QR Code deve ser válido