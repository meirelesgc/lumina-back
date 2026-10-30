## 1. Ambiente e linha de base

- [x] 1.1 Rodar `poetry install` na worktree e verificar que `poetry run pytest tests/unit/services/test_ingestion_sections.py tests/unit/services/test_retrieval_answer_keys.py tests/unit/services/test_positioning.py` passa antes de qualquer mudança. Registrar aqui o resultado: esses testes são as guardas da mudança.
  - Resultado: 21 testes passam em 128 s. Com o Docker Desktop, o testcontainers precisa de `DOCKER_HOST=unix:///home/gls/.docker/desktop/docker.sock`.

## 2. Gabarito de linhas corridas e teste sobre o acervo

- [x] 2.1 Em `tests/fixtures/answer_keys.py`, adicionar `RUNNING_SUFFIX = '.running.yaml'`, `RUNNING_KEYS`, a leitura do gabarito (`expected_running_lines` e `expected_keep_lines`), o sufixo novo em `pdf_for` e a comparação só por letras e dígitos sem diferença de caixa. Verificar que `RUNNING_KEYS` encontra os quatro gabaritos já aprovados em `tests/fixtures/documents/`.
- [x] 2.2 Criar `tests/unit/services/test_ingestion_running_lines.py` com a jornada em docstring e dois testes críticos parametrizados por documento: cada `running_line` fora dos chunks das páginas que não estão em `keep_on_pages`, e cada `keep_line` nos chunks da página anotada. O teste junta os chunks de cada página antes de comparar e aponta documento, linha e páginas na falha. Verificar que o teste de `running_lines` falha hoje em `dengue_no_brasil`, `recuperando_especialistas_renovaveis_pln_ueba` e `smart_tech_microgrids`, e que o teste de `keep_lines` passa hoje nos quatro documentos (guarda).
- [x] 2.3 Documentar o gabarito `<nome>.running.yaml` em `tests/fixtures/documents/README.md` e na seção "Validação da Ingestão sobre Acervo Anotado" de `docs/arquitetura-engenharia.md`, com o comando que roda o teste novo. Verificar que o comando documentado roda como escrito.

## 3. Detecção e máscara das linhas corridas

- [x] 3.1 Criar `tests/unit/services/test_running_lines.py` com páginas sintéticas (texto bruto, caixas e altura) para o cleaner: `page-header` repetido em 2 páginas sai; `page-footer` em uma página só fica; caixa `text` na faixa em 3 páginas e 30% delas sai, menos a primeira ocorrência; caixa `text` na faixa abaixo desse limite fica; caixa `text` repetida fora da faixa fica; número de página que muda conta como a mesma linha; caixa `picture` fica; a máscara troca o intervalo por `\n` e mantém o tamanho do texto; páginas sem repetição saem iguais. Verificar que o arquivo falha hoje, porque as funções não existem.
- [x] 3.2 Implementar em `lumina/services/ai/stages/extraction.py` as funções puras de chave da caixa, detecção das caixas corridas e máscara, com as constantes da faixa (12%) e dos limites (2 páginas para `page-header` e `page-footer`; 3 páginas e 30% para as outras). Verificar que `tests/unit/services/test_running_lines.py` passa.
- [x] 3.3 Em `extract_raw_markdown_and_pages`, ler todas as páginas, decidir as caixas corridas, aplicar a máscara no texto bruto antes do `re.sub` de espaços e marcar cada caixa corrida com `'running': True` no `page_map`. Atualizar a docstring. Verificar que `tests/unit/services/test_ingestion_running_lines.py` passa e que as guardas da tarefa 1.1 continuam passando. Se uma guarda falhar, parar e levar o caso ao usuário.
  - Resultado: a primeira rodada teve três falhas, levadas ao usuário. (1) No smart_tech, "Energies 2025, 18, 2676" também aparece no bloco "Citation:" da página 1, que é conteúdo: o gabarito passou a manter a linha na página 1. (2) Na página 1 do recuperando, o rodapé vem junto com a URL da revista numa caixa que não se repete: o usuário aceitou, e o gabarito mantém o rodapé na página 1. (3) A identificação de seções caiu para 62/63 ("REFERÊNCIAS" do recuperando passou da página 23 para a 24, sem perda de texto): o piso baixou de 1.0 para 0.98, com a justificativa no `design.md`. Depois disso, os 40 testes dos cinco arquivos passam.

## 4. Retângulos das citações

- [x] 4.1 Adicionar a `tests/unit/services/test_positioning.py` um caso com uma caixa `text` marcada com `'running': True` e mascarada no markdown: `char_range_to_blocks` não devolve a caixa e `locate_range` não devolve o `bbox` dela. Verificar que o teste falha hoje.
- [x] 4.2 Em `char_range_to_blocks` (`lumina/services/ai/stages/positioning.py`), ignorar as caixas com `running` verdadeiro. Verificar que o teste da tarefa 4.1 e os testes existentes de `test_positioning.py` passam.

## 5. Verificação

