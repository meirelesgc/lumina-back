## 0. Pré-requisito

- [x] 0.1 Verificar que a change `swap-llm-models` está implementada e arquivada (`openspec list` não a mostra como ativa e `lumina/core/llm.py` usa `gpt-6.1-sol` e `gpt-6-luna`).
  - Resultado: `swap-llm-models` arquivada em `bb63969`; `lumina/core/llm.py` usa `gpt-6.1-sol` e `gpt-6-luna`.

## 1. Gabaritos

- [x] 1.1 (Usuário) Anotar `fulfilled` nos 75 ramos com evidência e revisar o escopo dos ramos nos três `<nome>.retrieval.yaml`.
  - Feito no planejamento (commit `6fec47d`): 45 contemplam, 30 não contemplam, 11 ramos em `ENTIRE_DOCUMENT`.
- [x] 1.2 Documentar `fulfilled` em `tests/fixtures/documents/retrieval_template.yaml` e no README do acervo.
  - Feito no planejamento.
- [x] 1.3 Em `tests/unit/services/test_retrieval_answer_keys.py`, verificar que `fulfilled` é booleano, obrigatório nos ramos com evidência e `false` quando presente num ramo com `evidence: []`. É uma guarda: passa com os gabaritos atuais. Verificar que falha numa cópia temporária com `fulfilled` ausente e depois com `fulfilled: true` num ramo vazio.
  - Resultado: `test_veredito_anotado_e_coerente_com_a_evidencia` passa com os três gabaritos e falhou nas duas cópias quebradas (`fulfilled` ausente em `criterios-exclusao-definidos`; `fulfilled: true` em `ferramenta-avaliacao-definida`, que não tem evidência). `expected_fulfilled` foi para `tests/fixtures/answer_keys.py`.

## 2. Linha de base dos veredictos

- [x] 2.1 Criar `tests/ai/evaluation/verdicts/test_verdict_accuracy.py` (`@pytest.mark.ai`) com payload de `retrieve_criteria_payload` sobre o PGVector do container, avaliação por `evaluate_criteria_batch` com o modelo principal, acerto de `fulfilled` e matriz de confusão por documento, ramos sem texto recuperado contados como "não contempla" e piso provisório `0.0`. Verificar que o teste passa e imprime o relatório.
  - Resultado: a ingestão no PGVector passou para a fixture de sessão `indexed_vectorstore` (`tests/ai/evaluation/conftest.py`), compartilhada com o placar de recuperação, porque os dois usam a coleção `langchain`, fixa nas consultas SQL. A construção do PGVector, o filtro do documento e a entrada de cada ramo foram para `tests/ai/evaluation/support.py`. Rodando junto, o placar de recuperação não mudou.
- [x] 2.2 Rodar o teste três vezes e registrar aqui o acerto de cada execução, a mediana (linha de base), o tempo e o commit medido.
  - Resultado (commit medido `bb63969`, modelos `gpt-6.1-sol` e `gpt-6-luna`, cerca de 155 s por execução):

    | Execução | Anteprojeto | Dengue | Microgrids | Total |
    | :--- | ---: | ---: | ---: | ---: |
    | 1 | 10/16 | 61/65 | 45/65 | 116/146 = 0,79 |
    | 2 | 10/16 | 61/65 | 46/65 | 117/146 = 0,80 |
    | 3 | 10/16 | 60/65 | 45/65 | 115/146 = 0,79 |

    Linha de base: mediana de 116/146 (0,79). Nenhum erro de schema. A maior parte dos erros é "falso não contempla": 6 no anteprojeto e 17 a 18 no microgrids.

## 3. Testes do seletor

- [x] 3.1 Criar `tests/unit/services/test_outline.py`: ids na ordem de leitura, páginas inicial e final, tokens estimados, prévia de 200 caracteres sem o prefixo `[título]`, indentação pelo caminho de títulos e texto da seção como sequência dos seus chunks. Verificar que falha antes da mudança, porque o módulo não existe.
  - Resultado: falhou antes da mudança com `ModuleNotFoundError` de `lumina.services.ai.stages.outline`.
