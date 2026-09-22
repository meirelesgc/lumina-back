## 1. Configuração e Utilitários de Formatação

- [x] 1.1 Adicionar as configurações `DEBUG_INGESTION_AUDIT: bool = False` e `INGESTION_AUDIT_DIRECTORY: Path = 'lumina/storage/ingestion_audit'` em `lumina/core/settings.py` e validar via script interativo do Poetry.
- [x] 1.2 Implementar `tree_to_markdown` em `lumina/services/ai/stages/sections.py` e `documents_to_markdown_preview` em `lumina/services/ai/stages/chunking.py`, validando com testes unitários.

## 2. Implementação do Módulo de Auditoria e Anotação de PDF

- [x] 2.1 Criar `lumina/services/ai/stages/audit.py` contendo a paleta de cores (`ROLE_COLORS`, `CHUNK_COLORS`) e a função `annotate_pdf_document` que desenha barras laterais de seções na margem e highlights de chunks no PDF via PyMuPDF.
- [x] 2.2 Implementar `export_ingestion_audit` em `lumina/services/ai/stages/audit.py` para criar e gravar os 4 subdiretórios (`01_raw_markdown`, `02_sections_tree`, `03_chunks`, `04_annotated_pdfs`) com arquivos `.md`, `.json` e `.pdf`.

## 3. Integração com o Pipeline de Extração

- [x] 3.1 Integrar a chamada condicional a `export_ingestion_audit` dentro de `extract_pdf_chunks` em `lumina/services/ai/stages/extraction.py`, acionada somente quando `SETTINGS.DEBUG_INGESTION_AUDIT` for `True`.
- [x] 3.2 Proteger a rotina de auditoria com captura de exceções e log informativo, garantindo que falhas de I/O local não interrompam o processamento em memória do documento.

## 4. Testes Automatizados e Verificação

- [x] 4.1 Criar suite de testes em `tests/unit/services/test_ingestion_audit.py` verificando a geração dos arquivos e diretórios quando ativo, e a ausência de I/O quando inativo.
- [x] 4.2 Executar a suíte completa de testes (`poetry run task test`) e linting (`poetry run ruff check lumina tests`).
