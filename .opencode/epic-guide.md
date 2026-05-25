---
description: Guide for planning and initiating multi-PR epics with proper dependency tracking and workflow sequences
type: procedural-guide
reference: epic-coordinator, product-manager, planner
---

# Guia: Iniciando um Épico

## Visão Geral

Um épico coordena múltiplas PRs relacionadas, garantindo alinhamento arquitetural, migrações sequenciadas e release notes coerentes.

---

## Pré-requisitos

Antes de iniciar um épico, tenha:
- [ ] Descrição geral do épico (pode ser bruta)
- [ ] Histórias de usuário iniciais (se houver)
- [ ] Restrições de negócio (se houver)

---

## Fase 0: Refinar Requisitos com Product Manager

### 0.1 Chamar Product Manager

O Epic Coordinator (ou usuário) chama `@product-manager` para:
- Refinar requisitos brutos em PRD estruturado
- Criar hierarquia de documentos com progressive disclosure
- Validar com Requirements Reviewer

### 0.2 Product Manager irá:

1. **Clarificar requisitos** (grill mode se necessário)
2. **Criar `docs/PRD.md`** (visão geral do produto)
3. **Criar `docs/epics/epic-XX.md`** (detalhes por épico)
4. **Criar `docs/stories/story-XX-X.md`** (histórias com critérios de aceitação)
5. **Chamar Requirements Reviewer** para validação
6. **Iterar** até aprovação

### 0.3 Após PRD Aprovado

- Epic Coordinator divide o épico em PRs baseados nas histórias
- Para cada PR, chama o Planner para iniciar o fluxo per-PR

---

## Fase 1: Configurar Estrutura do Épico

### 1.1 Criar WORKFLOW_STATE.md (nível épico)

Localização: `WORKFLOW_STATE.md` (raiz do repositório ou pasta do épico)

Use o template em `## Epic Summary`:
```markdown
## Epic Summary (if epic-level)

### PR List & Dependencies
- PR-auth-service:
  - [ ] Status: waiting
  - Blocks: PR-frontend-auth
  - Depends on: none
- PR-frontend-auth:
  - [ ] Status: waiting
  - Blocks: PR-docs
  - Depends on: PR-auth-service
- PR-docs:
  - [ ] Status: waiting
  - Blocks: none
  - Depends on: PR-auth-service, PR-frontend-auth

### Consolidated Architecture
- (será preenchido pelo Epic Coordinator)

### Migration Chain (ordered by dependency)
- Step 1: Create users table (PR-auth-service)
- Step 2: Add auth tokens table (PR-auth-service)
- Rollback sequence: Step 2 → Step 1

### Consolidated Release Notes
- (será preenchido pelo Epic Coordinator)
```

### 1.2 Documentar Mapa de Dependências

Registre no WORKFLOW_STATE.md qual PR depende de qual, exemplo:

```
Graph:
PR-A (backend: schema) ─┬─ blocks → PR-B (middleware)
                        └─ blocks → PR-C (frontend)

Merge order: A → B → C
Rollback order: C → B → A
```

---

## Fase 2: Executar Fluxo Per-PR

Cada PR (baseado em uma história do PRD) segue o workflow padrão:

```
Planner → Requirements Reviewer → Tech Analyst → Architecture Reviewer 
  → Implementer → Reviewer → Security Reviewer → Tester 
  → [Doc Writer (incremental)] → [Migration Planner (incremental)]
  → Linter → [Release Notes (incremental)] → Commit-message
```

### Instruções para agents incremental:

**Doc Writer, Migration Planner, Release Notes** devem:
1. Ler a seção "Per-PR Workflow State" do WORKFLOW_STATE.md
2. Completar seu trabalho (Como de normal)
3. Registrar findings em `WORKFLOW_STATE.md` (não criar novo arquivo)
4. **Indicar no final**: "Incremental doc update" ou "Incremental migration found" ou "Draft release note"

### Exemplo: Migration Planner encontrou mudança de schema

```yaml
# Em WORKFLOW_STATE.md - seção "Implementation Notes"
- Migration Planner: Schema change detected
  - Table: users
  - Change: add auth_provider column
  - Migration file: 001_add_auth_provider.sql
  - Safe rollback: drop column
  - Blocks: PR-frontend-auth (depende desta coluna)
```

---

## Fase 3: Ativar Epic Coordinator (quando necessário)

### 3.1 Trigger para Epic Coordinator

Epic Coordinator **inicia quando**:
- [ ] TODAS as PRs passaram do `Tester`
- OU você detectou conflitos entre PRs e quer consolidação antecipada

### 3.2 Solicitar Consolidação

Edite WORKFLOW_STATE.md (nível épico):

