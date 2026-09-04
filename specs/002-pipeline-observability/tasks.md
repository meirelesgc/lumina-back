# Tasks: Observabilidade e Diagnóstico de Execução do Pipeline

**Feature**: Observabilidade e Diagnóstico de Execução do Pipeline para Melhoria Contínua
**Branch**: `002-pipeline-observability`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Estratégia de Commits Semânticos

Seguindo as diretrizes do projeto e a preferência de commits semânticos em português:
- Cada grupo lógico de tarefas ou história de usuário concluída DEVE gerar um commit atômico.
- Padrões de prefixo a utilizar:
  - `feat(observability): [descrição]` para novas funcionalidades e endpoints
  - `test(observability): [descrição]` para novos testes unitários ou de integração
  - `docs(observability): [descrição]` para documentações e MkDocs
  - `refactor(observability): [descrição]` para melhorias e isolamento de código

---

## Phase 1: Setup (Infraestrutura Compartilhada)

**Purpose**: Preparação do ambiente, diretórios de armazenamento e configurações base

- [x] T001 Criar diretório de armazenamento e configuração de caminho `PIPELINE_RUNS_DIR` em `lumina/core/settings.py`
- [x] T002 [P] Inicializar estrutura de arquivos da página de validação em `lumina/static/demos/pipeline_observability/index.html`

---

## Phase 2: Foundational (Pré-requisitos Bloqueantes)

**Purpose**: Modelos Pydantic de eventos, autorização de administrador e motor JSONL

**⚠️ CRITICAL**: Nenhuma história de usuário pode ser finalizada sem estes componentes base.

- [x] T003 Implementar schemas Pydantic de eventos, etapas dinâmicas e execuções em `lumina/schemas/processing_run.py`
- [x] T004 [P] Expor schemas de observabilidade no pacote central em `lumina/schemas/__init__.py`
- [x] T005 [P] Implementar dependência de autorização estrita `AdminUser` em `lumina/core/dependencies.py`
- [x] T006 Implementar motor central de gravação append-only e leitura de eventos JSONL em `lumina/services/run_logger.py`
- [x] T007 [P] Criar testes unitários para o motor JSONL e consolidação dinâmica em `tests/unit/services/test_run_logger.py`

**Commit Semântico Sugerido**: `feat(observability): implementar motor de eventos JSONL e schemas de execucao`

**Checkpoint**: Fundação pronta — Schemas, autorização administrativa e serviço `RunLogger` operacionais.

---

## Phase 3: User Story 1 - Rastreamento Estruturado de Execuções e Etapas do Pipeline (Priority: P1) 🎯 MVP

**Goal**: Atribuir `run_id == release_id` a cada processamento e instrumentar as etapas padrão com timestamps e durações.

**Independent Test**: Submeter uma release no pipeline (`POST /doc/{doc_id}/release`) e verificar a criação do arquivo `lumina/storage/pipeline_runs/{release_id}.jsonl` contendo início, etapas com durações e conclusão.

### Tests for User Story 1
- [x] T008 [P] [US1] Criar testes de integração para o ciclo de vida do pipeline e compatibilidade `run_id == release_id` em `tests/api/routers/test_processing_runs.py`

### Implementation for User Story 1
- [x] T009 [US1] Instrumentar início e término do ciclo de vida com `run_id = release_id` em `lumina/workers/docs/releases.py`
- [x] T010 [US1] Instrumentar ganchos de etapas (extração, seções, anonimização, embeddings, avaliação, síntese) em `lumina/services/release_orchestrator.py`
- [x] T011 [US1] Conectar persistência de eventos ao arquivo de índice `lumina/storage/pipeline_runs/index.jsonl` em `lumina/services/run_logger.py`

**Commit Semântico Sugerido**: `feat(observability): instrumentar pipeline de releases com rastreamento 1:1 em JSONL`

**Checkpoint**: User Story 1 (MVP) concluída — O pipeline grava seu ciclo de vida em logs estruturados vinculados ao ID da release.

---

## Phase 4: User Story 2 - Isolamento e Controle de Acesso Restrito a Administradores (Priority: P1)

**Goal**: Expor endpoints REST administrativos para consulta paginada e detalhamento de execuções com proteção RBAC estrita.

**Independent Test**: Usuário não-admin recebe `403 Forbidden` ao acessar `/processing-runs`; administrador autenticado recebe `200 OK` com dados consolidados.

