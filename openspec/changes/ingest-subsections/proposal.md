## Why

A ingestão só transforma em chunks as seções de primeiro nível da árvore. O texto de toda subseção (`2.1`, `2.2`, `ABSTRACT` filho de um título) fica fora do índice e a recuperação nunca o encontra. Na revisão sistemática `dengue_no_brasil.pdf`, a árvore tem 19 seções e só 6 viram chunks: os chunks somam cerca de 16 mil dos 61 mil caracteres extraídos. Resumo, Abstract, Resumen e as subseções 2.2 a 2.7 somem.

Esta correção vem antes das melhorias de recuperação (#15 a #20), porque nenhuma delas se mede com o texto incompleto.

## What Changes

- `create_chunks_from_sections` passa a percorrer a árvore inteira, em ordem de leitura, e gera chunks para cada seção e subseção.
- Cada chunk de subseção leva o título da própria subseção em `section_title` e o caminho completo em `section_path`. `section_index` passa a contar seções na ordem de leitura da árvore achatada.
- Novo teste de ingestão sobre um acervo de PDFs anotados (`tests/fixtures/documents/`), sem IA, na suíte padrão:
  - **Crítico, tolerância zero:** o início de cada seção anotada aparece no texto dos chunks.
  - **Métrica com piso:** a ingestão identifica cada seção anotada com o título e a página certos. O teste imprime o placar e falha abaixo de um piso. O piso é o valor medido depois da correção, arredondado para baixo, e só sobe.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: adiciona o requisito de cobertura integral do texto extraído pelos chunks, incluindo subseções, e o critério de aceite da ingestão sobre o acervo anotado.

## Impact

- **Código:** `lumina/services/ai/stages/chunking.py` (`create_chunks_from_sections`).
- **Comportamento observável:** documentos com subseções geram mais chunks e mais resumos de seção (`build_section_summary_documents`). Os títulos nos prefixos `[título]` dos chunks passam a ser os das subseções.
- **Dados existentes:** a ingestão roda de novo a cada avaliação (`process_release_pipeline`), então cada documento recebe as subseções na próxima avaliação. Não há migração.
- **Testes:** novo `tests/unit/services/test_ingestion_sections.py`, novo caso em `tests/unit/services/test_chunking.py`, acervo em `tests/fixtures/documents/`.
- **APIs:** nenhuma mudança de contrato.