- [x] 3.2 Criar `tests/unit/services/test_selection.py` com modelo falso: para quando `enough` é verdadeiro; para no teto de 3 rodadas com as seções lidas; para quando não há id novo; ignora e registra ids inválidos; ignora `not_found` na primeira rodada; manda o documento inteiro quando a primeira rodada não tem id válido; `ENTIRE_DOCUMENT` não chama o modelo; saída malformada é repetida 2 vezes e cai no documento inteiro com a falha registrada; o payload tem as chaves que a avaliação lê, `document` com os marcadores `[FONTE] chunk_id`, `_chunks` das seções escolhidas e `context_selection`; `not_found` gera `fulfilled = False`, `score = 0`, parecer com as seções inspecionadas e `skip_evaluation`. Verificar que falha antes da mudança.
  - Resultado: falhou antes da mudança pelo mesmo motivo. O teste de que a avaliação pula `skip_evaluation` ficou no mesmo arquivo.
- [x] 3.3 Criar `tests/unit/services/test_selection_audit.py`: com a flag ligada, a seleção grava `05_outline/<documento>.md` e `06_selection/<documento>/<ramo>.md`; com a flag desligada, não grava nada. Verificar que falha antes da mudança.
  - Resultado: falhou antes da mudança pelo mesmo motivo.
- [x] 3.4 Criar `tests/ai/evaluation/retrieval/test_outline_selection.py` (`@pytest.mark.ai`) sobre os chunks anonimizados dos gabaritos: recall de trechos, erro e acerto de inexistência, tokens enviados contra os do documento inteiro e rodadas, com relatório por documento e por ramo e pisos provisórios `0.0`. Verificar que falha antes da mudança.
  - Resultado: falhou antes da mudança pelo mesmo motivo. As métricas de inexistência viraram taxas que só sobem: acerto de inexistência (ramos vazios encerrados como "não existe") e segurança de inexistência (ramos com evidência que não foram encerrados assim).

## 4. Seletor

- [x] 4.1 Implementar `lumina/services/ai/stages/outline.py`. Verificar que 3.1 passa.
  - Resultado: 4 testes passam.
- [x] 4.2 Implementar `lumina/services/ai/stages/selection.py`, o schema da rodada e o prompt do seletor em `lumina/prompts.py`, e fazer `evaluate_criteria_batch` pular itens com `skip_evaluation`. Verificar que 3.2 passa e que os testes de `test_evaluation_styles.py` continuam passando.
  - Resultado: os campos comuns do critério (`criteria_fields`), a junção dos mapas do Presidio e o percurso da árvore foram para `stages/criteria.py`, usados pela recuperação e pela seleção; os 19 testes de `test_ai_stages.py` continuam passando. O laço do seletor tem uma saída só. 43 testes passam.
- [x] 4.3 Implementar a gravação de `05_outline` e `06_selection` em `audit.py`. Verificar que 3.3 passa.
  - Resultado: `export_selection_audit` em `audit.py`, com a verificação da flag dentro da função. 8 testes passam, com os de auditoria de ingestão.
- [x] 4.4 Rodar 3.4 três vezes com `gpt-6-luna` e registrar aqui o placar, os tokens e o tempo. Se a mediana do recall não passar de 0,44, repetir com `gpt-6.1-sol` como seletor e registrar.
  - Resultado com `gpt-6-luna` (cerca de 130 s por execução, sem PGVector):

    | Execução | Recall de trechos | Acerto de inexistência | Segurança de inexistência |
    | :--- | ---: | ---: | ---: |
    | 1 | 112/129 = 0,87 | 36/71 = 0,51 | 64/75 = 0,85 |
    | 2 | 113/129 = 0,88 | 33/71 = 0,46 | 65/75 = 0,87 |
    | 3 | 111/129 = 0,86 | 43/71 = 0,61 | 65/75 = 0,87 |

    Mediana do recall: 112/129 (0,87), contra 0,44 da recuperação atual. O `gpt-6.1-sol` não precisou ser testado. Tokens enviados por execução, somados nos ramos avaliados: ~21 mil a ~23 mil no anteprojeto (documento inteiro em todos os ramos: ~45 mil), ~156 mil a ~196 mil no dengue (~963 mil) e ~112 mil a ~131 mil no microgrids (~1,34 milhão). Cerca de 10 ramos com evidência são encerrados como "não existe" em cada execução; os mais frequentes são `intervencao-definida`, `pesquisas-futuras`, `lacuna-cientifica`, `vies-estudos-avaliado`, `processo-documentado`, `variaveis-descritas`, `etapa-elegibilidade-apresentada` e `triagem-inicial`.
