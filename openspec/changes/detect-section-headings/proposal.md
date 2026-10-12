## Why

O acervo anotado de `tests/fixtures/documents/` mede quantas seções a ingestão reconhece com título e página certos. O placar está em 44 de 55, no piso de 0,80. As 11 falhas vêm de dois defeitos na detecção de títulos:

- **Títulos na mesma linha do texto.** Artigos da MDPI e de outras editoras escrevem `**Abstract:** The production...`, `**Funding:** This research...`. O extrator não marca essas linhas como título, e o texto fica dentro da seção anterior. Em `smart_tech_microgrids.pdf`, 8 seções somem assim: Abstract, Supplementary Materials, Author Contributions, Funding, Data Availability Statement, Acknowledgments, Conflicts of Interest e Disclaimer/Publisher's Note.
- **Fusão de títulos vizinhos.** A fusão junta títulos separados por até 5 caracteres, pensando em títulos quebrados em duas linhas. Ela também junta títulos distintos. Em `dengue_no_brasil.pdf`, "RESUMO" vira o fim do título "DOI: ... RESUMO", e "2. Desenvolvimento" vira "2. Desenvolvimento 2.1 Agente Etiológico...".

A recuperação usa o título da seção no prefixo de cada chunk, no roteamento por seção e no papel semântico. Título errado leva o motor a procurar no lugar errado.

## What Changes

- A ingestão reconhece como título um rótulo em negrito seguido de dois-pontos no início da linha (`**Funding:** ...`) quando o rótulo está numa lista de nomes de seção conhecidos. O texto da linha pertence à seção nova.
- A fusão de títulos vizinhos deixa de juntar um título que tem numeração própria (`2.1`) ou que é um nome de seção conhecido (`RESUMO`). Títulos quebrados em duas linhas continuam fundidos.
- O teste de métrica passa a reconhecer uma seção também pelo caminho de títulos (`section_path`) dos chunks. Uma seção sem texto próprio, como "2. Desenvolvimento" antes de "2.1", não gera chunk, mas aparece no caminho dos chunks das filhas.
- O piso de identificação sobe para o placar medido depois da mudança. O protótipo do planejamento chegou a 55 de 55.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: adiciona o requisito de detecção de títulos de seção, com títulos na mesma linha do texto e limites para a fusão de títulos vizinhos.

## Impact

- **Código:** `lumina/services/ai/stages/sections.py` (leitura de títulos, fusão, filtro de órfãos, árvore de seções) e `lumina/services/ai/stages/section_models.py` (`Heading`).
- **Testes:** `tests/unit/services/test_ingestion_sections.py` (métrica por caminho e piso), testes novos em `tests/unit/services/test_heading_cleaners.py` e `tests/unit/services/test_section_tree.py`.
- **Comportamento observável:** documentos com rótulos conhecidos ganham seções novas, com chunks e resumos de seção próprios. Títulos antes fundidos viram seções separadas. Nenhum texto sai do índice.
- **Dados existentes:** sem migração. A ingestão roda de novo a cada avaliação.
- **Dependência:** parte do resultado de `ingest-subsections`, que ainda não foi arquivada.
