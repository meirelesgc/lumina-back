## 1. Acervo e dependências

- [x] 1.1 Declarar `pyyaml` como dependência de desenvolvimento (`poetry add --group dev pyyaml`) e verificar que `poetry run python -c "import yaml"` funciona.
- [x] 1.2 Revisar `tests/fixtures/documents/README.md`, `section_template.yaml` e `systematic_review/dengue_no_brasil.sections.yaml`, e verificar que os 14 `starts_with` ("2. Desenvolvimento" não tem) aparecem no texto do PDF.

## 2. Testes antes da correção

- [x] 2.1 Criar `tests/unit/services/test_ingestion_sections.py` com a descoberta dos gabaritos, a normalização, a fixture de extração com cache, o teste crítico de texto por documento e o teste de métrica com `MIN_SECTION_IDENTIFICATION_RATE = 0.80`. Verificar que `poetry run pytest tests/unit/services/test_ingestion_sections.py` falha hoje, apontando as 10 seções sem texto de `dengue_no_brasil.pdf`.
- [x] 2.2 Adicionar a `tests/unit/services/test_chunking.py` um teste de regressão com uma seção pai e duas filhas: o texto das filhas aparece nos chunks, com `section_title` da filha e `section_path` completo. Verificar que o teste falha hoje.

## 3. Correção

- [x] 3.1 Em `create_chunks_from_sections` (`lumina/services/ai/stages/chunking.py`), percorrer `flatten_sections(sections)` e atualizar a docstring. Verificar que os testes das tarefas 2.1 e 2.2 passam e que os testes existentes de `test_chunking.py` continuam passando sem alteração.
- [x] 3.2 Medir o placar final de identificação de seções impresso pelo teste de métrica e ajustar `MIN_SECTION_IDENTIFICATION_RATE` se ele diferir de 0.80. Verificar que o valor no código é o placar medido, arredondado para baixo.

## 4. Verificação

- [x] 4.1 Rodar `poetry run task test` e `poetry run ruff check lumina tests` e verificar que tudo passa.
  - Resultado: 331 testes passam. O `ruff check lumina tests` acusa 253 erros, a mesma contagem do `develop` antes da mudança, todos em arquivos fora desta mudança (`lumina/features/`, entre outros). Os arquivos alterados passam em `ruff check` e `ruff format --check`.
- [x] 4.2 Medir o tempo de `extract_pdf_chunks` em `dengue_no_brasil.pdf` antes e depois da correção e registrar os números e a contagem de chunks na descrição do PR.
  - Resultado (`DEBUG_INGESTION_AUDIT=False`, mediana de 5 execuções): antes, 23 chunks em 8,52 s; depois, 91 chunks em 9,19 s. O custo extra de embedding e anonimização dos 68 chunks novos não entra nesta medição.
