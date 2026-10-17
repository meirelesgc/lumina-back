## 0. Pré-requisito

- [ ] 0.1 Verificar que a change `swap-llm-models` está implementada e arquivada (`openspec list` não a mostra como ativa e `lumina/core/llm.py` usa `gpt-6.1-sol` e `gpt-6-luna`).

## 1. Gabaritos

- [x] 1.1 (Usuário) Anotar `fulfilled` nos 75 ramos com evidência e revisar o escopo dos ramos nos três `<nome>.retrieval.yaml`.
  - Feito no planejamento (commit `6fec47d`): 45 contemplam, 30 não contemplam, 11 ramos em `ENTIRE_DOCUMENT`.
- [x] 1.2 Documentar `fulfilled` em `tests/fixtures/documents/retrieval_template.yaml` e no README do acervo.
  - Feito no planejamento.
- [ ] 1.3 Em `tests/unit/services/test_retrieval_answer_keys.py`, verificar que `fulfilled` é booleano, obrigatório nos ramos com evidência e `false` quando presente num ramo com `evidence: []`. É uma guarda: passa com os gabaritos atuais. Verificar que falha numa cópia temporária com `fulfilled` ausente e depois com `fulfilled: true` num ramo vazio.

## 2. Linha de base dos veredictos

- [ ] 2.1 Criar `tests/ai/evaluation/verdicts/test_verdict_accuracy.py` (`@pytest.mark.ai`) com payload de `retrieve_criteria_payload` sobre o PGVector do container, avaliação por `evaluate_criteria_batch` com o modelo principal, acerto de `fulfilled` e matriz de confusão por documento, ramos sem texto recuperado contados como "não contempla" e piso provisório `0.0`. Verificar que o teste passa e imprime o relatório.
- [ ] 2.2 Rodar o teste três vezes e registrar aqui o acerto de cada execução, a mediana (linha de base), o tempo e o commit medido.

## 3. Testes do seletor

- [ ] 3.1 Criar `tests/unit/services/test_outline.py`: ids na ordem de leitura, páginas inicial e final, tokens estimados, prévia de 200 caracteres sem o prefixo `[título]`, indentação pelo caminho de títulos e texto da seção como sequência dos seus chunks. Verificar que falha antes da mudança, porque o módulo não existe.
- [ ] 3.2 Criar `tests/unit/services/test_selection.py` com modelo falso: para quando `enough` é verdadeiro; para no teto de 3 rodadas com as seções lidas; para quando não há id novo; ignora e registra ids inválidos; ignora `not_found` na primeira rodada; manda o documento inteiro quando a primeira rodada não tem id válido; `ENTIRE_DOCUMENT` não chama o modelo; saída malformada é repetida 2 vezes e cai no documento inteiro com a falha registrada; o payload tem as chaves que a avaliação lê, `document` com os marcadores `[FONTE] chunk_id`, `_chunks` das seções escolhidas e `context_selection`; `not_found` gera `fulfilled = False`, `score = 0`, parecer com as seções inspecionadas e `skip_evaluation`. Verificar que falha antes da mudança.
- [ ] 3.3 Criar `tests/unit/services/test_selection_audit.py`: com a flag ligada, a seleção grava `05_outline/<documento>.md` e `06_selection/<documento>/<ramo>.md`; com a flag desligada, não grava nada. Verificar que falha antes da mudança.
- [ ] 3.4 Criar `tests/ai/evaluation/retrieval/test_outline_selection.py` (`@pytest.mark.ai`) sobre os chunks anonimizados dos gabaritos: recall de trechos, erro e acerto de inexistência, tokens enviados contra os do documento inteiro e rodadas, com relatório por documento e por ramo e pisos provisórios `0.0`. Verificar que falha antes da mudança.

## 4. Seletor

