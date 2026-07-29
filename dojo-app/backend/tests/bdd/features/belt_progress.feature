# language: pt
Funcionalidade: Progresso de Faixa
  Como aluno e instrutor
  Quero visualizar o progresso de presenças e requisitos de faixa
  Para acompanhar a evolução até a próxima graduação

  Contexto:
    Dado o banco de dados está vazio
    E existe uma faixa "Branca" para categoria "adult" com ordem 1
    E existe uma faixa "6º Kyu" para categoria "adult" com ordem 2
    E existe uma faixa "5º Kyu" para categoria "adult" com ordem 3
    E existe um tipo de evento "Aula Regular" com cor "#3498db"
    E existe um tipo de evento "Treino de Graduados" com cor "#2ecc71"
    E existe um tipo de evento "Limpeza" com cor "#f39c12"
    E existe um usuário com email "admin@dojo.com" e senha "admin123" e papel "admin"
    E estou autenticado como "admin@dojo.com" com senha "admin123"
    E existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    E existe um evento "Aula de Aikido" com tipo "Aula Regular"

  @critical @smoke
  Cenário: Consultar progresso de aluno sem presenças (US-016)
    Quando eu envio uma requisição GET para "/api/v1/students/<student_id>/progress"
    Então o status da resposta deve ser 200
    E a resposta deve conter "current_belt"
    E a resposta deve conter os requisitos de presença

  @critical
  Cenário: Consultar progresso após presenças (US-016)
    Dado o requisito de "Aula Regular" para faixa "Branca" é 30
    E o aluno "João Silva" fez check-in no evento
    Quando eu envio uma requisição GET para "/api/v1/students/<student_id>/progress"
    Então o status da resposta deve ser 200
    E a resposta deve conter o progresso do aluno

  @slow
  Esquema do Cenário: Progresso calcula corretamente após múltiplas presenças (US-016)
    Dado o requisito de "Aula Regular" para faixa "Branca" é 30
    E o aluno "João Silva" tem <presencas> presenças em "Aula Regular"
    Quando eu envio uma requisição GET para "/api/v1/students/<student_id>/progress"
    Então o status da resposta deve ser 200

    Exemplos:
      | presencas |
      | 0         |
      | 15        |
      | 29        |
      | 30        |

  Cenário: Progresso considera apenas eventos que contam para faixa (US-016)
    Dado o requisito de "Aula Regular" para faixa "Branca" é 30
    E existe um evento "Limpeza do Dojo" com tipo "Limpeza"
    E o aluno "João Silva" fez check-in no evento "Limpeza do Dojo"
    Quando eu envio uma requisição GET para "/api/v1/students/<student_id>/progress"
    Então o status da resposta deve ser 200

  @critical
  Cenário: Instrutor visualiza progresso de aluno (US-017)
    Dado existe um usuário com email "instructor@dojo.com" e senha "instruct123" e papel "instructor"
    E estou autenticado como "instructor@dojo.com" com senha "instruct123"
    E o requisito de "Aula Regular" para faixa "Branca" é 30
    E o aluno "João Silva" fez check-in no evento
    Quando eu envio uma requisição GET para "/api/v1/students/<student_id>/progress"
    Então o status da resposta deve ser 200
    E a resposta deve conter o progresso do aluno

  @critical
  Cenário: Admin configura requisitos de presença para faixa (US-015)
    Dado estou autenticado como "admin@dojo.com" com senha "admin123"
    Quando eu envio uma requisição POST para "/api/v1/belts/<belt_id>/requirements" com:
      | field            | value          |
      | event_type_id    | <event_type_id>|
      | required_count   | 30             |
      | description      | Treinos Normais|
    Então o status da resposta deve ser 201
    E a resposta deve conter "required_count" com valor "30"

  Cenário: Admin configura múltiplos requisitos para mesma faixa (US-015)
    Dado estou autenticado como "admin@dojo.com" com senha "admin123"
    E existe um requisito de "Aula Regular" para faixa "Branca" com 30
    Quando eu envio uma requisição POST para "/api/v1/belts/<belt_id>/requirements" com:
      | field            | value          |
      | event_type_id    | <event_type_id>|
      | required_count   | 5              |
      | description      | Limpezas       |
    Então o status da resposta deve ser 201

  Cenário: Admin edita requisito de presença (US-015)
    Dado estou autenticado como "admin@dojo.com" com senha "admin123"
    E existe um requisito de "Aula Regular" para faixa "Branca" com 30
    Quando eu envio uma requisição PUT para "/api/v1/belts/requirements/<requirement_id>" com:
      | field            | value        |
      | required_count   | 40           |
    Então o status da resposta deve ser 200
    E a resposta deve conter "required_count" com valor "40"

  Cenário: Requisito de presença com counts_for_belt=false não conta (US-016)
    Dado o aluno "João Silva" está na faixa "Branca"
    E existe um tipo de evento "Evento Social" com cor "#9b59b6" e não conta para faixa
    E o requisito de "Evento Social" para faixa "6º Kyu" é 30
    E existe um evento "Festa do Dojo" com tipo "Evento Social"
    E o aluno "João Silva" fez check-in no evento "Festa do Dojo"
    Quando eu envio uma requisição GET para "/api/v1/students/<student_id>/progress"
    Então o status da resposta deve ser 200
    E todas as contagens de presença devem ser 0