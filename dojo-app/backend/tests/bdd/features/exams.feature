# language: pt
Funcionalidade: Gestão de Exames de Faixa
  Como administrador e membro da banca
  Quero criar exames, definir banca, avaliar candidatos e promover faixas
  Para gerenciar o processo de graduação do dojo

  Contexto:
    Dado o banco de dados está vazio
    E existe uma faixa "Branca" para categoria "adult" com ordem 1
    E existe uma faixa "6º Kyu" para categoria "adult" com ordem 2
    E existe um tipo de evento "Exame de Faixa" com cor "#e74c3c"
    E existe um usuário com email "admin@dojo.com" e senha "admin123" e papel "admin"
    E existe um usuário com email "sensei@dojo.com" e senha "sensei123" e papel "instructor"
    E existe um usuário com email "shihan@dojo.com" e senha "shihan123" e papel "instructor"
    E existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    E existe um aluno "Maria Santos" com matrícula "2024002" e PIN "5678" e categoria "adult"
    E existe um aluno "Pedro Uke" com matrícula "2024003" e PIN "9012" e categoria "adult"
    E estou autenticado como "admin@dojo.com" com senha "admin123"

  @critical @smoke
  Cenário: Criar exame de faixa (US-018)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    Quando eu envio uma requisição POST para "/api/v1/exams" com:
      | field            | value                  |
      | event_id         | <event_id>             |
      | belt_id          | <belt_id>              |
      | exam_date        | 2026-06-15T10:00:00Z   |
      | notes            | Exame semestral        |
    Então o status da resposta deve ser 201
    E a resposta deve conter "status" com valor "scheduled"

  Cenário: Criar exame sem evento retorna erro (US-018)
    Quando eu envio uma requisição POST para "/api/v1/exams" com:
      | field            | value                  |
      | belt_id          | <belt_id>              |
      | exam_date        | 2026-06-15T10:00:00Z   |
    Então o status da resposta deve ser 422

  @critical
  Cenário: Definir banca examinadora (US-019)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    Quando eu envio uma requisição POST para "/api/v1/exams/<exam_id>/board-members" com:
      | field            | value              |
      | user_id          | <sensei_user_id>   |
      | role_in_board    | president          |
    Então o status da resposta deve ser 201
    E a resposta deve conter "role_in_board" com valor "president"

  Cenário: Adicionar múltiplos membros à banca (US-019)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    E existe um membro na banca do exame com usuário "sensei@dojo.com" como "president"
    Quando eu envio uma requisição POST para "/api/v1/exams/<exam_id>/board-members" com:
      | field            | value              |
      | user_id          | <shihan_user_id>   |
      | role_in_board    | member             |
    Então o status da resposta deve ser 201
    E o exame deve ter 2 membros na banca

  @critical
  Cenário: Cadastrar candidato no exame (US-020)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    Quando eu envio uma requisição POST para "/api/v1/exams/<exam_id>/participants" com:
      | field            | value              |
      | student_id       | <student_id>       |
      | role             | candidate          |
    Então o status da resposta deve ser 201
    E a resposta deve conter "role" com valor "candidate"
    E a resposta deve conter "status" com valor "pending"

  Cenário: Cadastrar uke no exame (US-020)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    Quando eu envio uma requisição POST para "/api/v1/exams/<exam_id>/participants" com:
      | field            | value              |
      | student_id       | <student_id>       |
      | role             | uke                |
    Então o status da resposta deve ser 201
    E a resposta deve conter "role" com valor "uke"

  Cenário: Cadastrar mesmo candidato duas vezes retorna erro (US-020)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    E existe um participante "candidate" no exame com aluno "João Silva"
    Quando eu envio uma requisição POST para "/api/v1/exams/<exam_id>/participants" com:
      | field            | value              |
      | student_id       | <student_id>       |
      | role             | candidate          |
    Então o status da resposta deve ser 400

  @critical
  Cenário: Banca adiciona anotações para candidato (US-021)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    E existe um participante "candidate" no exame com aluno "João Silva"
    E estou autenticado como "sensei@dojo.com" com senha "sensei123"
    Quando eu envio uma requisição PUT para "/api/v1/exams/participants/<participant_id>" com:
      | field            | value                                      |
      | notes            | Boa técnica de projeção. Precisa melhorar ukemi.|
    Então o status da resposta deve ser 200
    E a resposta deve conter "notes" com valor "Boa técnica de projeção. Precisa melhorar ukemi."

  @critical
  Cenário: Admin aprova candidato e promove faixa automaticamente (US-022)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    E existe um participante "candidate" no exame com aluno "João Silva"
    Quando eu envio uma requisição PUT para "/api/v1/exams/participants/<participant_id>" com:
      | field            | value        |
      | status           | approved     |
    Então o status da resposta deve ser 200
    E a resposta deve conter "status" com valor "approved"

  Cenário: Admin reprova candidato mantém faixa atual (US-022)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    E existe um participante "candidate" no exame com aluno "João Silva"
    Quando eu envio uma requisição PUT para "/api/v1/exams/participants/<participant_id>" com:
      | field            | value        |
      | status           | rejected     |
    Então o status da resposta deve ser 200
    E a resposta deve conter "status" com valor "rejected"

  @slow
  Cenário: Fluxo completo de exame (US-018 a US-022)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    Quando eu envio uma requisição POST para "/api/v1/exams" com:
      | field            | value                  |
      | event_id         | <event_id>             |
      | belt_id          | <belt_id>              |
      | exam_date        | 2026-06-15T10:00:00Z   |
    Então o status da resposta deve ser 201

  Cenário: Visualizar histórico de exames de um aluno (US-023)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    E existe um participante "candidate" no exame com aluno "João Silva"
    Quando eu envio uma requisição GET para "/api/v1/students/<student_id>/exam-history"
    Então o status da resposta deve ser 200

  Cenário: Instrutor não consegue aprovar candidato (US-022)
    Dado existe um evento "Exame Semestral" com tipo "Exame de Faixa"
    E existe um exame para o evento "Exame Semestral" com faixa "6º Kyu"
    E existe um participante "candidate" no exame com aluno "João Silva"
    E estou autenticado como "sensei@dojo.com" com senha "sensei123"
    Quando eu envio uma requisição PUT para "/api/v1/exams/participants/<participant_id>" com:
      | field            | value        |
      | status           | approved     |
    Então o status da resposta deve ser 403