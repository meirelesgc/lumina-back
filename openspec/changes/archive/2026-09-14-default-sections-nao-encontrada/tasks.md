## 1. Refatoração do Estágio de Seções

- [x] 1.1 Definir a constante `DEFAULT_SECTION_TITLE = 'NÃO ENCONTRADA'` em `lumina/services/ai/stages/sections.py`
- [x] 1.2 Simplificar `assign_sections_to_chunks` para atribuir `metadata['section_title'] = DEFAULT_SECTION_TITLE` e prefixar `SECTION: NÃO ENCONTRADA\n\n` em cada chunk de PDF sem invocar chamadas de LLM
- [x] 1.3 Simplificar `split_by_sections` para atribuir `metadata['section_title'] = DEFAULT_SECTION_TITLE` a cada documento bruto de DOCX/TXT sem fatiamento difuso
- [x] 1.4 Atualizar `assign_sections_with_telemetry` e `split_sections_with_telemetry` para registrar a conclusão no `RunLogger` com metadados limpos (`sections_detected: []`, `mapping_success_rate: 1.0`)
- [x] 1.5 Manter stubs/compatibilidade das importações expostas em `lumina/services/ai/stages/__init__.py`

## 2. Testes e Qualidade

- [x] 2.1 Implementar testes unitários em `tests/unit/services/test_sections_fallback.py` verificando a atribuição de `section_title = "NÃO ENCONTRADA"` e prefixo `SECTION:` para PDFs e DOCX/TXT
- [x] 2.2 Executar `poetry run pytest tests/unit/services/test_sections_fallback.py` e confirmar que todos os testes passam
- [x] 2.3 Executar `poetry run ruff check` e `poetry run ruff format` garantindo conformidade com as regras de estilo
