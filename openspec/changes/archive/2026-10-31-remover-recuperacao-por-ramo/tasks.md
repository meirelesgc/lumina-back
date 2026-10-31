# Tasks

## 1. Testes de jornada e de risco

- [x] 1.1 Em `tests/integration/routers/check_tree/test_branches.py`, criar `test_configurador_cria_e_edita_ramo_sem_chamar_modelo`: (1) cria um ramo pela API e vê o ramo na resposta; (2) edita a descrição e vê o novo texto; (3) confere que o modelo rápido substituto não recebeu chamada. Verificar que o teste falha no código atual.
- [x] 1.2 Em `tests/integration/test_tree_suggestion_service.py`, trocar `test_confirm_chain_and_dispatch_branch_enrichment` por `test_revisor_confirma_cadeia_de_sugestoes_sem_chamar_modelo`, que confirma a cadeia até o ramo e vê o ramo aplicado sem chamada de modelo nem tarefa agendada. Verificar que o teste falha no código atual.
- [x] 1.3 Em `tests/integration/test_release_pipeline.py`, criar o teste de que a ingestão de um PDF envia à base vetorial só documentos sem `record_type`. Verificar que o teste falha no código atual.
- [x] 1.4 Criar `tests/integration/test_remove_branch_retrieval_migration.py` no padrão de `tests/integration/test_branch_section_scope_migration.py`: base separada em `0adaecd70bea`, um ramo com expansão, um veredito com versão, um chunk e um resumo em `langchain_pg_embedding`. Depois do upgrade, a tabela e a coluna somem, o resumo some e o chunk fica. Depois do `downgrade -1`, a tabela e a coluna voltam vazias. Verificar também o upgrade sem `langchain_pg_embedding`. Verificar que o teste falha antes da migração existir.

## 2. Remoção das expansões

- [x] 2.1 Remover `query_expansion_service.py`, `branch_query_expansion_repo.py`, `scripts/enrich_existing_branches.py`, a tarefa `enrich-branches` do `pyproject.toml`, os schemas de expansão e seus testes (`test_query_expansion_service.py`, `test_branch_query_expansion_repo.py`, `test_enrich_existing_branches.py`). Verificar com `grep -rni 'expansion' lumina tests/unit tests/integration` que só restam a migração e o teste dela. A busca não inclui `migrations/`, e `expand_and_merge_neighbors` sai no grupo 3.
- [x] 2.2 Remover de `branch_service.py` a montagem de `BranchNormativeContext`, `_dispatch_background`, `dispatch_branch_enrichment` e `build_branch_context`, e tirar `background_tasks` de `create_branch`, `update_branch`, `confirm_item` e das rotas. Atualizar `test_branch_service.py`. Verificar que os testes 1.1 e 1.2 passam.
- [x] 2.3 Remover `BranchQueryExpansion` e `AppliedBranch.expansion_generation_version` de `models.py`, a escrita em `pipeline.py` e em `selection.py`, o `monkeypatch` de `tests/conftest.py` e a menção em `lumina/core/llm.py`. Verificar com `poetry run pytest tests/unit`.

## 3. Remoção da recuperação por ramo

- [x] 3.1 Remover de `retrieval.py` tudo que não está na lista de `design.md`, apagar `reranking.py`, `fetch_chunk_siblings` e `CROSS_ENCODER_RERANKING_ENABLED`, e ajustar `stages/__init__.py`. Verificar com `poetry run ruff check`.
- [x] 3.2 Remover `build_section_summary_documents`, as constantes de resumo e a chamada em `run_document_ingestion`. Verificar que o teste 1.3 passa.
- [x] 3.3 Tirar `record_type` de `get_base_filter` e `lexical_search`. Ajustar `test_ai_stages.py`, removendo os testes das funções apagadas. Reescrever `tests/integration/test_lexical_search.py` sobre `lexical_search`, cobrindo os cenários de "Recuperação Híbrida do Chat". Verificar que esse arquivo passa.
- [x] 3.4 Remover `tests/ai/evaluation/retrieval/test_retrieval_baseline.py` e os auxiliares que só ele usava em `tests/fixtures/answer_keys.py` e `tests/ai/evaluation/support.py`. Tirar `expansions` dos gabaritos e do modelo e reescrever o comentário de `section_requirement`. Verificar com `poetry run pytest tests/unit/services/test_retrieval_answer_keys.py`.

## 4. Migração

- [x] 4.1 Criar a revisão Alembic sobre `0adaecd70bea` com o `upgrade` e o `downgrade` de `design.md`. Verificar que o teste 1.4 passa e que `poetry run alembic check` não aponta diferença nos objetos desta mudança. A checagem já acusa, antes desta revisão, `add_fk` nas chaves de auditoria de outras tabelas.

## 5. Documentação e fechamento

- [x] 5.1 Atualizar `docs/ia-plataforma.md`, `docs/arquitetura-engenharia.md`, `docs/base-de-conhecimento.md` e `tests/fixtures/documents/README.md`, tirando expansões, resumos de seção, roteamento e o placar de recuperação. Verificar com `grep -nE 'retrieve_criteria_payload|test_retrieval_baseline|section_summary' docs tests/fixtures/documents/README.md`, sem resultado.
- [x] 5.2 Rodar a suíte padrão com `poetry run pytest` e registrar o resultado (546 aprovados, 9 pulados). Rodar `poetry run pytest tests/ai/evaluation/retrieval/test_outline_selection.py -s --run-ai -m ai`, se houver credenciais, e conferir que os pisos não caem (recall 0,89, acerto de inexistência 0,59, segurança de inexistência 0,88).

## Workflow follow-up

- Levar as delta specs para as specs principais com `openspec-sync-specs` e arquivar a mudança com `openspec-archive-change`.
- Commitar os artefatos em `docs(openspec): ...`, e o código e os testes em `fix(...)` ou `refactor(...)`.
- Abrir o PR com o aviso de perda de dados e a lista do que sai.
- Propor a issue sobre a avaliação própria do chat, com o modelo `.github/ISSUE_TEMPLATE/demanda.md`.
