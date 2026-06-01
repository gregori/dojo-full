# language: pt
Funcionalidade: Login de Usuário
  Como instrutor ou administrador
  Quero fazer login na aplicação
  Para acessar as funcionalidades do sistema

  Contexto:
    Dado o banco de dados está vazio

  @smoke @critical
  Cenário: Login com credenciais válidas
    Dado existe um usuário com email "admin@dojo.com" e senha "admin123" e papel "admin"
    Quando eu envio uma requisição POST para "/api/v1/auth/login" com:
      | field    | value           |
      | username | admin@dojo.com  |
      | password | admin123        |
    Então o status da resposta deve ser 200
    E a resposta deve conter um token de acesso válido
    E a resposta deve conter "token_type" com valor "bearer"

  @critical
  Cenário: Login falha com senha incorreta
    Dado existe um usuário com email "admin@dojo.com" e senha "admin123" e papel "admin"
    Quando eu envio uma requisição POST para "/api/v1/auth/login" com:
      | field    | value           |
      | username | admin@dojo.com  |
      | password | wrongpassword   |
    Então o status da resposta deve ser 401
    E a resposta deve conter "detail" com valor "Incorrect email or password"

  Cenário: Login falha com usuário inexistente
    Quando eu envio uma requisição POST para "/api/v1/auth/login" com:
      | field    | value              |
      | username | unknown@dojo.com   |
      | password | anypassword        |
    Então o status da resposta deve ser 401

  @slow
  Esquema do Cenário: Login com vários papéis de usuário
    Dado existe um usuário com email "<email>" e senha "<password>" e papel "<role>"
    Quando eu envio uma requisição POST para "/api/v1/auth/login" com:
      | field    | value      |
      | username | <email>    |
      | password | <password> |
    Então o status da resposta deve ser 200
    E o papel do usuário no token deve ser "<role>"

    Exemplos:
      | email              | password   | role       |
      | admin@dojo.com     | admin123   | admin      |
      | instructor@dojo.com| instruct123| instructor |

  @critical
  Cenário: Admin cria conta de instrutor
    Dado existe um usuário com email "admin@dojo.com" e senha "admin123" e papel "admin"
    E estou autenticado como "admin@dojo.com" com senha "admin123"
    Quando eu envio uma requisição POST para "/api/v1/users" com:
      | field      | value              |
      | email      | instructor@dojo.com|
      | password   | instruct123        |
      | full_name  | Sensei Test        |
      | role       | instructor         |
    Então o status da resposta deve ser 201
    E a resposta deve conter "email" com valor "instructor@dojo.com"
    E a resposta deve conter "role" com valor "instructor"

  Cenário: Instrutor não consegue criar outro usuário
    Dado existe um usuário com email "instructor@dojo.com" e senha "instruct123" e papel "instructor"
    E estou autenticado como "instructor@dojo.com" com senha "instruct123"
    Quando eu envio uma requisição POST para "/api/v1/users" com:
      | field      | value              |
      | email      | another@dojo.com   |
      | password   | pass123            |
      | full_name  | Outro Sensei       |
      | role       | instructor         |
    Então o status da resposta deve ser 403

  Cenário: Instrutor consegue fazer login e acessar sua área
    Dado existe um usuário com email "instructor@dojo.com" e senha "instruct123" e papel "instructor"
    Quando eu envio uma requisição POST para "/api/v1/auth/login" com:
      | field    | value              |
      | username | instructor@dojo.com|
      | password | instruct123        |
    Então o status da resposta deve ser 200
    E a resposta deve conter um token de acesso válido
    E o papel do usuário no token deve ser "instructor"