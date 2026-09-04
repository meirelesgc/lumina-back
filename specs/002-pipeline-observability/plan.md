# Implementation Plan: Observabilidade e Diagnóstico de Execução do Pipeline

**Branch**: `002-pipeline-observability` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Especificação funcional de `specs/002-pipeline-observability/spec.md` com requisitos de observabilidade estruturada em JSONL, compatibilidade direta `run_id == release_id`, extensibilidade dinâmica de etapas e interface visual minimalista restrita a administradores.

## Summary

O objetivo deste plano é estabelecer a infraestrutura de observabilidade e diagnóstico de execução do pipeline de documentos e inteligência artificial do Lumina Back. 

A solução adota persistência leve em arquivos estruturados **JSON Lines (JSONL)** sob `lumina/storage/pipeline_runs/`, eliminando a necessidade de tabelas relacionais pesadas ou dependências externas complexas. A identificação de cada execução é 1:1 compatível com a release processada (`run_id == release_id`), simplificando a localização e correlação de dados.

O modelo e a interface visual são construídos com **dinamismo total de etapas**: novas fases instrumentadas no pipeline no futuro são consolidadas e exibidas automaticamente na tela sem exigir alterações de código no frontend ou esquemas rígidos. Em estrita conformidade com o Princípio VII da Constituição, é disponibilizada uma página de demonstração e validação administrativa em `/demos/pipeline-observability/` (zero build step, HTML5/CSS/JS vanilla), protegida por controle de acesso baseado em papéis (`role = admin`) e salvaguarda absoluta contra vazamento de dados pessoais (LGPD).

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: FastAPI (>=0.120.1), Pydantic (>=2.0), aiofiles (>=24.1.0)

**Storage**: Arquivos estruturados append-only no formato JSON Lines (JSONL) sob `lumina/storage/pipeline_runs/` (arquivo dedicado por release `{run_id}.jsonl` e índice agregado `index.jsonl`)

**Testing**: Pytest, Pytest-Asyncio, Testcontainers (PostgreSQL 17), Factory-Boy

**Target Platform**: Linux Server / Docker Container / AWS EC2

**Project Type**: REST Web Service (FastAPI) + Static HTML Validation Demo

**Performance Goals**: Overhead de gravação de observabilidade inferior a 2% do tempo total de execução do pipeline; tempo de resposta de consulta a execuções `< 50ms`

**Constraints**:
- Acesso estritamente restrito a administradores (`current_user.access_level == AccessType.ADMIN`);
- Identificador de execução idêntico ao identificador de release (`run_id = release_id`);
- Dinamismo de etapas: etapas não utilizam Enums estáticos e são renderizadas iterativamente na tela;
- Zero vazamento de dados pessoais não anonimizados (PII) nos registros de log;
- Interface de validação minimalista e direta, sem dependência de bibliotecas de gráficos ou frameworks pesados.