- [x] 4.5 Ligar 2.1 ao payload de `select_evaluation_payloads`, rodar três vezes com o seletor que passou em 4.4 e registrar aqui o acerto de cada execução e a mediana. Se a mediana ficar abaixo da linha de base de 2.2 e o seletor for o `gpt-6-luna`, repetir 4.4 e 4.5 com `gpt-6.1-sol`.
  - Resultado com o seletor `gpt-6-luna` (cerca de 170 s por execução). A montagem dos payloads do seletor ficou em `select_answer_key` (`tests/ai/evaluation/support.py`), usada pelo placar do seletor e pelos veredictos:

    | Execução | Anteprojeto | Dengue | Microgrids | Total |
    | :--- | ---: | ---: | ---: | ---: |
    | 1 | 12/16 | 63/65 | 53/65 | 128/146 = 0,88 |
    | 2 | 11/16 | 62/65 | 52/65 | 125/146 = 0,86 |
    | 3 | 13/16 | 60/65 | 51/65 | 124/146 = 0,85 |

    Mediana: 125/146 (0,86), contra 116/146 (0,79) da linha de base. Os "falsos não contempla" caem de 23 a 24 para 14 a 16; os "falsos contempla" ficam entre 2 e 4. Nenhum erro de schema.
- [x] 4.6 Decisão: com recall acima de 0,44 e acerto maior ou igual à linha de base, seguir para o grupo 5 com o seletor aprovado. Se nenhum seletor atingir os dois critérios, parar aqui, registrar os resultados, não executar o grupo 5 e reportar ao usuário.
  - Decisão: recall 0,87 (acima de 0,44) e acerto 0,86 (acima de 0,79). O `gpt-6-luna` fica como seletor e o grupo 5 segue.
- [x] 4.7 Gravar `MIN_SELECTION_RECALL` e os pisos de inexistência em 3.4, e `MIN_FULFILLED_ACCURACY` em 2.1, com o menor valor das três execuções do seletor aprovado, arredondado para baixo na segunda casa. Verificar que os dois testes passam com os pisos.
  - Resultado: `MIN_SELECTION_RECALL = 0.86` (111/129), `MIN_NOT_FOUND_HIT_RATE = 0.46` (33/71), `MIN_NOT_FOUND_SAFETY = 0.85` (64/75) e `MIN_FULFILLED_ACCURACY = 0.84` (124/146). A verificação final roda na tarefa 7.2.

## 5. Integração na avaliação

- [x] 5.1 Criar um teste de integração com modelos falsos para `process_release_pipeline`: todos os ramos da árvore recebem veredito, ramos `not_found` não chamam o avaliador e `AppliedBranch.context_selection` é gravado. Verificar que falha antes da mudança.
  - Resultado: `tests/integration/test_release_pipeline.py` roda `process_release_pipeline` com banco real, extração e anonimização reais sobre o anteprojeto, base vetorial simulada e modelos falsos (um seletor por regra e um modelo que registra os prompts). Antes da mudança, falhou dentro de `retrieve_evaluation_payloads`, porque a avaliação ainda dependia da busca vetorial. A divisão em teste unitário do pipeline e teste de integração do snapshot, prevista no início, não foi necessária: o teste único cobre os três comportamentos.
- [x] 5.2 Criar a migração Alembic da coluna `context_selection` em `applied_branches`, o campo em `AppliedBranch` e a gravação em `save_applied_snapshot`. Verificar `alembic upgrade head` e `alembic downgrade -1` num banco limpo.
  - Resultado: migração `0211df046da3`. Num container `pgvector/pgvector:pg16` limpo, `upgrade head`, `downgrade -1` e `upgrade head` rodaram, e a coluna ficou como `jsonb`.