### Tests for User Story 2
- [x] T012 [P] [US2] Criar testes de segurança e autorização (401 Unauthorized e 403 Forbidden) em `tests/api/routers/test_processing_runs.py`

### Implementation for User Story 2
- [x] T013 [US2] Implementar router administrativo com endpoint de listagem `GET /processing-runs` em `lumina/routers/processing_runs.py`
- [x] T014 [US2] Implementar endpoints `GET /processing-runs/{run_id}` e `GET /processing-runs/{run_id}/events` em `lumina/routers/processing_runs.py`
- [x] T015 [US2] Registrar o router de observabilidade na aplicação FastAPI em `lumina/app.py`

**Commit Semântico Sugerido**: `feat(observability): criar endpoints REST administrativos protegidos por RBAC`

**Checkpoint**: User Stories 1 e 2 funcionais — API REST completa e protegida contra acesso indevido.

---

## Phase 5: User Story 3 - Visualização e Diagnóstico Interativo Simples (Painel / Demo) (Priority: P2)

**Goal**: Criar a interface visual minimalista servida em `/demos/pipeline-observability/` com renderização dinâmica de qualquer etapa.

**Independent Test**: Abrir `/demos/pipeline-observability/` no navegador, autenticar como administrador, visualizar lista de releases, selecionar uma release e verificar etapas renderizadas dinamicamente.

### Implementation for User Story 3
- [x] T016 [US3] Implementar página HTML minimalista com autenticação de persona em `lumina/static/demos/pipeline_observability/index.html`
- [x] T017 [US3] Implementar renderização dinâmica iterativa de etapas (suporte a qualquer etapa futura) e acordeão em `lumina/static/demos/pipeline_observability/index.html`
- [x] T018 [US3] Implementar mecanismo de sanitização restritiva de textos contra XSS em `lumina/static/demos/pipeline_observability/index.html`
- [x] T019 [P] [US3] Adicionar card descritivo da Spec 002 no catálogo central de demonstrações em `lumina/static/demos/index.html`

**Commit Semântico Sugerido**: `feat(observability): criar interface demo de diagnostico com renderizacao dinamica de etapas`

**Checkpoint**: Demonstração interativa operacional atendendo ao Princípio VII da Constituição.

---

## Phase 6: User Story 4 - Diagnóstico Granular de Avaliações Paralelas por Critério (Priority: P2)

**Goal**: Registrar métricas individuais para cada critério avaliado concorrentemente (tempo, pontuação, citações e erros).

**Independent Test**: Executar avaliação paralela de múltiplos critérios e verificar registro individual de cada critério nos eventos e no acordeão da interface.

### Tests for User Story 4
- [x] T020 [P] [US4] Criar testes unitários para a instrumentação de critérios paralelos em `tests/unit/services/test_run_logger.py`

### Implementation for User Story 4
- [x] T021 [US4] Instrumentar captura de tempos e resultados individuais por critério no batch de avaliação em `lumina/services/release_logic_service.py`
- [x] T022 [US4] Consolidar subitens de avaliação no schema `ProcessingStageDetail.items` em `lumina/services/run_logger.py`
- [x] T023 [US4] Renderizar lista de critérios no acordeão expansível da interface em `lumina/static/demos/pipeline_observability/index.html`

**Commit Semântico Sugerido**: `feat(observability): adicionar rastreamento granular de criterios avaliados em paralelo`

**Checkpoint**: Diagnóstico granular de critérios ativo para identificação de gargalos de IA.

---

## Phase 7: User Story 5 - Modo de Depuração Controlada com Salvaguarda de Dados Pessoais (LGPD) (Priority: P3)

**Goal**: Gravar artefatos intermediários quando depuração ativada, garantindo zero persistência de dados pessoais (PII).

**Independent Test**: Executar teste de conformidade que tenta registrar CPF ou nomes não anonimizados e validar que a barreira de sanitização impede o vazamento.

### Tests for User Story 5
- [x] T024 [P] [US5] Criar testes de validação de salvaguarda LGPD garantindo zero PII em logs em `tests/unit/services/test_run_logger.py`

### Implementation for User Story 5
- [x] T025 [US5] Implementar filtro de higienização de payload e barreira contra PII não-anonimizado em `lumina/services/run_logger.py`
- [x] T026 [US5] Configurar flag condicional de depuração `DEBUG_PIPELINE_RUNS` em `lumina/core/settings.py` e `lumina/services/run_logger.py`

