## 1. Refatoração e Padronização do Módulo de Retrieval

- [x] 1.1 Implementar `retrieve_criteria_payload` e `retrieve_evaluation_payloads` em `lumina/services/ai/stages/retrieval.py` substituindo as 3 passadas recursivas por uma passada direta por critério
- [x] 1.2 Padronizar a nomenclatura em `lumina/services/ai/stages/retrieval.py` substituindo referências a `sessions` por `evidence_chunks` / `chunks` e `expected_session` por `expected_section`
- [x] 1.3 Adicionar aliases retrocompatíveis para `get_eval_args` e `simplify_eval_args` em `lumina/services/ai/stages/retrieval.py` garantindo suporte aos testes existentes
- [x] 1.4 Atualizar `lumina/services/ai/stages/__init__.py` exportando `retrieve_evaluation_payloads` junto com os aliases de compatibilidade

## 2. Integração no Pipeline e Validação de Qualidade

- [x] 2.1 Atualizar `process_release_pipeline` em `lumina/services/ai/pipeline.py` para invocar `retrieve_evaluation_payloads` diretamente
- [x] 2.2 Criar e atualizar testes unitários em `tests/unit/services/test_ai_stages.py` cobrindo `retrieve_evaluation_payloads` e validando a presença de `expected_section` e chunks de evidência
- [x] 2.3 Executar `poetry run pytest tests/unit/services/test_ai_stages.py` e confirmar que todos os testes passam
- [x] 2.4 Executar `poetry run task test` e `poetry run ruff check` garantindo a integridade da suíte completa e aderência aos padrões de estilo
