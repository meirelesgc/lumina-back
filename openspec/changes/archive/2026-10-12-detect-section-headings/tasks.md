## 1. Testes antes da mudança

- [x] 1.1 Em `tests/unit/services/test_ingestion_sections.py`, trocar `identified_sections` pela leitura de `section_path` descrita no design. Verificar que o placar continua 44/55 (a troca sozinha não muda o resultado, porque "2. Desenvolvimento" ainda está fundido com "2.1").
- [x] 1.2 Em `tests/unit/services/test_section_tree.py`, adicionar testes para: rótulo conhecido na mesma linha vira seção e o texto da linha fica na seção; rótulo de resumo estruturado (`**Objetivo** :`) não vira seção; intervalo de caracteres de um título `inline` começa no início da própria linha. Verificar que os testes falham hoje.
- [x] 1.3 Em `tests/unit/services/test_heading_cleaners.py`, adicionar testes para a fusão: título numerado seguido de subseção numerada fica separado; título seguido de "RESUMO" fica separado; título `inline` nunca é fundido. Verificar que os testes falham hoje e que `test_make_adjacent_merger` continua passando.

## 2. Implementação

- [x] 2.1 Adicionar `inline: bool = False` a `Heading` (`section_models.py`), a lista de rótulos conhecidos e a função `content_start_line` em `sections.py`. Verificar com `poetry run pytest tests/unit/services/test_section_tree.py tests/unit/services/test_heading_cleaners.py` que nenhum teste existente quebra.
- [x] 2.2 Ler rótulos `inline` em `parse_headings_from_markdown` e usar `content_start_line` em `build_section_tree` e `make_orphan_cleaner`. Verificar que os testes da tarefa 1.2 passam.
- [x] 2.3 Limitar a fusão em `make_adjacent_merger` como no design. Verificar que os testes da tarefa 1.3 passam.

## 3. Piso e verificação

- [x] 3.1 Rodar `poetry run pytest tests/unit/services/test_ingestion_sections.py -s`, registrar o placar e subir `MIN_SECTION_IDENTIFICATION_RATE` para o valor medido, arredondado para baixo. Verificar que o teste crítico passa nos três documentos.
  - Resultado: 55/55 (artigo 14/14, dengue 15/15, microgrids 26/26). Piso sobe de 0,80 para 1,0. O teste crítico passa nos três documentos.
- [x] 3.2 Rodar `poetry run task test` e `poetry run ruff check` e `ruff format --check` nos arquivos alterados. Verificar que a suíte passa e que a contagem de erros de lint do repositório não aumenta.
  - Resultado: 339 testes passam. Os arquivos alterados passam em `ruff check` e `ruff format --check`; a contagem de erros de lint do repositório segue em 253.
