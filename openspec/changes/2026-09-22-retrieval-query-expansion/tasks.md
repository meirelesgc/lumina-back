## 1. Base de Conhecimento — Query Expansion (Fase 1)

- [x] 1.1 Criar modelo `BranchQueryExpansion` em `lumina/models.py` e coluna
      `expansion_generation_version` em `AppliedBranch`
- [x] 1.2 Gerar migrations `3505c2db872a` (criação de `branch_query_expansions`) e
      `46b17d59cdce` (coluna em `applied_branches`)
- [x] 1.3 Adicionar schemas `ExpansionType`, `QueryExpansionItem`, `QueryExpansionList` em
      `lumina/schemas/branch.py`
- [x] 1.4 Criar `lumina/repositories/branch_query_expansion_repo.py`
      (`add`, `list_active_grouped`, `deactivate_active`, `get_latest_generation_version`)
- [x] 1.5 Criar `lumina/services/ai/query_expansion_service.py`
      (`generate_query_expansions`, `persist_branch_expansions`,
      `run_branch_query_expansion_background`)
- [x] 1.6 Disparar geração em background em `branch_service.create_branch` e em
      `branch_service.update_branch` (quando título/descrição mudam); repassar
      `BackgroundTasks` em `routers/check_tree/branches.py::update_branch`

## 2. Retrieval com Reciprocal Rank Fusion

- [x] 2.1 Implementar `reciprocal_rank_fusion` em
      `lumina/services/ai/stages/retrieval.py`
- [x] 2.2 Adaptar `retrieve_criteria_payload` para buscar em paralelo a consulta original e as
      expansões ativas, fundindo via RRF
- [x] 2.3 Adaptar `retrieve_evaluation_payloads` para aceitar `expansions_by_branch` e anexar
      `expansion_generation_version` ao payload
- [x] 2.4 Orquestrar a busca de expansões ativas em `pipeline.process_release_pipeline` e
      congelar `expansion_generation_version` em `AppliedBranch` (`save_applied_snapshot`)

## 3. Contextualização de Chunk (Fase 6 — mock)

- [x] 3.1 Adicionar flag `CONTEXTUAL_CHUNK_ENRICHMENT_ENABLED` em `lumina/core/settings.py`
- [x] 3.2 Criar `lumina/services/ai/stages/contextualization.py`
      (`DocumentMetadata`, `generate_chunk_context` mockado)
- [x] 3.3 Condicionar a chamada em `create_chunks_from_sections`
      (`lumina/services/ai/stages/chunking.py`) à flag
- [x] 3.4 Criar issue de rastreamento no GitHub para a implementação futura

## 4. Testes e Validação

- [x] 4.1 Testes unitários de `query_expansion_service` (geração, fallback, versionamento,
      background)
- [x] 4.2 Testes de integração de `branch_query_expansion_repo`
- [x] 4.3 Testes de `reciprocal_rank_fusion` e de `retrieve_criteria_payload` /
      `retrieve_evaluation_payloads` com expansões
- [x] 4.4 Testes de disparo de background task em `branch_service` (create/update)
- [x] 4.5 Testes de chamada condicional de `generate_chunk_context` no chunking
- [x] 4.6 Executar `poetry run ruff check` e `poetry run task test` e confirmar suíte completa
      passando
