## 1. Medição antes da mudança

- [x] 1.1 Rodar `poetry run task test-ai -k test_retrieval_baseline` no código atual e registrar aqui o placar total das quatro métricas. Verificar que o teste passa com os pisos atuais.
  - Resultado (4 passed): recall de trechos 58/129 = 0,45 (piso 0,44), seção e página 63/129 = 0,49 (piso 0,48), precisão entre ramos 36/200 = 0,18 (piso 0,18), roteamento 0/64 = 0,00 (piso 0,0).

## 2. Testes

- [x] 2.1 Criar `tests/integration/test_lexical_search.py` com o fixture de módulo que indexa os PDFs anotados por `run_document_ingestion` num `PGVector` com `DeterministicFakeEmbedding` ligado ao `engine` do teste e apaga a coleção no fim. Criar o teste do ramo da issue #16 sobre chunks curtos em português indexados à mão. Verificar que o teste falha com a lista vazia no código atual.
- [x] 2.2 No mesmo arquivo, criar o teste parametrizado pelos gabaritos dos documentos em português: cada ramo com evidência recebe ao menos um chunk do próprio documento, e a falha lista os ramos vazios. Deixar `smart_tech_microgrids` de fora, com comentário que cita a issue #38. Verificar que o teste falha no código atual para os dois documentos.
- [x] 2.3 No mesmo arquivo, criar as guardas: nenhum chunk de outro documento nem resumo de seção, ramo com `&`, `|`, `!`, `:`, `(` e aspas sem erro, e ramo só com stopwords devolvendo lista vazia. Verificar que as guardas passam no código atual.

## 3. Implementação do OR

- [x] 3.1 Em `lexical_search` (`lumina/services/ai/stages/vector_store_sql.py`), trocar `&` por `|` no texto do `plainto_tsquery` e converter de volta para `tsquery`, mantendo filtros e `ts_rank`. Verificar que `poetry run pytest tests/integration/test_lexical_search.py` passa.
- [x] 3.2 Rodar `poetry run task test-ai -k test_retrieval_baseline` e registrar aqui o placar total. Se uma métrica cair abaixo do piso, parar e levar o placar ao usuário.
  - Resultado (1 failed, 3 passed): recall de trechos 57/129 = 0,44 (piso 0,44), seção e página 61/129 = 0,47 (piso 0,48), precisão entre ramos 37/201 = 0,18 (piso 0,18), roteamento 0/64 = 0,00. O baseline do código anterior, rodado de novo num worktree, repetiu 0,45 / 0,49 / 0,18 / 0,00.
  - Ramos que perderam: `objetivo-analise` (4/4 para 0/4) e `justificativa-relevancia` (4/4 para 3/4) no anteprojeto, `desfechos-definidos`, `justificativa-revisao` e `questao-pesquisa-explicita` (seção e página) na dengue, `formulario-extracao-definido`, `etapa-inclusao-apresentada` e `datas-busca-informadas` nos microgrids.
  - O usuário escolheu investigar. A medição das variantes está em `design.md`, e o usuário aprovou a consulta só com o título e o `ts_rank` normalizado (grupo 4).

## 4. Consulta pelo título e `ts_rank` normalizado

- [ ] 4.1 Em `tests/integration/test_lexical_search.py`, trocar a consulta do teste parametrizado pelo título do ramo e criar o teste do chunk longo com termos repetidos. Verificar que o teste do chunk longo falha no código da tarefa 3.1 e que o parametrizado passa ou aponta os ramos vazios.
- [ ] 4.2 Em `tests/unit/services/test_ai_stages.py`, criar o teste de `retrieve_criteria_payload` que espiona `lexical_search` e confere que ele recebe só o título do ramo, enquanto a busca vetorial recebe título e descrição. Verificar que o teste falha no código da tarefa 3.1.
- [ ] 4.3 Passar `ts_rank` para a normalização 2 em `lexical_search` e o título do ramo para `lexical_search` em `retrieve_criteria_payload`. Verificar que os testes das tarefas 4.1 e 4.2 e o resto de `tests/integration/test_lexical_search.py` passam.
- [ ] 4.4 Rodar `poetry run task test-ai -k test_retrieval_baseline` e registrar aqui o placar total. Subir cada piso que subiu para o valor medido, arredondado para baixo na segunda casa. Se uma métrica cair abaixo do piso, parar e levar o placar ao usuário. Verificar que o teste passa com os pisos gravados.

## 5. Verificação final

- [ ] 5.1 Rodar `poetry run task test` e registrar aqui o resultado que rodou.
  - Rodada com a correção da 3.1: 494 passed, 12 skipped, cobertura 80%.

## Workflow follow-up

- Commitar os artefatos em `docs(openspec): ...` e o código e os testes em `fix(retrieval): ...`, citando a issue #16.
- Comentar na issue #37 que a consulta léxica passou a usar só o título.
- Sincronizar a delta spec com `openspec-sync-specs` e arquivar a mudança com `openspec-archive-change`.
