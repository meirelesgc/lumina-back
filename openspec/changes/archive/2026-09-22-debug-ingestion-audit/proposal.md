## Why

Após a migração do motor de ingestão de documentos baseada no laboratório experimental (`.tmp/lumina-section-extractor/`), o processamento passou a ser executado 100% em memória para máxima performance em produção. No entanto, desenvolvedores e auditores necessitam inspecionar as etapas intermediárias (Markdown bruto, mapeamento de páginas, árvore de seções, chunks fatiados e marcação visual em PDF) para diagnosticar falhas de extração, verificar o alinhamento de bounding boxes e validar a hierarquia de seções em novos formatos de editais ou contratos.

Esta mudança introduz a capacidade de auditoria e exportação estruturada em disco de cada estágio da ingestão documental quando a flag `DEBUG_INGESTION_AUDIT` estiver ativada nas configurações do sistema (`Settings`), recriando a organização em pastas e o PDF anotado do MVP sem onerar o fluxo normal de produção.

## What Changes

- **Nova configuração `DEBUG_INGESTION_AUDIT` e `INGESTION_AUDIT_DIRECTORY`**: adiciona as variáveis booleanas e de caminho em `lumina/core/settings.py` (`DEBUG_INGESTION_AUDIT: bool = False`, com diretório padrão `INGESTION_AUDIT_DIRECTORY: Path = 'lumina/storage/ingestion_audit'`).
- **Módulo de persistência de auditoria (`lumina/services/ai/stages/audit.py`)**:
  - Geração de relatórios legíveis em Markdown e dumps JSON estruturados para cada fase:
    - `01_raw_markdown/`: `{stem}.md` e `{stem}_pages.json`
    - `02_sections_tree/`: `{stem}_sections.json` e `{stem}_sections.md`
    - `03_chunks/`: `{stem}_chunks.json` e `{stem}_chunks.md`
    - `04_annotated_pdfs/`: `{stem}_annotated.pdf` com barras laterais coloridas para seções e destaques visuais para os chunks fatiados.
- **Acoplamento não-intrusivo em `extract_pdf_chunks`**: acionamento condicional da rotina de exportação no estágio de extração, garantindo que em produção (`DEBUG_INGESTION_AUDIT=False`) não haja nenhum custo de I/O em disco ou overhead de renderização visual.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade raiz externa; extensão observacional do pipeline de IA. -->

### Modified Capabilities
- `ai-pipeline`: adiciona requisito de exportação de artefatos de auditoria e PDF anotado dos estágios de extração documental condicionado à configuração de flag de depuração.

## Impact

- **Código Afetado**:
  - `lumina/core/settings.py`: adição de `DEBUG_INGESTION_AUDIT` e `INGESTION_AUDIT_DIRECTORY`.
  - `lumina/services/ai/stages/audit.py` (novo módulo): funções puras de formatação/anotação e gravação em disco.
  - `lumina/services/ai/stages/extraction.py`: chamada condicional a `export_ingestion_audit` quando a flag de depuração estiver habilitada.
  - `lumina/services/ai/stages/sections.py`: exportação de helper `tree_to_markdown`.
  - `lumina/services/ai/stages/chunking.py`: exportação de helper `documents_to_markdown_preview`.
- **APIs e Interfaces**: Nenhuma quebra de contrato de API pública. O comportamento padrão permanece idêntico e em memória.
- **Dependências**: Utiliza ferramentas já instaladas no projeto (`pymupdf`/`fitz`).
- **Testes**: Novos testes unitários validando a gravação dos 4 estágios e a inação completa quando a flag está desativada.