**Commit Semântico Sugerido**: `feat(observability): adicionar salvaguardas LGPD e controle de artefatos de depuracao`

**Checkpoint**: Conformidade LGPD e modo de depuração assegurados.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Qualidade final de código, documentação viva MkDocs e validação de regressão

- [x] T027 [P] Documentar arquitetura de observabilidade no MkDocs em `docs/ia-plataforma.md`
- [x] T028 Executar validação de linter e formatação com Ruff via `poetry run ruff check` e `poetry run ruff format`
- [x] T029 Executar bateria completa de testes de regressão com `poetry run task test`
- [x] T030 Executar validação manual completa ponta a ponta seguindo o guia em `specs/002-pipeline-observability/quickstart.md`

**Commit Semântico Sugerido**: `docs(observability): documentar arquitetura no MkDocs e validar suite completa`

---

## Phase 9: Incremento - Mapeamento e Rotação Automática de Logs (FR-015)

**Goal**: Implementar a limpeza automática de arquivos `.jsonl` e linhas do índice excedentes para garantir retenção de no máximo 30 execuções ou 7 dias.

**Independent Test**: Simular a criação de mais de 30 execuções e verificar que a rotina de purga descarta os arquivos mais antigos e sincroniza o `index.jsonl`.

### Tests for Phase 9
- [x] T031 [P] [US1] Criar testes unitários para a política de rotação e limpeza automática em `tests/unit/services/test_run_logger.py`

### Implementation for Phase 9
- [x] T032 [US1] Implementar rotina de expurgo de execuções antigas `purge_old_runs` em `lumina/services/run_logger.py`
- [x] T033 [US1] Integrar chamada de rotação no término de execuções (`complete_run` e `fail_run`) em `lumina/services/run_logger.py`

**Commit Semântico Sugerido**: `feat(observability): implementar rotina de rotacao e retencao automatica de logs`

---

## Phase 10: Incremento - Observabilidade das Macroetapas de Ingestão (FR-013, FR-014.1, 14.2, 14.3)

**Goal**: Capturar variáveis de entrada, estado e saída nas 3 etapas de ingestão (extração, seções, anonimização) e consolidá-las sob a release correspondente.

**Independent Test**: Realizar upload de documento e posterior release, validando a presença das etapas `extraction`, `sections` e `anonymization` com suas variáveis no `{release_id}.jsonl`.

### Tests for Phase 10
- [x] T034 [P] [US1] Criar testes unitários para a captura e consolidação de eventos de ingestão em `tests/unit/services/test_run_logger.py`

### Implementation for Phase 10
- [x] T035 [US1] Instrumentar extração e chunking (páginas, chunks, tamanho médio, tipo de extrator, sanitização) em `lumina/services/vector_service.py`
- [x] T036 [US1] Instrumentar detecção de seções por LLM (janela de 3.000 chars, SectionInfo, taxa de mapeamento) em `lumina/services/vector_service.py`
- [x] T037 [US1] Instrumentar anonimização Presidio LGPD (quantitativos por entidade e chaves de reversão) em `lumina/services/vector_service.py`
- [x] T038 [US1] Consolidar eventos de ingestão do documento no log da release (`{release_id}.jsonl`) em `lumina/services/release_orchestrator.py`

**Commit Semântico Sugerido**: `feat(observability): instrumentar macroetapas de ingestao e consolidacao na release`

---

## Phase 11: Incremento - Mapeamento das Macroetapas de Avaliação, Citações e Síntese (FR-005, FR-008, FR-014.4-14.7)

**Goal**: Registrar variáveis ricas de recuperação semântica (query triplicada e margem), prompt integral, raw output, resolução de coordenadas e síntese executiva OiacIA.

**Independent Test**: Executar uma release e verificar a presença de `retrieval`, `llm_interaction`, detecção de alucinações e texto particionado da síntese.

### Tests for Phase 11
- [x] T039 [P] [US4] Criar testes unitários para captura de retriever, isolamento de falha de schema e síntese em `tests/unit/services/test_run_logger.py`

