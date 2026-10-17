## 1. Testes antes da troca

- [x] 1.1 Em `tests/unit/services/test_evaluation_styles.py` (ou arquivo novo em `tests/unit/services/`), testar que `_process_eval_item` com um `AIMessage` de conteúdo em blocos contendo um JSON de parecer válido registra `fulfilled`, `score`, `feedback` e citações desse JSON. Verificar que o teste falha antes da mudança, com o parecer "Erro na validação de schema".
  - Resultado: `tests/unit/services/test_model_responses.py`. Antes da mudança, o caso em blocos falha e o caso em texto simples passa.
- [x] 1.2 Testar que `generate_release_synthesis` grava só o texto quando o modelo devolve blocos, e que `chat_with_document` e o assistente devolvem `str` com o modelo devolvendo blocos. Verificar que os testes falham antes da mudança.
  - Resultado: no mesmo arquivo. Antes da mudança, a síntese quebra com `'list' object has no attribute 'strip'` e o chat e o assistente devolvem a lista de blocos.
- [x] 1.3 Criar `tests/ai/evaluation/models/test_models_smoke.py` com `@pytest.mark.ai`: modelo principal com texto, com saída estruturada e pela cadeia de avaliação (`with_low_verbosity`); modelo rápido com saída estruturada; configuração de visão do rápido com uma imagem gerada no teste; configuração do médio com um PDF de uma página por `input_file`. Verificar que os testes do modelo principal falham antes da mudança, porque a cadeia de avaliação não lê blocos.
  - Resultado: os 6 testes passam antes da mudança. O `gpt-5-mini` sem `reasoning` responde pela Chat Completions API, em texto simples, então o teste de fumaça é uma guarda da configuração. A falha com blocos fica provada pelos testes 1.1 e 1.2. Os testes de visão chamam `visual_compare` e `request_criteria`.

## 2. Troca

- [x] 2.1 Em `lumina/core/llm.py`, criar as constantes por uso (`FAST_MODEL = 'gpt-6-luna'`, `FAST_REASONING_EFFORT = 'none'`, `FAST_TEMPERATURE = 0`, `MAIN_MODEL = 'gpt-6.1-sol'`, `MAIN_REASONING_EFFORT = 'medium'`) e configurar os dois `ChatOpenAI` com `reasoning`, sem `temperature` no principal. Verificar que a suíte padrão passa.
  - Resultado: `get_fast_model` mantém a assinatura e passa `reasoning` e `temperature`; o modelo principal passa só `reasoning`.
- [x] 2.2 Ler o texto da resposta com `.text` em `evaluation._extract_raw_text`, `synthesis.generate_release_synthesis`, `chat.py` e `assistant_service.py`. Verificar que os testes 1.1 e 1.2 passam.
  - Resultado: `_extract_raw_text` usa `.text` só para `BaseMessage` e mantém o caminho antigo para outros objetos. Com `hasattr(..., 'text')`, o `MagicMock` de `test_apply_tree_isolates_schema_validation_error` passava a ser tratado como mensagem.
- [x] 2.3 Passar `template_check/constants.py` para o uso rápido e `abnt_check/abnt.py` para o uso médio, importando as constantes de `lumina/core/llm.py`, sem `temperature` no `abnt_check`, e atualizar os comentários. Verificar que `tests/routers/test_abnt.py` e `tests/routers/test_templates.py` passam.
  - Resultado: 51 testes passam. Os nomes antigos das constantes (`VISION_MODEL`, `AI_MODEL`, `REASONING_EFFORT`) continuam, apontando para `lumina/core/llm.py`; `TEMPERATURE` sai do `abnt_check`.
- [x] 2.4 Rodar `poetry run pytest tests/ai/evaluation/models -s --run-ai -m ai` e verificar que todos os testes passam. Se o `gpt-6.1-sol` recusar `verbosity`, ajustar `with_low_verbosity` e registrar aqui.
  - Resultado: 6 testes passam em 1 min 25 s. O `gpt-6.1-sol` aceita `verbosity = 'low'`, então `with_low_verbosity` não muda. A saída estruturada gera 2 avisos de serialização do Pydantic dentro do SDK da OpenAI, sem efeito no resultado.

## 3. Verificação

- [x] 3.1 Rodar `poetry run task test` e `ruff check` e `ruff format --check` nos arquivos alterados, e registrar aqui o resultado.
  - Resultado: 356 testes passam e 10 são pulados (`@pytest.mark.ai`), contra 351 antes. Cobertura de `lumina/` em 75%. `ruff check` e `ruff format --check` passam nos arquivos novos e em `lumina/core/llm.py`, `evaluation.py`, `synthesis.py`, `chat.py` e `assistant_service.py`. Em `abnt.py` e `template_check/constants.py`, os 16 erros e a formatação pendente são os mesmos de antes da mudança.
- [x] 3.2 Rodar `poetry run pytest tests/ai/evaluation/retrieval -s --run-ai -m ai` e verificar que o placar de recuperação não muda, já que ele não usa os modelos de chat. Registrar aqui.
  - Resultado: 4 testes passam com o mesmo placar (recall 58/129, seção e página 63/129, precisão 36/199). O roteamento passou a ter 64 casos em vez de 72 porque o usuário mudou o escopo de ramos para `ENTIRE_DOCUMENT` nos gabaritos (commit `6fec47d`), sem relação com a troca de modelos.
