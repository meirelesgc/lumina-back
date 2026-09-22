## Context

Ver motivação detalhada em `proposal.md`.

Atualmente, o motor de ingestão em [`lumina/services/ai/stages/extraction.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/services/ai/stages/extraction.py) orquestra a leitura do PDF, a criação da árvore hierárquica de seções, o corte monopágina e o enriquecimento de retângulos de linha inteiramente em memória através do objeto `fitz.Document` (PyMuPDF) e estruturas Python puras.

O laboratório experimental em [`.tmp/lumina-section-extractor/`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/.tmp/lumina-section-extractor/) possuía scripts desacoplados por estágio que gravavam o estado intermediário em pastas dedicadas (`01_raw_markdown`, `02_sections_tree`, `03_chunks` e `04_annotated_pdfs`). O objetivo deste design é reincorporar essa capacidade ao Lumina Back sob demanda.

## Goals / Non-Goals

**Goals:**
- Prover exportação determinística dos quatro estágios de ingestão documental em diretórios espelhados aos do MVP quando `DEBUG_INGESTION_AUDIT` for `True`.
- Gerar o PDF anotado (`04_annotated_pdfs/{stem}_annotated.pdf`) com barras marginais laterais codificadas por cor para cada papel de seção (`ROLE_COLORS`) e destaques visuais com rótulos `chunk_id` para cada fragmento fatiado.
- Garantir zero overhead de I/O em disco, processamento adicional ou alocação de memória quando `DEBUG_INGESTION_AUDIT` for `False`.
- Isolar a lógica de exportação e visualização em um módulo dedicado para não poluir os estágios funcionais do pipeline.

**Non-Goals:**
- Não alterar formatos de retorno das funções do pipeline de produção (`extract_pdf_chunks`, `assign_sections_with_telemetry`, etc.).
- Não modificar APIs públicas REST nem respostas de endpoints existentes.
- Não persistir esses arquivos intermediários em ambientes de nuvem (S3/GCS); a funcionalidade é estritamente voltada a depuração e auditoria local em disco.

## Decisions

### 1. Configuração via `DEBUG_INGESTION_AUDIT` e `INGESTION_AUDIT_DIRECTORY`
- **Decisão:** Adicionar em [`lumina/core/settings.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/core/settings.py):
  ```python
  DEBUG_INGESTION_AUDIT: bool = False
  INGESTION_AUDIT_DIRECTORY: Path = 'lumina/storage/ingestion_audit'
  ```
- **Racional:** Alinha-se diretamente com a preferência explícita do usuário de usar uma variável booleana, permitindo também customizar o diretório de destino caso necessário via `.env`.

### 2. Módulo de Auditoria Isolado (`lumina/services/ai/stages/audit.py`)
- **Decisão:** Centralizar toda a formatação de relatórios (Markdown previews), serialização de dicionários e renderização de PDF anotado em `lumina/services/ai/stages/audit.py`.
- **Racional:** Evita acoplar responsabilidades de desenho visual de PDF e serialização de relatórios dentro de `extraction.py`, `sections.py` ou `positioning.py`.
- **Alternativas consideradas:**
  - *Distribuir gravação dentro de cada estágio:* Rejeitado por espalhar verificações de debug e operações de arquivo por todo o código.

### 3. Mecanismo de Anotação no PDF com PyMuPDF
- **Decisão:** Implementar `annotate_pdf_document` que clona/reabre o documento ou anota uma cópia em memória:
  - **Seções:** Desenha retângulos verticais (`page.draw_rect`) na margem esquerda (coordenadas x de 4 a 8 pontos) com a cor correspondente a `section_role` (`ROLE_COLORS`) e insere o texto do título da seção (`page.insert_text`).
  - **Chunks:** Adiciona anotações de destaque (`page.add_highlight_annot`) para as caixas físicas calculadas em `metadata['rects']`, configurando transparência e título no popup (`chunk_id`).
  - Salva o arquivo em `{output_dir}/04_annotated_pdfs/{stem}_annotated.pdf`.

### 4. Tolerância a Falhas no Modo Debug
- **Decisão:** A execução de `export_ingestion_audit` será protegida por bloco `try/except` com log de erro, para que qualquer eventual falha de escrita em disco local nunca interrompa a ingestão principal de um documento em desenvolvimento.

## Risks / Trade-offs

- **[Risco]** Overhead de tempo na geração do PDF anotado em documentos com centenas de páginas.
  - **Mitigação:** Como a funcionalidade só roda com `DEBUG_INGESTION_AUDIT=True`, a latência adicional é esperada pelo desenvolvedor/auditor e não afeta o ambiente padrão.
- **[Risco]** Conflito de nomes de arquivos com o mesmo `stem` ao reprocessar.
  - **Mitigação:** A gravação sobrescreve os artefatos daquele mesmo arquivo no diretório de auditoria, refletindo sempre a execução mais recente.