**Scale/Scope**:
- Instrumentação do pipeline de release (`lumina/workers/docs/releases.py`, `lumina/services/release_orchestrator.py`);
- Serviço de observabilidade e consolidação de eventos (`lumina/services/run_logger.py`);
- Router administrativo (`lumina/routers/processing_runs.py`);
- Página de demonstração (`lumina/static/demos/pipeline_observability/index.html`) e catálogo (`lumina/static/demos/index.html`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio da Constituição | Status | Avaliação / Conformidade |
|---|---|---|
| **I. Arquitetura em Camadas** | ✅ PASS | Separação rigorosa respeitada: Router (`processing_runs.py`) → Service (`run_logger.py`) → Schemas (`processing_run.py`) e Storage em disco. Nenhuma regra de negócio na camada de transporte. |
| **II. IA Responsável e Engenharia de LLMs** | ✅ PASS | Proibição de registro de dados pessoais em texto puro. Mapeamentos Presidio preservados. Metadados de inferência (modelo, tokens, durações) registrados de forma estruturada e determinística. |
| **III. Testes Orientados a Risco** | ✅ PASS | Testes unitários para o `run_logger.py` e testes de integração com segurança (401, 403, 200) para o router, sem consumo de tokens externos no CI/CD. |
| **IV. Simplicidade e Consistência** | ✅ PASS | Formatação estrita PEP 8 / Ruff (79 chars), aspas simples `'`, tipagem estática e uso do Poetry. |
| **V. Segurança e Privacidade por Padrão** | ✅ PASS | Validação rigorosa de autenticação JWT e autorização administrativa via `AdminUser` (`access_level == AccessType.ADMIN`). Bloqueio 403 para não-admins. Conformidade estrita com a LGPD. |
| **VI. Documentação Viva (MkDocs)** | ✅ PASS | Resumo arquitetural e guia funcional preparados para sincronização na documentação viva em `docs/`. |
| **VII. Página HTML Funcional de Validação/Demo** | ✅ PASS | Página HTML simples, direta e funcional servida nativamente pelo FastAPI em `/demos/pipeline-observability/`, com zero build step, dark mode padrão do projeto e catálogo atualizado. |

## Project Structure

### Documentation (this feature)

```text
specs/002-pipeline-observability/
├── spec.md                  # Especificação funcional e requisitos
├── plan.md                  # Este plano de implementação
├── research.md              # Decisões técnicas e premissas resolvidas (Phase 0)
├── data-model.md            # Entidades, esquemas Pydantic e modelo JSONL (Phase 1)
├── contracts/               # Contrato OpenAPI dos endpoints (Phase 1)
│   └── openapi-pipeline-observability.yaml
├── quickstart.md            # Guia de validação automatizada e interativa (Phase 1)
├── checklists/
│   └── requirements.md      # Checklist de qualidade da especificação
└── tasks.md                 # Tarefas detalhadas (Phase 2, via /speckit-tasks)
```

### Source Code Impacted

```text
lumina/
├── core/
│   ├── dependencies.py          # Adiciona injeção AdminUser para proteção RBAC
│   └── settings.py              # Adiciona configurações PIPELINE_RUNS_DIR e DEBUG_PIPELINE_RUNS
├── demos/
│   ├── index.html               # Atualiza catálogo central com card da Spec 002
│   └── pipeline_observability/  # Página de validação da demo administrativa
│       └── index.html           # Interface minimalista com cascata dinâmica de etapas
├── routers/
│   └── processing_runs.py       # Endpoints GET /processing-runs e GET /processing-runs/{run_id}
├── schemas/
│   ├── __init__.py              # Exporta novos schemas de observabilidade
│   └── processing_run.py        # Schemas Pydantic de eventos, etapas dinâmicas e execuções
├── services/
│   ├── release_logic_service.py # Instrumentação de retrieval, prompt integral, raw output e validação
│   ├── release_orchestrator.py  # Consolidação das 7 macroetapas na linha do tempo da release
│   ├── run_logger.py            # Serviço central JSONL com rotação automática (30 runs / 7 dias)
│   └── vector_service.py        # Instrumentação das etapas de ingestão (extração, seções, LGPD)
└── workers/
    └── docs/
        └── releases.py          # Instrumentação de início/fim do pipeline com run_id == release_id

tests/
├── api/
│   └── routers/
│       └── test_processing_runs.py # Testes de API e segurança (401, 403, 200)
└── unit/
    └── services/
        └── test_run_logger.py      # Testes unitários do gravador/consolidador JSONL e rotação
```

**Structure Decision**: A implementação reutiliza as camadas canônicas do Lumina Back (`routers`, `services`, `schemas`, `demos`), desacoplando a persistência de observabilidade em arquivos JSONL no diretório de armazenamento local (`lumina/storage/pipeline_runs/`), atendendo às diretrizes arquiteturais sem introduzir novas tabelas no banco de dados.

## Complexity Tracking

*Nenhuma violação aos princípios da Constituição identificada.*
