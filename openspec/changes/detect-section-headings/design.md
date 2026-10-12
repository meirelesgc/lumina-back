## Context

A árvore de seções nasce de `parse_headings_from_markdown`, que só aceita linhas iniciadas por `#`. O `pymupdf4llm` gera `#` a partir do tamanho da fonte. Rótulos como `**Funding:** This research...` têm a fonte do corpo, então saem como parágrafo comum.

Depois da leitura, `run_heading_pipeline` aplica cinco limpezas em ordem: marcação, repetidos, fusão de vizinhos (`make_adjacent_merger`), nível pela numeração e órfãos (`make_orphan_cleaner`). A fusão junta qualquer título seguido de outro com até 5 caracteres entre eles. O filtro de órfãos remove títulos com menos de 20 caracteres de texto entre eles e o próximo título.

Toda a cadeia supõe que o texto de uma seção começa na linha seguinte ao título: `build_section_tree`, `content_char_range` e o filtro de órfãos usam `heading.line_number` como primeira linha excluída.

Protótipo feito no planejamento, com monkeypatch e sem alterar código, medido pelo teste do acervo:

| Documento | Hoje | Protótipo | Protótipo, métrica por caminho |
| :--- | ---: | ---: | ---: |
| `article/recuperando_especialistas...` | 14/14 | 14/14 | 14/14 |
| `systematic_review/dengue_no_brasil` | 12/15 | 14/15 | 15/15 |
| `systematic_review/smart_tech_microgrids` | 18/26 | 26/26 | 26/26 |

O teste crítico de texto passou nos três documentos.

## Goals / Non-Goals

**Goals:**
- Reconhecer rótulos de seção conhecidos escritos na mesma linha do texto, sem perder o texto da linha.
- Impedir a fusão de títulos distintos, sem desfazer a fusão de títulos quebrados em duas linhas.
- Medir a identificação de seções sem texto próprio pelo caminho de títulos.

**Non-Goals:**
- Reconhecer rótulos fora da lista (heurística genérica de negrito com dois-pontos).
- Corrigir títulos falsos que o extrator gera a partir de citações, como "(TEIXEIRA, 2005).". Eles não afetam o placar atual.
- Mudar o tamanho dos chunks ou a recuperação.

## Decisions

### Lista de rótulos em vez de regra genérica

O rótulo vira título só quando, depois de normalizado (sem marcação, sem espaços nas pontas, em minúsculas, com `’` igual a `'`), pertence a uma lista fixa:

`abstract`, `resumo`, `resumen`, `supplementary materials`, `author contributions`, `funding`, `data availability statement`, `acknowledgments`, `acknowledgements`, `conflicts of interest`, `disclaimer/publisher's note`, `institutional review board statement`, `informed consent statement`.

A lista fica em `sections.py`, ao lado de `ROLE_ALIASES`.

Alternativa: tratar como título todo negrito com dois-pontos no início da linha. Rejeitada porque resumos estruturados (`**Objetivo** :`, `**Metodologia** :`, `**Resultados:**` no artigo do acervo) virariam seções. O resumo ficaria quebrado em pedaços com títulos que nenhum critério procura, e o título "RESUMO" ficaria sem texto próprio. A lista cresce quando um documento anotado mostrar um rótulo novo.

A expressão casa só o rótulo dentro do negrito com os dois-pontos (`**Funding:**`). Os rótulos de resumo estruturado do artigo fecham o negrito antes dos dois-pontos (`**Objetivo** :`) e já ficam fora pela lista.

### `Heading.inline` marca o título na mesma linha do texto

`Heading` ganha o campo `inline: bool = False`. A leitura cria esses títulos com `level=1` e `level_source='inline_label'`, e devolve a lista ordenada por linha, junto com os títulos `#`.

