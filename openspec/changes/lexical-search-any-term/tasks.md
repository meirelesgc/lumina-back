## 1. Medição antes da mudança

- [ ] 1.1 Rodar `poetry run task test-ai -k test_retrieval_baseline` no código atual e registrar aqui o placar total das quatro métricas. Verificar que o teste passa com os pisos atuais.

## 2. Testes

- [ ] 2.1 Criar `tests/integration/test_lexical_search.py` com o fixture de módulo que indexa os PDFs anotados por `run_document_ingestion` num `PGVector` com `DeterministicFakeEmbedding` ligado ao `engine` do teste e apaga a coleção no fim. Criar o teste do ramo da issue #16 sobre chunks curtos em português indexados à mão. Verificar que o teste falha com a lista vazia no código atual.
- [ ] 2.2 No mesmo arquivo, criar o teste parametrizado pelos gabaritos dos documentos em português: cada ramo com evidência recebe ao menos um chunk do próprio documento, e a falha lista os ramos vazios. Deixar `smart_tech_microgrids` de fora, com comentário que cita a issue #38. Verificar que o teste falha no código atual para os dois documentos.
- [ ] 2.3 No mesmo arquivo, criar as guardas: nenhum chunk de outro documento nem resumo de seção, ramo com `&`, `|`, `!`, `:`, `(` e aspas sem erro, e ramo só com stopwords devolvendo lista vazia. Verificar que as guardas passam no código atual.

## 3. Implementação

- [ ] 3.1 Em `lexical_search` (`lumina/services/ai/stages/vector_store_sql.py`), trocar `&` por `|` no texto do `plainto_tsquery` e converter de volta para `tsquery`, mantendo filtros e `ts_rank`. Verificar que `poetry run pytest tests/integration/test_lexical_search.py` passa.
- [ ] 3.2 Rodar `poetry run task test-ai -k test_retrieval_baseline` e registrar aqui o placar total. Se uma métrica subir, subir o piso para o valor medido, arredondado para baixo na segunda casa. Se uma métrica cair abaixo do piso, parar e levar o placar ao usuário. Verificar que o teste passa com os pisos gravados.

## 4. Verificação final

- [ ] 4.1 Rodar `poetry run task test` e registrar aqui o resultado que rodou.

## Workflow follow-up

- Commitar os artefatos em `docs(openspec): ...` e o código e os testes em `fix(retrieval): ...`, citando a issue #16.
- Sincronizar a delta spec com `openspec-sync-specs` e arquivar a mudança com `openspec-archive-change`.
