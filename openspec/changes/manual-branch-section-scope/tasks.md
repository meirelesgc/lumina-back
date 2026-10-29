## 1. Testes da marcação pela API

- [ ] 1.1 Em `tests/integration/routers/check_tree/test_branches.py`, criar o teste da jornada `test_configurador_marca_secao_do_ramo_e_edicao_preserva_marcacao`: (1) cria um ramo com `SPECIFIC_SECTION` e "Metodologia" e vê os dois campos na resposta; (2) consulta `GET /branch/{id}` e vê a mesma marcação; (3) edita só o título e vê a marcação mantida; (4) envia `ENTIRE_DOCUMENT` e vê a seção esperada vazia; (5) envia `UNKNOWN` e vê o ramo sem marcação. Verificar que o teste falha no código atual.
- [ ] 1.2 No mesmo arquivo, criar o teste de que um ramo criado só com título, descrição e taxonomia volta com `UNKNOWN` e sem seção esperada. Verificar que o teste falha no código atual.
- [ ] 1.3 No mesmo arquivo, criar o teste parametrizado dos 422 em `POST` e `PUT`: `SPECIFIC_SECTION` sem seção, `SPECIFIC_SECTION` com seção só de espaços, seção com `ENTIRE_DOCUMENT`, seção com `UNKNOWN`, seção sem escopo no `PUT` e escopo fora do enum. No `PUT`, consultar o ramo depois e conferir que a marcação não mudou. Verificar que o teste falha no código atual.
- [ ] 1.4 Em `tests/unit/services/test_branch_service.py`, trocar `test_dispatch_branch_enrichment_schedules_both_tasks` por um teste de que `dispatch_branch_enrichment` agenda só a tarefa de expansão. Verificar que o teste falha no código atual.

## 2. Testes da avaliação e da migração

- [ ] 2.1 Em `tests/integration/test_release_pipeline.py`, criar ramos marcados (um com `ENTIRE_DOCUMENT`, um com `SPECIFIC_SECTION` e "Objetivos") e verificar, com o seletor falso, que o ramo de documento inteiro recebe todas as seções sem chamar o seletor, que o prompt do seletor do outro ramo traz "Objetivos", e que `context_selection` grava `scope` e `expected_section` de cada um. Verificar que o teste falha no código atual.
- [ ] 2.2 Em `tests/unit/services/test_selection.py`, trocar o teste que passa `section_requirements_by_branch` e confere `section_requirement_version` por um que monta o requisito a partir de `section_scope` e `expected_section` do ramo. Verificar que o teste falha no código atual.
- [ ] 2.3 Criar `tests/integration/test_branch_section_scope_migration.py` no padrão de `tests/integration/check_tree/test_document_groups_repo.py`: base separada, `alembic upgrade ad86bd43da06`, um ramo com linha em `branch_section_requirements`, upgrade até a nova cabeça, ramo com `UNKNOWN` e sem seção, tabela antiga inexistente, `downgrade -1` e tabela de volta vazia. Verificar que o teste falha antes da migração existir.

## 3. Marcação no ramo

- [ ] 3.1 Em `lumina/models.py`, adicionar `section_scope` (não nulo, `server_default='UNKNOWN'`) e `expected_section` (nulo) a `Branch`, remover o modelo `BranchSectionRequirement` e a coluna `AppliedBranch.section_requirement_version`.
- [ ] 3.2 Criar a revisão Alembic sobre `ad86bd43da06` com o `upgrade` e o `downgrade` descritos em `design.md`. Verificar que o teste da tarefa 2.3 passa.
- [ ] 3.3 Em `lumina/schemas/branch.py`, adicionar os campos a `BranchCreate`, `BranchUpdate` e `BranchPublic` com o validador do par descrito em `design.md`, e remover o schema `BranchSectionRequirement`.
- [ ] 3.4 Em `lumina/services/branch_service.py`, gravar a marcação na criação e, na edição, só quando `section_scope` estiver em `model_fields_set`. Verificar que os testes das tarefas 1.1 a 1.3 passam.

## 4. Avaliação pela marcação do ramo

- [ ] 4.1 Em `lumina/services/ai/stages/selection.py`, montar o requisito a partir do ramo em `select_evaluation_payloads`, remover o parâmetro `section_requirements_by_branch` e `section_requirement_version`, e adicionar `expected_section` a `SectionSelection`.
- [ ] 4.2 Em `lumina/services/ai/pipeline.py`, remover a leitura de `branch_section_requirement_repo` e a gravação de `section_requirement_version` em `save_applied_snapshot`. Verificar que os testes das tarefas 2.1 e 2.2 passam.

## 5. Remoção do classificador

- [ ] 5.1 Mover `BranchNormativeContext` para `lumina/services/ai/query_expansion_service.py`, ajustar as importações em `branch_service.py`, `enrich_existing_branches.py` e nos testes, e fazer `dispatch_branch_enrichment` disparar só as expansões. Verificar que o teste da tarefa 1.4 passa.
- [ ] 5.2 Remover a parte de seção de `lumina/scripts/enrich_existing_branches.py` e ajustar `tests/unit/scripts/test_enrich_existing_branches.py`.
- [ ] 5.3 Apagar `lumina/services/ai/branch_analyzer.py`, `lumina/repositories/branch_section_requirement_repo.py`, `lumina/scripts/analyze_existing_branches.py`, a tarefa `analyze-branches` do `pyproject.toml` e os testes `tests/unit/services/test_branch_analyzer.py`, `tests/unit/scripts/test_analyze_existing_branches.py` e `tests/integration/repositories/test_branch_section_requirement_repo.py`. Tirar a exportação de `BranchSectionRequirement` em `lumina/schemas/__init__.py`.
- [ ] 5.4 Em `tests/conftest.py`, remover o mock do analisador e a entrada de `branch_analyzer` em `isolate_background_task_db_writes`. Atualizar `.agents/skills/testing-methodology/references/06-projeto-lumina.md`, que cita `branch_analyzer`.
- [ ] 5.5 Rodar `git grep -n "branch_analyzer\|branch_section_requirement\|section_requirement_version\|analyze-branches"` e verificar que só sobram as migrações antigas e os artefatos arquivados do OpenSpec.

## 6. Verificação final

- [ ] 6.1 Rodar `poetry run pytest tests/ai/evaluation/retrieval/test_outline_selection.py -s --run-ai -m ai` e registrar aqui o placar. O teste lê a marcação do gabarito, então o placar deve continuar nos pisos.
- [ ] 6.2 Rodar `poetry run task test` e registrar aqui o resultado que rodou.

## Workflow follow-up

- Commitar os artefatos em `docs(openspec): ...` e o código e os testes em `feat(branch): ...`, citando a issue #17.
- Comentar na issue #23 que o requisito de seção deixou de ser gerado por LLM, e que sobra só a parte das expansões.
- Sincronizar as delta specs com `openspec-sync-specs` e arquivar a mudança com `openspec-archive-change`.
