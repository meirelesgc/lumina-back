# Implementation Plan: Advisorship and Entity Access Control

**Branch**: `001-advisorship-access-control` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-advisorship-access-control/spec.md`

## Summary

O objetivo deste plano é estabelecer a matriz completa de isolamento e controle de acesso para entidades no Lumina Back (Projetos, Documentos e Orientações), corrigindo o vazamento global em `GET /project` e fornecendo a página HTML de demonstração e validação manual (`/demos/advisorship/`) em total conformidade com o Princípio VIII da Constituição.

A abordagem técnica consiste em:
1. Injetar `CurrentUser` nas rotas de projetos e documentos de projeto, filtrando por `created_by` e vínculos ativos de orientação.
2. Criar a página de validação/demo estática em `lumina/demos/advisorship/index.html` servida nativamente pelo FastAPI, permitindo alternância entre personas e validação imediata da matriz de acesso.
3. Adicionar testes de integração cobrindo o isolamento de projetos.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: FastAPI (>=0.120.1), SQLAlchemy 2.0 (Async), Pydantic Settings, PyJWT, Argon2 (pwdlib)

**Storage**: PostgreSQL 17 + pgvector (AsyncSession via SQLAlchemy)

**Testing**: Pytest, Pytest-Asyncio, Testcontainers (Postgres 16), Factory-Boy

**Target Platform**: Linux / Docker Container / AWS EC2

**Project Type**: REST Web Service (FastAPI) + Static HTML Validation Demo

**Performance Goals**: Resposta de consultas e validações de acesso < 50ms (queries indexadas em `created_by` e `deleted_at`)

**Constraints**: Isolamento estrito por sessão; zero vazamento de dados entre contas independentes; compatibilidade retroativa com o frontend

**Scale/Scope**: Módulos de Projetos (`routers/check_tree/projects.py`, `services/project_service.py`), Documentos de Projeto e Demos (`lumina/demos/advisorship/`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio da Constituição | Status | Avaliação / Conformidade |
|---|---|---|
| **I. Arquitetura em Camadas** | ✅ PASS | Separação estrita mantida: Router (`projects.py`) → Service (`project_service.py`) → Repository (`project_repo.py`) → Models (`models.py`). |
| **II. Base de Conhecimento (Check Tree)** | ✅ PASS | Entidades do Check Tree (Projects, ProjectDocuments) respeitam integridade relacional e soft delete. |
| **III. IA Responsável** | ✅ PASS | Não aplicável a esta alteração de autorização; nenhuma chamada a LLM é efetuada ou alterada. |
| **IV. Testes Orientados a Risco** | ✅ PASS | Testes de integração em `tests/integration/` cobrindo cenários críticos de autorização (401, 403, 200) com Testcontainers e savepoints. |
| **V. Simplicidade e Consistência** | ✅ PASS | 79 chars, aspas simples `'`, tipagem estática, linter Ruff e Poetry. |
| **VI. Segurança e Privacidade por Padrão** | ✅ PASS | Corrige diretamente a brecha de segurança/privacidade identificada, garantindo isolamento total entre tenants/usuários. |
| **VII. Documentação Viva (MkDocs)** | ✅ PASS | Resumo funcional preparado para a documentação em `docs/`. |
| **VIII. Página HTML Funcional de Validação/Demo** | ✅ PASS | Página HTML simples criada em `lumina/demos/advisorship/index.html`, servida nativamente pelo FastAPI, sem regras de negócio no frontend e consumindo a API real. |

## Project Structure

### Documentation (this feature)

```text
specs/001-advisorship-access-control/
├── spec.md                  # Especificação funcional e requisitos
├── plan.md                  # Este plano de implementação
├── research.md              # Decisões arquiteturais e resolução de premissas (Phase 0)
├── data-model.md            # Entidades, regras de validação e matriz de acesso (Phase 1)
├── contracts/               # Contrato OpenAPI dos endpoints (Phase 1)
│   └── openapi-access-control.yaml
├── quickstart.md            # Guia de validação manual e automatizada (Phase 1)
├── checklists/
│   └── requirements.md      # Checklist de qualidade da especificação
└── tasks.md                 # Tarefas detalhadas (Phase 2, via /speckit-tasks)
```

### Source Code Impacted

```text
lumina/
├── demos/
│   └── advisorship/
│       └── index.html       # Página HTML de validação e demo interativa da spec
├── repositories/
│   └── project_repo.py      # Filtro de listagem por created_by e orientandos
├── routers/
│   └── check_tree/
│       ├── project_documents.py # Injeção de CurrentUser e proteção de rotas
│       └── projects.py      # Injeção de CurrentUser em GET /project e GET /project/{id}
└── services/
    ├── project_document_service.py # Verificação de permissões de acesso ao projeto
    └── project_service.py   # Lógica de scoping (mine vs advisees) em projetos

tests/
└── integration/
    ├── test_doc_access_control.py     # Testes existentes de documentos
    └── test_project_access_control.py # Novos testes de integração para isolamento de projetos
```

**Structure Decision**: A implementação segue estritamente a arquitetura em camadas do Lumina Back, inserindo o ponto de entrada da demonstração no diretório `lumina/demos/` que já possui montagem de arquivos estáticos configurada no FastAPI.

## Complexity Tracking

*Nenhuma violação à Constituição identificada.*
