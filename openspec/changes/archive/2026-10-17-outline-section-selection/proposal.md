## Why

A avaliação de cada critério recebe até 5 blocos que a busca vetorial e léxica escolhe. No acervo anotado, o trecho que o avaliador precisa chega em 58 de 129 casos (0,44), e só 18% dos blocos anotados que chegam são do próprio ramo. O roteamento por seção nunca liga (0 de 72). Os documentos avaliados têm de 3 mil a 21 mil tokens e cabem inteiros no contexto do modelo. O gargalo é a escolha do contexto (issue #26).

## What Changes

- **Sumário do documento:** a partir das seções e chunks da ingestão, com id, caminho de títulos, páginas, tokens estimados e o começo do texto de cada seção, em Markdown.
- **Seletor de seções:** um modelo rápido, separado do avaliador, recebe o ramo e o sumário, pede seções pelo id, lê o texto integral, decide se basta, pede outras ou conclui que o conteúdo não existe no documento. São no máximo 3 rodadas. "Não existe" só vale depois de ao menos uma leitura.
- **Escopos:** `ENTIRE_DOCUMENT` manda o documento inteiro, sem seletor. `SPECIFIC_SECTION` e `UNKNOWN` passam pelo seletor, que recebe o `expected_section` como dica quando existir.
- **Avaliação:** recebe as seções selecionadas com os marcadores de chunk atuais, então as citações e o destaque no PDF não mudam. O prompt passa a falar em seções do documento, e não em trechos recuperados.
- **Conteúdo inexistente:** o critério recebe "não contempla", nota 0 e um parecer padrão com as seções inspecionadas, sem chamar o avaliador.
- **BREAKING (comportamento):** a seleção substitui a recuperação na avaliação, sem chave de configuração. Todo critério da árvore passa a ter veredito. Hoje, critérios sem trecho recuperado ficam sem parecer.
- **Registro:** cada veredito guarda a seleção que o gerou (seções, motivo, rodadas, tokens), numa coluna nova de `applied_branches`.
- **Auditoria:** com `DEBUG_INGESTION_AUDIT=True`, o sumário e a seleção de cada ramo vão para `05_outline/` e `06_selection/`.
- **Gabarito de veredictos:** `fulfilled` nos `<nome>.retrieval.yaml`, validado pelo teste de consistência.
- **Medição:** a linha de base do acerto de `fulfilled` é medida com a recuperação atual antes da troca. Um placar do seletor (recall de trechos, acerto de "não existe", tokens e rodadas) fica sobre o acervo.
- **Critério de aceite:** recall do seletor acima de 0,44 **e** acerto de `fulfilled` maior ou igual ao da linha de base. Sem os dois, a seleção não entra na avaliação.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: adiciona a seleção de seções pelo sumário e o critério de aceite dela sobre o acervo; altera a avaliação estruturada para usar seções selecionadas e a auditoria para incluir sumário e seleção; remove a fusão de consultas expandidas do contexto da avaliação.

## Impact

- **Código:** novo `lumina/services/ai/stages/outline.py` e `selection.py`; `pipeline.py` (`run_document_ingestion`, `process_release_pipeline`, `save_applied_snapshot`), `evaluation.py`, `audit.py`, `prompts.py`, `models.py`; `retrieval.py` perde `retrieve_evaluation_payloads`.
- **Banco:** migração com a coluna `context_selection` (JSON, opcional) em `applied_branches`.
- **Comportamento observável:** pareceres baseados em seções inteiras, veredito para todos os critérios e "não contempla" direto quando o seletor conclui que o conteúdo não existe. Citações, destaque no PDF e frontend não mudam.
- **Chat:** não muda. A ingestão continua gerando embeddings para ele.
- **Testes:** `tests/unit/services/test_outline.py`, `test_selection.py`, `test_selection_audit.py`, casos novos em `test_retrieval_answer_keys.py` e `test_ai_stages.py`; `tests/ai/evaluation/retrieval/test_outline_selection.py` e `tests/ai/evaluation/verdicts/test_verdict_accuracy.py`.
- **Dependência:** a change `swap-llm-models` precisa estar implementada e arquivada antes, para que a linha de base dos veredictos use os modelos definitivos.