- [ ] 4.1 Implementar `lumina/services/ai/stages/outline.py`. Verificar que 3.1 passa.
- [ ] 4.2 Implementar `lumina/services/ai/stages/selection.py`, o schema da rodada e o prompt do seletor em `lumina/prompts.py`, e fazer `evaluate_criteria_batch` pular itens com `skip_evaluation`. Verificar que 3.2 passa e que os testes de `test_evaluation_styles.py` continuam passando.
- [ ] 4.3 Implementar a gravação de `05_outline` e `06_selection` em `audit.py`. Verificar que 3.3 passa.
- [ ] 4.4 Rodar 3.4 três vezes com `gpt-6-luna` e registrar aqui o placar, os tokens e o tempo. Se a mediana do recall não passar de 0,44, repetir com `gpt-6.1-sol` como seletor e registrar.
- [ ] 4.5 Ligar 2.1 ao payload de `select_evaluation_payloads`, rodar três vezes com o seletor que passou em 4.4 e registrar aqui o acerto de cada execução e a mediana. Se a mediana ficar abaixo da linha de base de 2.2 e o seletor for o `gpt-6-luna`, repetir 4.4 e 4.5 com `gpt-6.1-sol`.
- [ ] 4.6 Decisão: com recall acima de 0,44 e acerto maior ou igual à linha de base, seguir para o grupo 5 com o seletor aprovado. Se nenhum seletor atingir os dois critérios, parar aqui, registrar os resultados, não executar o grupo 5 e reportar ao usuário.
- [ ] 4.7 Gravar `MIN_SELECTION_RECALL` e os pisos de inexistência em 3.4, e `MIN_FULFILLED_ACCURACY` em 2.1, com o menor valor das três execuções do seletor aprovado, arredondado para baixo na segunda casa. Verificar que os dois testes passam com os pisos.

## 5. Integração na avaliação

- [ ] 5.1 Criar um teste de integração com modelos falsos para `process_release_pipeline`: todos os ramos da árvore recebem veredito, ramos `not_found` não chamam o avaliador e `AppliedBranch.context_selection` é gravado. Verificar que falha antes da mudança.
- [ ] 5.2 Criar a migração Alembic da coluna `context_selection` em `applied_branches`, o campo em `AppliedBranch` e a gravação em `save_applied_snapshot`. Verificar `alembic upgrade head` e `alembic downgrade -1` num banco limpo.
- [ ] 5.3 Fazer `run_document_ingestion` devolver os chunks anonimizados, trocar `retrieve_evaluation_payloads` por `select_evaluation_payloads` em `process_release_pipeline` com o seletor aprovado, deixar de carregar as expansões e remover `retrieve_evaluation_payloads` e os testes dela em `test_ai_stages.py`. Verificar que 5.1 passa.
- [ ] 5.4 Trocar no `DOCUMENT_ANALYSIS_PROMPT` "Trechos recuperados do documento" por "Seções do documento" e "trechos" por "seções" nas regras, mantendo as regras de citação. Verificar que `test_evaluation_styles.py` passa.

## 6. Documentação e registros

- [ ] 6.1 Atualizar `docs/arquitetura-engenharia.md` (seleção de seções, auditoria `05` e `06`, gabarito de veredictos e os dois testes novos) e `.agents/skills/testing-methodology/references/06-projeto-lumina.md`. Verificar que os nomes citados existem no código.
- [ ] 6.2 Abrir uma issue, pelo modelo `demanda.md`, sobre o destino do serviço de expansões de consulta, que a avaliação deixa de usar, e citar o número aqui e no design.

## 7. Verificação

- [ ] 7.1 Rodar `poetry run task test` e `ruff check` e `ruff format --check` nos arquivos alterados, e registrar aqui o resultado.
- [ ] 7.2 Rodar `poetry run pytest tests/ai/evaluation -s --run-ai -m ai` e registrar aqui os placares finais de recuperação, seleção e veredictos, e o tempo.
- [ ] 7.3 Abrir o PR da branch `evaluation-outline-selection` para `main`, sem merge, com os placares e a referência à #26.
