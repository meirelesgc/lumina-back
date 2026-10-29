## 1. Ambiente e linha de base

- [ ] 1.1 Rodar `poetry install` na worktree e verificar que `poetry run pytest tests/unit/services/test_ingestion_sections.py tests/unit/services/test_retrieval_answer_keys.py tests/unit/services/test_positioning.py` passa antes de qualquer mudança. Registrar aqui o resultado: esses testes são as guardas da mudança.

## 2. Gabarito de linhas corridas e teste sobre o acervo

- [ ] 2.1 Em `tests/fixtures/answer_keys.py`, adicionar `RUNNING_SUFFIX = '.running.yaml'`, `RUNNING_KEYS`, a leitura do gabarito (`expected_running_lines` e `expected_keep_lines`), o sufixo novo em `pdf_for` e a comparação só por letras e dígitos sem diferença de caixa. Verificar que `RUNNING_KEYS` encontra os quatro gabaritos já aprovados em `tests/fixtures/documents/`.
- [ ] 2.2 Criar `tests/unit/services/test_ingestion_running_lines.py` com a jornada em docstring e dois testes críticos parametrizados por documento: cada `running_line` fora dos chunks das páginas que não estão em `keep_on_pages`, e cada `keep_line` nos chunks da página anotada. O teste junta os chunks de cada página antes de comparar e aponta documento, linha e páginas na falha. Verificar que o teste de `running_lines` falha hoje em `dengue_no_brasil`, `recuperando_especialistas_renovaveis_pln_ueba` e `smart_tech_microgrids`, e que o teste de `keep_lines` passa hoje nos quatro documentos (guarda).
- [ ] 2.3 Documentar o gabarito `<nome>.running.yaml` em `tests/fixtures/documents/README.md` e na seção "Validação da Ingestão sobre Acervo Anotado" de `docs/arquitetura-engenharia.md`, com o comando que roda o teste novo. Verificar que o comando documentado roda como escrito.

## 3. Detecção e máscara das linhas corridas

- [ ] 3.1 Criar `tests/unit/services/test_running_lines.py` com páginas sintéticas (texto bruto, caixas e altura) para o cleaner: `page-header` repetido em 2 páginas sai; `page-footer` em uma página só fica; caixa `text` na faixa em 3 páginas e 30% delas sai, menos a primeira ocorrência; caixa `text` na faixa abaixo desse limite fica; caixa `text` repetida fora da faixa fica; número de página que muda conta como a mesma linha; caixa `picture` fica; a máscara troca o intervalo por `\n` e mantém o tamanho do texto; páginas sem repetição saem iguais. Verificar que o arquivo falha hoje, porque as funções não existem.
- [ ] 3.2 Implementar em `lumina/services/ai/stages/extraction.py` as funções puras de chave da caixa, detecção das caixas corridas e máscara, com as constantes da faixa (12%) e dos limites (2 páginas para `page-header` e `page-footer`; 3 páginas e 30% para as outras). Verificar que `tests/unit/services/test_running_lines.py` passa.
- [ ] 3.3 Em `extract_raw_markdown_and_pages`, ler todas as páginas, decidir as caixas corridas, aplicar a máscara no texto bruto antes do `re.sub` de espaços e marcar cada caixa corrida com `'running': True` no `page_map`. Atualizar a docstring. Verificar que `tests/unit/services/test_ingestion_running_lines.py` passa e que as guardas da tarefa 1.1 continuam passando. Se uma guarda falhar, parar e levar o caso ao usuário.

## 4. Retângulos das citações

- [ ] 4.1 Adicionar a `tests/unit/services/test_positioning.py` um caso com uma caixa `text` marcada com `'running': True` e mascarada no markdown: `char_range_to_blocks` não devolve a caixa e `locate_range` não devolve o `bbox` dela. Verificar que o teste falha hoje.
- [ ] 4.2 Em `char_range_to_blocks` (`lumina/services/ai/stages/positioning.py`), ignorar as caixas com `running` verdadeiro. Verificar que o teste da tarefa 4.1 e os testes existentes de `test_positioning.py` passam.

## 5. Verificação

- [ ] 5.1 Rodar `poetry run task test` e `poetry run ruff check` e `poetry run ruff format --check` nos arquivos alterados. Registrar aqui o resultado que de fato rodou.
- [ ] 5.2 Medir, para cada documento do acervo, o total de chunks e quantos contêm uma linha corrida do gabarito, antes e depois (antes: 49 de 91, 53 de 94, 21 de 119 e 0 de 21). Registrar aqui e na descrição do PR.
- [ ] 5.3 Rodar `poetry run pytest tests/ai/evaluation/retrieval -s --run-ai -m ai` e registrar aqui o placar de cada métrica. Se alguma ficar abaixo do piso, parar e levar a decisão ao usuário. Se alguma subir, propor subir o piso no mesmo commit.

## Workflow follow-up

- Commitar os artefatos do OpenSpec (`docs(openspec): ...`) separados do código, dos testes e dos gabaritos (`feat(ingestion): ...`).
- Levar a delta spec para `openspec/specs/ai-pipeline/spec.md` com `openspec-sync-specs` e arquivar a mudança com `openspec-archive-change`.
