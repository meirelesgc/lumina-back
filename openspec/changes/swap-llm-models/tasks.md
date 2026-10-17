## 1. Testes antes da troca

- [ ] 1.1 Em `tests/unit/services/test_evaluation_styles.py` (ou arquivo novo em `tests/unit/services/`), testar que `_process_eval_item` com um `AIMessage` de conteúdo em blocos contendo um JSON de parecer válido registra `fulfilled`, `score`, `feedback` e citações desse JSON. Verificar que o teste falha antes da mudança, com o parecer "Erro na validação de schema".
- [ ] 1.2 Testar que `generate_release_synthesis` grava só o texto quando o modelo devolve blocos, e que `chat_with_document` e o assistente devolvem `str` com o modelo devolvendo blocos. Verificar que os testes falham antes da mudança.
- [ ] 1.3 Criar `tests/ai/evaluation/models/test_models_smoke.py` com `@pytest.mark.ai`: modelo principal com texto, com saída estruturada e pela cadeia de avaliação (`with_low_verbosity`); modelo rápido com saída estruturada; configuração de visão do rápido com uma imagem gerada no teste; configuração do médio com um PDF de uma página por `input_file`. Verificar que os testes do modelo principal falham antes da mudança, porque a cadeia de avaliação não lê blocos.

## 2. Troca

- [ ] 2.1 Em `lumina/core/llm.py`, criar as constantes por uso (`FAST_MODEL = 'gpt-6-luna'`, `FAST_REASONING_EFFORT = 'none'`, `FAST_TEMPERATURE = 0`, `MAIN_MODEL = 'gpt-6.1-sol'`, `MAIN_REASONING_EFFORT = 'medium'`) e configurar os dois `ChatOpenAI` com `reasoning`, sem `temperature` no principal. Verificar que a suíte padrão passa.
- [ ] 2.2 Ler o texto da resposta com `.text` em `evaluation._extract_raw_text`, `synthesis.generate_release_synthesis`, `chat.py` e `assistant_service.py`. Verificar que os testes 1.1 e 1.2 passam.
- [ ] 2.3 Passar `template_check/constants.py` para o uso rápido e `abnt_check/abnt.py` para o uso médio, importando as constantes de `lumina/core/llm.py`, sem `temperature` no `abnt_check`, e atualizar os comentários. Verificar que `tests/routers/test_abnt.py` e `tests/routers/test_templates.py` passam.
- [ ] 2.4 Rodar `poetry run pytest tests/ai/evaluation/models -s --run-ai -m ai` e verificar que todos os testes passam. Se o `gpt-6.1-sol` recusar `verbosity`, ajustar `with_low_verbosity` e registrar aqui.

## 3. Verificação

- [ ] 3.1 Rodar `poetry run task test` e `ruff check` e `ruff format --check` nos arquivos alterados, e registrar aqui o resultado.
- [ ] 3.2 Rodar `poetry run pytest tests/ai/evaluation/retrieval -s --run-ai -m ai` e verificar que o placar de recuperação não muda, já que ele não usa os modelos de chat. Registrar aqui.