- [x] 5.3 Fazer `run_document_ingestion` devolver os chunks anonimizados, trocar `retrieve_evaluation_payloads` por `select_evaluation_payloads` em `process_release_pipeline` com o seletor aprovado, deixar de carregar as expansões e remover `retrieve_evaluation_payloads` e os testes dela em `test_ai_stages.py`. Verificar que 5.1 passa.
  - Resultado: além de `retrieve_evaluation_payloads` e dos 2 testes dele, saíram `iter_typifications`, `iter_taxonomies` e `iter_branches`, que só ele usava, e a carga de expansões no pipeline. 5.1 passa.
- [x] 5.4 Trocar no `DOCUMENT_ANALYSIS_PROMPT` "Trechos recuperados do documento" por "Seções do documento" e "trechos" por "seções" nas regras, mantendo as regras de citação. Verificar que `test_evaluation_styles.py` passa.
  - Resultado: o prompt passa a falar em "Seções do documento" e "nas seções"; as regras de citação por `chunk_id` não mudam. `test_evaluation_styles.py` e 5.1 passam. A mudança veio depois da medição dos pisos e é verificada em 7.2.

## 6. Documentação e registros

- [x] 6.1 Atualizar `docs/arquitetura-engenharia.md` (seleção de seções, auditoria `05` e `06`, gabarito de veredictos e os dois testes novos) e `.agents/skills/testing-methodology/references/06-projeto-lumina.md`. Verificar que os nomes citados existem no código.
  - Resultado: `docs/ia-plataforma.md` troca "Recuperação de Evidências por Critério" por "Seleção de Seções por Critério" e ajusta o fluxo, o barema e as diretrizes; `docs/arquitetura-engenharia.md` ganha "Validação da Seleção de Seções e dos Veredictos"; a referência da skill de testes ganha os testes novos e o comando dos veredictos.
- [x] 6.2 Abrir uma issue, pelo modelo `demanda.md`, sobre o destino do serviço de expansões de consulta, que a avaliação deixa de usar, e citar o número aqui e no design.
  - Resultado: issue #28, citada no design e no delta spec.

## 7. Verificação

- [x] 7.1 Rodar `poetry run task test` e `ruff check` e `ruff format --check` nos arquivos alterados, e registrar aqui o resultado.
  - Resultado: 376 testes passam e 12 são pulados (`@pytest.mark.ai`). A cobertura de `lumina/` sobe de 75% para 77%. `ruff format --check` passa nos 31 arquivos Python alterados fora de `lumina/features/`; `ruff check` só acusa 4 erros em `assistant_service.py` (argumentos e linhas longas), os mesmos da `main`, em linhas que esta mudança não tocou.
- [x] 7.2 Rodar `poetry run pytest tests/ai/evaluation -s --run-ai -m ai` e registrar aqui os placares finais de recuperação, seleção e veredictos, e o tempo.
  - Parcial (435 s): 11 testes passam. Seletor: recall 113/129 (0,88), acerto de inexistência 39/71 (0,55), segurança de inexistência 67/75 (0,89), todos acima dos pisos. Recuperação: placar igual ao anterior (recall 58/129). Fumaça dos modelos: 6 passam. O teste de veredictos parou por falta de créditos na OpenAI (erro 429).
  - Os testes do seletor e de veredictos passam a imprimir o consumo por modelo (entrada, cache, saída e raciocínio), separado entre seletor e avaliador no teste de veredictos (`usage_report` em `tests/ai/evaluation/support.py`).
  - Decisão do usuário, por custo: o uso médio passa de `gpt-6.1-sol` para `gpt-6-luna` com `reasoning.effort = medium` (sem `temperature`, que o modelo recusa nesse esforço). Com o novo avaliador, o teste de veredictos deu 115/146 e depois 116/146 (0,79), abaixo do piso de 0,84. `MIN_FULFILLED_ACCURACY` desce para 0,78 (115/146, arredondado para baixo), com a justificativa no design. Na execução que passou (164 s), o seletor consumiu 1.106.806 tokens de entrada (883.897 do cache) e 20.811 de saída, cerca de US$ 0,12; o avaliador, 496.882 de entrada (55.382 do cache) e 48.868 de saída (31.424 de raciocínio), cerca de US$ 0,07.
- [ ] 7.3 Abrir o PR da branch `evaluation-outline-selection` para `main`, sem merge, com os placares e a referência à #26.
