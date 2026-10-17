## Why

O Lumina passa a usar dois modelos por tipo de uso: `gpt-6-luna` para chamadas rápidas e simples e `gpt-6.1-sol` para chamadas médias e equilibradas. Hoje o código usa `gpt-5-mini` como modelo principal, `gpt-4o-mini` como modelo rápido e `gpt-5.4` e `gpt-5.4-mini` nos módulos de visão, cada um configurado num lugar.

Os modelos novos respondem pela Responses API, e o LangChain devolve o conteúdo como lista de blocos, e não como texto. A avaliação converte esse conteúdo com `str(...)`: o parser de JSON falha e o código grava "não contempla" com o parecer "Erro na validação de schema", sem aviso. A síntese e o chat quebram ou devolvem a lista ao frontend. A troca precisa vir antes do seletor de seções (#26), porque a linha de base dos veredictos tem que ser medida com o modelo que vai ficar.

## What Changes

- Modelo rápido: `gpt-6-luna` com `reasoning.effort = none` e `temperature = 0`. Usado por `branch_analyzer`, expansão de consultas, sugestão de árvore e `template_check`.
- Modelo principal: `gpt-6.1-sol` com `reasoning.effort = medium`, sem `temperature`, que a API recusa nesse modelo. Usado pela avaliação, síntese, chat, assistente, sugestão de árvore e `abnt_check`.
- Os nomes e parâmetros dos dois modelos ficam num único lugar, e os módulos de visão passam a importá-los.
- O texto da resposta passa a ser lido de forma independente do formato do conteúdo na avaliação, na síntese, no chat e no assistente.
- Novos testes: unitários com respostas em blocos e um teste com IA para cada uso (texto, saída estruturada, imagem e PDF).

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: adiciona o requisito de leitura do texto da resposta do modelo independente do formato do conteúdo.

## Impact

- **Código:** `lumina/core/llm.py`, `lumina/services/ai/stages/evaluation.py`, `lumina/services/ai/stages/synthesis.py`, `lumina/services/ai/chat.py`, `lumina/services/assistant_service.py`, `lumina/features/template_check/constants.py`, `lumina/features/abnt_check/abnt.py`.
- **Comportamento observável:** pareceres, sínteses, respostas do chat e verificações de ABNT e template passam a vir dos modelos novos. O `abnt_check` sai de `effort = none` com `temperature = 0` para `effort = medium` sem `temperature`: fica mais lento, mais caro e menos repetível entre execuções.
- **Testes:** novos casos em `tests/unit/services/`, novo `tests/ai/evaluation/models/test_models_smoke.py`.
- **APIs:** nenhuma mudança de contrato.
