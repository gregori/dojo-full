# language: pt
Funcionalidade: Lista de Presença
  Como instrutor
  Quero visualizar e gerenciar a lista de presença de um evento
  Para acompanhar quem está presente na aula

  Contexto:
    Dado o banco de dados está vazio
    E existe uma faixa "Branca" para categoria "adult" com ordem 1
    E existe um tipo de evento "Aula Regular" com cor "#3498db"
    E existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    E existe um aluno "Maria Santos" com matrícula "2024002" e PIN "5678" e categoria "adult"
    E existe um evento "Aula de Aikido" com tipo "Aula Regular"
    E existe um usuário com email "instructor@dojo.com" e senha "instruct123" e papel "instructor"
    E estou autenticado como "instructor@dojo.com" com senha "instruct123"

  @critical @smoke
  Cenário: Visualizar lista de presença vazia (US-013)
    Quando eu envio uma requisição GET para "/api/v1/checkin/event/<event_id>"
    Então o status da resposta deve ser 200
    E a resposta deve conter uma lista vazia de presenças

  @critical
  Cenário: Visualizar lista de presença em tempo real (US-013)
    Dado o aluno "João Silva" fez check-in no evento
    Quando eu envio uma requisição GET para "/api/v1/checkin/event/<event_id>"
    Então o status da resposta deve ser 200
    E a lista de presenças deve conter "João Silva"
    E a lista de presenças não deve conter "Maria Santos"

  Cenário: Lista de presença mostra método de check-in (US-013)
    Dado o aluno "João Silva" fez check-in no evento via "tablet"
    E o aluno "Maria Santos" fez check-in no evento via "qrcode"
    Quando eu envio uma requisição GET para "/api/v1/checkin/event/<event_id>"
    Então o status da resposta deve ser 200
    E a presença de "João Silva" deve ter método "tablet"
    E a presença de "Maria Santos" deve ter método "qrcode"

  @critical
  Cenário: Registrar presença manualmente (US-014)
    Quando eu envio uma requisição POST para "/api/v1/checkin/manual" com:
      | field               | value        |
      | event_id            | <event_id>   |
      | student_id          | <student_id> |
      | check_in_method     | manual       |
    Então o status da resposta deve ser 201
    E o método de check-in deve ser "manual"

  Cenário: Registrar presença manualmente para aluno já presente retorna erro (US-014)
    Dado o aluno "João Silva" fez check-in no evento
    Quando eu envio uma requisição POST para "/api/v1/checkin/manual" com:
      | field               | value        |
      | event_id            | <event_id>   |
      | student_id          | <student_id> |
      | check_in_method     | manual       |
    Então o status da resposta deve ser 400

  Cenário: Instrutor registra presença de aluno inativo retorna erro (US-014)
    Dado o aluno "João Silva" foi inativado
    Quando eu envio uma requisição POST para "/api/v1/checkin/manual" com:
      | field               | value        |
      | event_id            | <event_id>   |
      | student_id          | <student_id> |
      | check_in_method     | manual       |
    Então o status da resposta deve ser 400

  @slow
  Cenário: Lista de presença atualiza após múltiplos check-ins (US-013)
    Dado o aluno "João Silva" fez check-in no evento
    Quando o aluno "Maria Santos" faz check-in com:
      | field               | value        |
      | registration_number | 2024002      |
      | pin                 | 5678         |
      | check_in_method     | tablet       |
    E eu envio uma requisição GET para "/api/v1/checkin/event/<event_id>"
    Então o status da resposta deve ser 200
    E a lista de presenças deve conter 2 alunos