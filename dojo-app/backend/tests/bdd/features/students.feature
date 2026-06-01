# language: pt
Funcionalidade: Gestão de Alunos
  Como administrador
  Quero cadastrar, editar, inativar e listar alunos
  Para gerenciar a matrícula do dojo

  Contexto:
    Dado o banco de dados está vazio
    E existe uma faixa "Branca" para categoria "adult" com ordem 1
    E existe um usuário com email "admin@dojo.com" e senha "admin123" e papel "admin"
    E estou autenticado como "admin@dojo.com" com senha "admin123"

  @critical @smoke
  Cenário: Cadastrar novo aluno com sucesso (US-003)
    Quando eu envio uma requisição POST para "/api/v1/students" com:
      | field         | value        |
      | full_name     | João Silva   |
      | birth_date    | 1990-05-15   |
      | category      | adult        |
      | belt_id       | <belt_id>    |
      | pin           | 1234         |
    Então o status da resposta deve ser 201
    E a resposta deve conter "full_name" com valor "João Silva"
    E a resposta deve conter "registration_number"
    E a resposta deve conter "pin"

  Cenário: Cadastrar aluno gera matrícula automática única (US-003)
    Quando eu envio uma requisição POST para "/api/v1/students" com:
      | field         | value        |
      | full_name     | Maria Santos |
      | birth_date    | 1995-08-20   |
      | category      | adult        |
      | belt_id       | <belt_id>    |
      | pin           | 5678         |
    Então o status da resposta deve ser 201
    E a resposta deve conter "registration_number"

  Cenário: Cadastrar aluno criança com faixa inicial (US-003)
    Dado existe uma faixa "Branca" para categoria "child" com ordem 1
    Quando eu envio uma requisição POST para "/api/v1/students" com:
      | field         | value        |
      | full_name     | Pedro Kids   |
      | birth_date    | 2015-03-10   |
      | category      | child        |
      | belt_id       | <belt_id>    |
      | pin           | 9012         |
    Então o status da resposta deve ser 201
    E a resposta deve conter "category" com valor "child"

  @critical
  Cenário: Listar alunos ativos (US-004)
    Dado existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    E existe um aluno "Maria Santos" com matrícula "2024002" e PIN "5678" e categoria "adult"
    Quando eu envio uma requisição GET para "/api/v1/students"
    Então o status da resposta deve ser 200
    E a resposta deve conter uma lista de alunos

  Cenário: Listar alunos não inclui inativos por padrão (US-004)
    Dado existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    E existe um aluno "Maria Santos" com matrícula "2024002" e PIN "5678" e categoria "adult"
    E o aluno "Maria Santos" foi inativado
    Quando eu envio uma requisição GET para "/api/v1/students"
    Então o status da resposta deve ser 200
    E a lista deve conter "João Silva"
    E a lista não deve conter "Maria Santos"

  Cenário: Listar alunos com filtro de inativos (US-004)
    Dado existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    E existe um aluno "Maria Santos" com matrícula "2024002" e PIN "5678" e categoria "adult"
    E o aluno "Maria Santos" foi inativado
    Quando eu envio uma requisição GET para "/api/v1/students?include_inactive=true"
    Então o status da resposta deve ser 200
    E a lista deve conter "João Silva"
    E a lista deve conter "Maria Santos"

  @critical
  Cenário: Editar dados de um aluno (US-005)
    Dado existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    Quando eu envio uma requisição PUT para "/api/v1/students/<student_id>" com:
      | field         | value         |
      | full_name     | João Updated  |
      | email         | joao@email.com|
      | phone         | 11999999999   |
    Então o status da resposta deve ser 200
    E a resposta deve conter "full_name" com valor "João Updated"
    E a resposta deve conter "email" com valor "joao@email.com"

  Cenário: Editar faixa de um aluno (US-005)
    Dado existe uma faixa "6º Kyu" para categoria "adult" com ordem 2
    E existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    Quando eu envio uma requisição PUT para "/api/v1/students/<student_id>" com:
      | field         | value           |
      | current_belt_id | <belt_id>    |
    Então o status da resposta deve ser 200
    E a resposta deve conter a nova faixa

  @critical
  Cenário: Inativar um aluno (US-006)
    Dado existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    Quando eu envio uma requisição DELETE para "/api/v1/students/<student_id>"
    Então o status da resposta deve ser 204
    E o aluno deve estar inativo no banco de dados

  Cenário: Aluno inativo não consegue fazer check-in
    Dado existe um aluno "João Silva" com matrícula "2024001" e PIN "1234" e categoria "adult"
    E existe um tipo de evento "Aula Regular" com cor "#3498db"
    E existe um evento "Aula de Aikido" com tipo "Aula Regular"
    E o aluno "João Silva" foi inativado
    Quando o aluno faz check-in com:
      | field               | value        |
      | registration_number | 2024001      |
      | pin                 | 1234         |
      | check_in_method     | tablet       |
    Então o status da resposta deve ser 400

  @critical
  Cenário: Instrutor não consegue cadastrar aluno (US-003)
    Dado existe um usuário com email "instructor@dojo.com" e senha "instruct123" e papel "instructor"
    E estou autenticado como "instructor@dojo.com" com senha "instruct123"
    Quando eu envio uma requisição POST para "/api/v1/students" com:
      | field         | value        |
      | full_name     | João Silva   |
      | birth_date    | 1990-05-15   |
      | category      | adult        |
      | belt_id       | <belt_id>    |
      | pin           | 1234         |
    Então o status da resposta deve ser 403