- [x] 5.1 Rodar `poetry run task test` e `poetry run ruff check` e `poetry run ruff format --check` nos arquivos alterados. Registrar aqui o resultado que de fato rodou.
  - Resultado: `poetry run task test` passa com 520 testes e 12 pulados, em 7 min 5 s, sem `.env` na worktree. `ruff check` e `ruff format --check` passam nos 7 arquivos Python alterados. O `ruff format` reformatou `extraction.py` e `test_running_lines.py` depois da suíte, e os 19 testes desses dois arquivos de teste rodaram de novo e passaram.
- [x] 5.2 Medir, para cada documento do acervo, o total de chunks e quantos contêm uma linha corrida do gabarito, antes e depois (antes: 49 de 91, 53 de 94, 21 de 119 e 0 de 21). Registrar aqui e na descrição do PR.
  - Resultado, com o mesmo script nos dois lados (texto sem os prefixos `[título]`, só letras e dígitos; "antes" é o código de `main`):

    | Documento | Antes | Depois | Onde a linha ficou |
    | :--- | ---: | ---: | :--- |
    | `dengue_no_brasil.pdf` | 48 de 91 | 1 de 83 | página 1 (título do artigo e primeira linha de autores) |
    | `recuperando_especialistas_renovaveis_pln_ueba.pdf` | 53 de 94 | 2 de 77 | páginas 1 (rodapé com a URL) e 2 (primeira linha de autores) |
    | `smart_tech_microgrids.pdf` | 21 de 119 | 1 de 116 | página 1 (bloco "Citation:") |
    | `estrategias_teste_software_llm_judge_hitl.pdf` | 0 de 21 | 0 de 21 | |

    A contagem de 49 do planejamento incluía os prefixos `[título]`. O total de chunks caiu 8 na dengue, 17 no recuperando e 3 no smart_tech, porque as fatias de página encolheram sem as linhas apagadas.
- [x] 5.3 Rodar `poetry run pytest tests/ai/evaluation/retrieval -s --run-ai -m ai` e registrar aqui o placar de cada métrica. Se alguma ficar abaixo do piso, parar e levar a decisão ao usuário. Se alguma subir, propor subir o piso no mesmo commit.
  - Primeira rodada (com o `.env` do checkout principal ligado na worktree): 1 falha e 4 testes passam, em 4 min 39 s. `test_retrieval_baseline.py`: recall de trechos 71/129 = 0.55 (piso 0.53); acerto de seção e página 73/129 = 0.57 (piso 0.58, abaixo); precisão entre ramos 42/199 = 0.21 (piso 0.19); roteamento 0/64 = 0.00 (piso 0.0). `test_outline_selection.py`: recall 115/129 = 0.89 (piso 0.86); acerto de inexistência 38/71 = 0.54 (piso 0.46); segurança de inexistência 68/75 = 0.91 (piso 0.85). Implementação parada aqui, aguardando decisão do usuário.
  - Comparação com `main` (`7ba30d7`, numa worktree temporária), só `test_retrieval_baseline.py`: recall 69/129 para 71/129, acerto de seção e página 75/129 para 73/129, precisão entre ramos 40/202 para 42/199, roteamento 0/64 nos dois. A segunda rodada da mudança repetiu os números da primeira. Mudaram 5 de 75 ramos. Ganharam recall `desfechos-definidos`, `questao-pesquisa-explicita` e `operadores-booleanos-utilizados`. Perderam `implicacoes-praticas-discutidas` (dengue, "3. Resultados e Discussão" saiu dos blocos) e `justificativa-revisao` (dengue, "1. Introdução" saiu dos blocos, e o chunk do título na página 1 passou a vir primeiro).
  - Decisão do usuário: aceitar a troca. `MIN_SECTION_PAGE_HIT_RATE` baixou para 0.56, `MIN_EVIDENCE_RECALL` subiu para 0.55 e `MIN_BRANCH_PRECISION` para 0.21. Resultado final: 5 testes passam, em 7 min 43 s. `test_retrieval_baseline.py`: 0.55, 0.57, 0.21 e 0.00. `test_outline_selection.py`: recall 112/129 = 0.87, acerto de inexistência 41/71 = 0.58, segurança 65/75 = 0.87. Essas três métricas variaram entre as rodadas, então os pisos delas continuam como estavam.
  - Depois do merge de `main` com a anonymize-person-names: suíte padrão com 531 testes e 12 pulados. `test_retrieval_baseline.py` mediu 70/129 = 0.54, 72/129 = 0.56 (0.5581) e 41/196 = 0.21 (0.2092), abaixo dos pisos 0.55, 0.56 e 0.21. `test_outline_selection.py` mediu 0.91, 0.63 e 0.92. Decisão do usuário: pisos 0.54, 0.55 e 0.20.

## Workflow follow-up

- Commitar os artefatos do OpenSpec (`docs(openspec): ...`) separados do código, dos testes e dos gabaritos (`feat(ingestion): ...`).
- Levar a delta spec para `openspec/specs/ai-pipeline/spec.md` com `openspec-sync-specs` e arquivar a mudança com `openspec-archive-change`.