Uma função `content_start_line(heading)` devolve a primeira linha do texto da seção: a própria linha do título quando `inline` é verdadeiro e a linha seguinte nos demais casos. `build_section_tree` (fatia de texto e `content_char_range`) e `make_orphan_cleaner` passam a usar essa função. Sem isso, o filtro de órfãos descarta os rótulos: no protótipo com o limite de 20 caracteres, 5 dos 8 rótulos de `smart_tech_microgrids` sumiram porque todo o texto deles está na linha do rótulo.

Nível 1 porque os rótulos aparecem no fim do artigo, depois da conclusão (`5. Conclusions`, nível 1 pela numeração). Com nível 2 eles virariam filhos da conclusão.

Alternativa: reescrever o Markdown, quebrando `**Funding:** texto` em `# Funding` e `texto`. Rejeitada porque os offsets de caractere do Markdown alimentam o mapa de páginas e os retângulos das citações (`enrich_chunks_with_line_rects`). Alterar o texto deslocaria esses offsets.

### Fusão não junta título numerado nem nome conhecido

`make_adjacent_merger` deixa de juntar o próximo título quando ele:
- casa algum padrão de `NUMBERING_PATTERNS` (depois de `strip_markup`), ou
- casa por inteiro (`re.fullmatch`) algum alias de `ROLE_ALIASES`, depois de `normalize_title_for_alias`, ou
- é `inline`.

Casamento por inteiro porque vários aliases não têm âncora (`m[ée]todos?`, `conclus[ãa]o`). Com busca parcial, a segunda linha de um título quebrado como "MÉTODOS DE CLASSIFICAÇÃO" deixaria de ser fundida.

O título atual também não absorve vizinhos quando é `inline`. O caso coberto hoje por `test_make_adjacent_merger` ("1.0. DO OBJETO:" seguido de um título sem numeração) continua igual.

### Métrica por caminho de títulos

`identified_sections` em `test_ingestion_sections.py` passa a ler cada título de `section_path` de cada chunk, guardando a menor página em que o título aparece. Uma seção anotada conta como identificada quando o título normalizado aparece com a página anotada.

Motivo: "2. Desenvolvimento" vem logo antes de "2.1" e não tem texto próprio, então nunca gera chunk. A árvore tem a seção, e ela aparece no caminho dos chunks de "2.1". A versão por `section_title` não enxerga seções assim. Para seções com texto, o resultado é o mesmo, porque o título da seção também está no fim do caminho dos chunks dela.

### Piso

O piso sobe para o placar medido depois da implementação, arredondado para baixo, como manda `testing-methodology/references/05-ia.md`. Se o placar for 55/55, o piso vira `1.0`, e qualquer documento novo com uma seção não identificada derruba o teste. Essa é a consequência pretendida da regra: cada documento novo obriga a decidir entre melhorar a heurística e justificar a queda do piso.

## Risks / Trade-offs

- [A lista de rótulos deixa de fora editoras com outros nomes ("Declaration of Competing Interest", "CRediT authorship")] → O acervo mostra o rótulo que falta. A pessoa que anota o documento estende a lista na mesma mudança.
- [Um título que começa com número por acaso, como "2020 em revisão", deixa de ser fundido com a linha anterior] → Aceito. Um título quebrado cuja segunda linha começa com número é mais raro que o caso "2. Desenvolvimento" seguido de "2.1".
- [Piso 1.0 deixa a suíte frágil a cada documento novo] → É o comportamento pedido pela regra do piso. Baixar exige justificativa registrada no OpenSpec.
- [`inline` muda a forma de cálculo do intervalo de texto, o que pode deslocar `char_start` de seções existentes] → Só títulos `inline` mudam de regra. Teste em `test_section_tree.py` cobre o intervalo de um título `inline` e mantém `test_build_section_tree_char_offsets_integrity` passando.

## Migration Plan

Sem migração. A próxima avaliação de cada documento reingere o PDF com as seções novas. Reverter o commit restaura o comportamento anterior.