```yaml
## Current Status
- All PRs past Tester, ready for epic consolidation
- Conflicts detected in Schema Changes (see Migration Chain)

## Next Agent
- epic-coordinator
```

### 3.3 Epic Coordinator irá:

1. **Coletar arquitetura** de todas as PRs
2. **Validar dependências** (nenhuma circular?)
3. **Sequenciar migrações** (ordem segura de changelog)
4. **Consolidar docs** (índices, cross-references)
5. **Agregar release notes** (narrativa coerente)
6. **Detectar conflitos** (se houver, escalona)
7. **Handoff para Release Notes**

---

## Fase 4: Release Notes (Consolidação Final)

Após Epic Coordinator:

- [ ] Release Notes valida épico-level release notes
- [ ] Atualiza CHANGELOG.md
- [ ] Confirma versioning
- [ ] Prepara comunicação

---

## Checklist: Iniciando um Épico

```
FASE 0 - REFINAMENTO DE REQUISITOS:
[ ] Product Manager chamado para refinar épico
[ ] docs/PRD.md criado (visão geral)
[ ] docs/epics/ criado (detalhes por épico)
[ ] docs/stories/ criado (histórias com critérios de aceitação)
[ ] Requirements Reviewer validou PRD
[ ] PRD aprovado

PRÉ-REQUISITOS (pós-PRD):
[ ] Épico dividido em PRs baseados nas histórias
[ ] Dependências entre PRs documentadas
[ ] WORKFLOW_STATE.md criado com Epic Summary

DURANTE DESENVOLVIMENTO:
[ ] Cada PR segue workflow padrão
[ ] Agents incrementais atualizam WORKFLOW_STATE.md
[ ] Nenhum novo arquivo de documentação criado (tudo em WORKFLOW_STATE.md)
[ ] Conflitos registrados conforme identificados

ANTES DE CONSOLIDAÇÃO:
[ ] Todas as PRs passaram do Tester
[ ] WORKFLOW_STATE.md atualizado com status final de cada PR
[ ] Next Agent definido como epic-coordinator

APÓS CONSOLIDAÇÃO:
[ ] Epic Coordinator sinalizou conclusão
[ ] Release Notes iniciado
[ ] Merge order validada
[ ] Migrações sequenciadas

APÓS RELEASE:
[ ] CHANGELOG.md atualizado
[ ] Tags criadas
[ ] PRs podem fazer merge na ordem validada
```

---

## Troubleshooting

### Conflito detectado: Duas PRs modificam mesma tabela

**Resolução (Epic Coordinator fará):**
1. Contatar autores das PRs
2. Definir sequência (qual vai primeiro)
3. Registrar em WORKFLOW_STATE.md: "PR-A requires rollback of PR-B schema before merge"
4. Atualizar Migration Chain

### PR com delay bloqueando épico

**Solução:**
1. Epic Coordinator marca status: "Blocked by: PR-name"
2. Paralelize outros trabalhos
3. Se PR é bloqueador essencial, reunião de alignment necessária

---

## Exemplo: Epic de Autenticação

```yaml
Epic: User Authentication System

FASE 0 - REFINAMENTO:
1. @product-manager recebe requisitos brutos
2. PM clarifica com usuário (grill mode)
3. PM cria:
   - docs/PRD.md (visão geral)
   - docs/epics/epic-01.md (autenticação)
   - docs/stories/story-01-1.md (login)
   - docs/stories/story-01-2.md (registro)
   - docs/stories/story-01-3.md (recuperação de senha)
4. @requirements-reviewer valida PRD
5. PRD aprovado

FASE 1 - DIVISÃO EM PRs:
PRs:
1. PR-auth-backend (story-01-1 + story-01-2)
   - Depends on: none
   - Blocks: PR-auth-frontend, PR-auth-docs
   - Status: In Implementation

2. PR-auth-frontend (story-01-1 UI)
   - Depends on: PR-auth-backend
   - Blocks: PR-auth-docs
   - Status: Waiting for PR-auth-backend

3. PR-auth-docs
   - Depends on: PR-auth-backend, PR-auth-frontend
   - Blocks: none
   - Status: Ready to start (incremental updates)

Merge Order: 1 → 2 → 3
Epic Coordinator: Inicia quando PR-auth-backend chegar no Tester
```

---

## Referências

- [AGENTS.md](../AGENTS.md) – Regras gerais de workflow
- [epic-coordinator.md](./agents/epic-coordinator.md) – Instruções do agent
- [product-manager.md](./agents/product-manager.md) – Instruções do agent
- [WORKFLOW_STATE.md](../WORKFLOW_STATE.md) – Template de estado compartilhado
