## Why

O texto dos chunks traz os cabeçalhos e rodapés que se repetem nas páginas do PDF (issue #20). No acervo anotado, 49 dos 91 chunks de `dengue_no_brasil.pdf` e 53 dos 94 de `recuperando_especialistas_renovaveis_pln_ueba.pdf` contêm uma dessas linhas. Um ramo que menciona "Revisão Sistemática" puxa os chunks que repetem o título "DENGUE NO BRASIL: UMA REVISÃO SISTEMÁTICA", e esses chunks ocupam vagas do limite de trechos sem trazer conteúdo.

## What Changes

- A extração passa a apagar do texto, antes de montar seções e chunks, as linhas corridas de cada página:
  - caixas que o `pymupdf4llm` classifica como `page-header` ou `page-footer` e cujo texto se repete em 2 páginas ou mais;
  - caixas de texto na faixa de 12% do topo ou da base da página cujo texto se repete em pelo menos 3 páginas e em 30% delas, como a linha de autores que o layout classifica como `text`. A primeira ocorrência fica no texto.
- O texto entra na comparação sem marcação e com os dígitos trocados por um marcador, para que número de página e intervalo de páginas contem como a mesma linha.
- O sistema troca as linhas apagadas por espaços e quebras de linha do mesmo tamanho. `char_start`, `char_end`, o mapa de páginas e as caixas continuam com os mesmos deslocamentos.
- O cálculo dos retângulos das citações ignora as caixas apagadas, então o destaque no PDF não cobre o cabeçalho.
- Novo gabarito `<nome>.running.yaml` ao lado de cada PDF do acervo, com as linhas corridas que não podem chegar aos chunks e as linhas perto do topo ou da base que precisam ficar, como legendas de figura que o layout marca como rodapé.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: adiciona o requisito de remoção de cabeçalhos e rodapés corridos na extração e amplia o critério de aceite da ingestão sobre o acervo anotado com o gabarito de linhas corridas.

## Impact

- **Código:** `lumina/services/ai/stages/extraction.py` (detecção e máscara das linhas corridas em `extract_raw_markdown_and_pages`) e `lumina/services/ai/stages/positioning.py` (caixas apagadas fora dos retângulos).
- **Comportamento observável:** os chunks deixam de trazer cabeçalhos, rodapés e números de página repetidos. Chunks que só tinham essas linhas deixam de existir, e os `chunk_id` das páginas afetadas podem mudar de índice. A árvore de seções perde os títulos falsos que vinham de cabeçalhos.
- **Dados existentes:** a ingestão roda de novo a cada avaliação (`process_release_pipeline`), então cada documento recebe os chunks limpos na próxima avaliação. Não há migração.
- **Testes e acervo:** novo `tests/unit/services/test_ingestion_running_lines.py` sobre os gabaritos, testes do cleaner, um caso novo em `tests/unit/services/test_positioning.py`, leitura do gabarito em `tests/fixtures/answer_keys.py`, `running_template.yaml` e quatro `<nome>.running.yaml` em `tests/fixtures/documents/`.
- **Documentação:** `tests/fixtures/documents/README.md` e a seção de validação da ingestão em `docs/arquitetura-engenharia.md`.
- **Fora do escopo:** o desalinhamento entre o `pos` das caixas e o markdown depois de juntar espaços, que já desloca os retângulos de citação hoje, e as legendas classificadas como rodapé, que não ganham retângulo. Os dois ficam na issue #43.
- **APIs:** nenhuma mudança de contrato.