### Implementation for Phase 11
- [x] T040 [US4] Capturar dados de recuperação semântica (query triplicada, 3 chunks iniciais e expansão MARGIN_SIZE=2) em `lumina/services/release_logic_service.py`
- [x] T041 [US4] Capturar prompt integral e raw output da LLM (em modo debug) e isolar falhas de schema em `schema_validation_error` em `lumina/services/release_logic_service.py`
- [x] T042 [US4] Instrumentar resolução de coordenadas e detecção de citações alucinadas em `lumina/services/release_logic_service.py`
- [x] T043 [US1] Instrumentar síntese executiva OiacIA com seleção de ramos extremos e texto particionado em `lumina/services/release_orchestrator.py`

**Commit Semântico Sugerido**: `feat(observability): instrumentar retriever, avaliacao estruturada e sintese executiva`

---

## Phase 12: Incremento - Interface Demo com Tríade de Sub-Abas e Cópia Rápida (FR-011)

**Goal**: Aprimorar a interface em `/demos/pipeline-observability/` com suporte a sub-abas [Entrada | Estado Interno | Saída] para cada etapa e critério, além de botão de cópia para prompts e raw outputs.

**Independent Test**: Acessar `/demos/pipeline-observability/`, abrir uma release e alternar entre as abas [Entrada | Estado Interno | Saída] de cada etapa e critério, testando o botão de cópia rápida.

### Implementation for Phase 12
- [x] T044 [US3] Implementar componente de sub-abas [Entrada | Estado Interno | Saída] nos cartões de etapas em `lumina/static/demos/pipeline_observability/index.html`
- [x] T045 [US3] Implementar renderização das variáveis das 7 macroetapas em suas respectivas sub-abas em `lumina/static/demos/pipeline_observability/index.html`
- [x] T046 [US3] Adicionar sub-abas e botão de cópia rápida de prompts e saídas brutas na visualização de critérios em `lumina/static/demos/pipeline_observability/index.html`

**Commit Semântico Sugerido**: `feat(observability): implementar navegacao por abas e inspecao rica na interface demo`

---

## Phase 13: Incremento - Validação Final e Documentação MkDocs

**Goal**: Garantir conformidade de linter, bateria completa de testes e atualização da documentação viva no MkDocs.

- [x] T047 [P] Atualizar documentação viva no MkDocs em `docs/ia-plataforma.md` detalhando as 7 macroetapas e retenção
- [x] T048 Executar validação de linter e formatação com Ruff via `poetry run ruff check` e `poetry run ruff format`
- [x] T049 Executar bateria completa de testes de regressão com `poetry run task test`
- [x] T050 Executar validação manual completa ponta a ponta seguindo o roteiro em `specs/002-pipeline-observability/quickstart.md`

**Commit Semântico Sugerido**: `docs(observability): atualizar documentacao das 7 macroetapas e validar suite completa`

---

## Dependências e Ordem de Execução

### Dependências entre Fases

1. **Phase 1 a 8**: Infraestrutura base, MVP e primeira entrega concluídos (Commits `bf2bf46` a `64eaee4`).
2. **Phase 9 (Rotação)**: Depende do motor `RunLogger` existente — execução imediata.
3. **Phase 10 (Ingestão)**: Depende da Phase 9 — Instrumenta `vector_service.py` e consolida em `release_orchestrator.py`.
4. **Phase 11 (Avaliação & Síntese)**: Depende da Phase 10 — Aprofunda captura no lote de avaliação e na síntese.
5. **Phase 12 (UI Rica em Abas)**: Depende das Phases 10 e 11 — Consome todas as variáveis ricas dos eventos na interface.
6. **Phase 13 (Polish & MkDocs)**: Depende de todas as fases implementadas.

---

## Oportunidades de Execução Paralela

- Tarefas marcadas com `[P]` operam em arquivos isolados e sem dependência cruzada:
  - `T031` (testes de rotação) em paralelo com `T032`-`T033`.
  - `T034` (testes de ingestão) em paralelo com `T035`-`T038`.
  - `T039` (testes de avaliação rica) em paralelo com `T040`-`T043`.
  - `T047` (documentação MkDocs) em paralelo com as validações finais.

---

## Estratégia de Entrega dos Incrementos

1. **Incremento 1 (Phase 9)**: Rotação automática de logs (evita crescimento de disco).
2. **Incremento 2 (Phases 10 & 11)**: Coleta profunda de dados das 7 macroetapas no backend.
3. **Incremento 3 (Phase 12)**: Navegação em sub-abas [Entrada | Estado Interno | Saída] e botão de cópia na interface demo.
4. **Incremento 4 (Phase 13)**: Validação de regressão, lint estrito e documentação viva no MkDocs.
