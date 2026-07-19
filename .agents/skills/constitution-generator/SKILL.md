---
name: constitution-generator
description: Generate CONSTITUTION.md for a project through structured interview.
argument-hint: "Run at project root to generate CONSTITUTION.md"
---

You are generating a CONSTITUTION.md for this project — the universal rules that every AI agent must follow. Interview the user round by round.

For each round, ask 2-4 objective questions. After each answer, summarize briefly. At the end, generate CONSTITUTION.md at the project root.

## Rounds

### Round 1: Stack & Architecture
- Primary language(s)? (Python, TypeScript, Go, Rust, ...)
- Backend framework? (FastAPI, Express, Django, Next.js, ...)
- Frontend? (React, Vue, none, ...)
- Database? (PostgreSQL, MySQL, SQLite, MongoDB, ...)
- Deploy target? (AWS, Azure, OKE, Vercel, ...)

### Round 2: Code Style
- Python linter? (Ruff, pylint, flake8, ...)
- TS/JS linter? (ESLint + Prettier, none, ...)
- Type hints required? (yes/no)
- Docstring format? (Google, NumPy, Sphinx, none)

### Round 3: Testing
- Python framework? (pytest, unittest, ...)
- JS/TS framework? (Vitest, Jest, ...)
- Minimum coverage? (%)
- Test layers? (unit, integration, e2e)

### Round 4: Git & PRs
- Branch pattern? (feature/xxx, fix/xxx, ...)
- Commit format? (Conventional Commits, gitmoji, ...)
- Review required? (always, optional, none)
- CI must pass? (lint + test + build)

### Round 5: Security
- Auth method? (JWT, OAuth, sessions, API keys)
- Secrets management? (env vars, vault, ...)
- Input validation required? (yes/no)
- SQL injection prevention? (ORM, parameterized queries)

### Round 6: Documentation
- Docs location? (docs/, wiki, README only)
- CHANGELOG format? (Semantic, Keep a Changelog, none)
- API docs? (OpenAPI, Swagger, manual)

## Output Format

Generate `CONSTITUTION.md` at the project root with:

```markdown
# CONSTITUTION — [Project Name]

Regras universais que todo agente de IA deve seguir ao trabalhar neste repositório.

## 1. Stack & Arquitetura
...

## 2. Padrões de Código
...

## 3. Testes
...

## 4. Git & Pull Requests
...

## 5. Segurança
...

## 6. Documentação
...
```

Only generate the file after all 6 rounds are complete. Ask "CONSTITUTION.md generated. Review and adjust?" at the end.
