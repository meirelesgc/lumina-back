## Context

`extract_pdf_chunks` monta a árvore com `build_sections_tree_from_markdown`, que devolve só as raízes, e passa essa lista para `create_chunks_from_sections`. O laço de chunking percorre a lista sem descer aos filhos. Cada seção cobre o texto entre o próprio título e o próximo título de qualquer nível (`build_section_tree`), então o texto de um filho não pertence ao intervalo do pai e fica sem chunk.

`flatten_sections` já existe em `sections.py` e devolve a árvore em ordem de leitura. A auditoria, a classificação de papéis e a sugestão de árvore já usam essa função.

Medição feita no planejamento com `dengue_no_brasil.pdf`, chamando as funções atuais com a árvore achatada:

| | Chunks | Caracteres nos chunks | Seções anotadas sem texto | Seções identificadas |
| :--- | ---: | ---: | ---: | ---: |
| Hoje | 23 | 14.526 | 10 de 15 | 3 de 15 |
| Árvore achatada | 91 | 57.191 | 0 de 15 | 12 de 15 |

O Markdown extraído tem 57.517 caracteres normalizados. A diferença para os chunks são os próprios títulos. As 3 seções ainda não identificadas são "Resumo" (o título "RESUMO" não vira heading e o texto cai na seção do DOI), "2. Desenvolvimento" e "2.1", que o extrator junta em um único título. O texto delas está nos chunks.

## Goals / Non-Goals

**Goals:**
- Todo o texto das seções da árvore chega aos chunks.
- Um teste determinístico, na suíte padrão, que trava a perda de texto e mede a identificação de seções sobre um acervo anotado.

**Non-Goals:**
- Melhorar a detecção de títulos (o "RESUMO" e os títulos colados). Fica para depois, guiado pela métrica.
- Mudar recuperação, consulta ou avaliação (issues #15 a #20).
- Remover cabeçalhos e rodapés corridos (#20).

## Decisions

### Achatar a árvore dentro de `create_chunks_from_sections`

A função chama `flatten_sections(sections)` antes do laço. Para listas sem filhos o resultado é a mesma lista, então os testes atuais de `test_chunking.py` continuam válidos e o cenário "Documento sem subseções" da spec se cumpre sem caso especial.

Alternativa: achatar em `extract_pdf_chunks` e manter a função como está. Rejeitada porque deixa a armadilha para o próximo chamador que passar uma árvore.

### `section_index` conta a árvore achatada

`section_index` passa a ser a posição na lista achatada. A expansão de vizinhos (`fetch_chunk_siblings`) agrupa por `section_index` e página, e os resumos de seção pegam o primeiro chunk de cada `section_index`. Os dois passam a operar por subseção, que é a granularidade certa: um vizinho de um chunk de "2.3" deve vir de "2.3". `section_path` continua com o caminho completo (`2. Desenvolvimento > 2.3 ...`).

### Teste de ingestão orientado por gabarito

Jornada: o analista envia uma revisão sistemática com subseções numeradas e espera que a avaliação de um critério encontre trechos de qualquer subseção. O teste prova esse comportamento na camada mais barata que o garante, a extração, porque a recuperação só enxerga o que virou chunk. Um teste pela API exigiria banco, vetores e LLM falso sem provar nada a mais sobre a cobertura do texto.

`tests/unit/services/test_ingestion_sections.py`:
- Descobre todos os `*.sections.yaml` em `tests/fixtures/documents/`. Um documento anotado novo entra no teste sem mudar código.
- Normaliza textos antes de comparar: remove marcação Markdown e HTML que o `pymupdf4llm` insere (`**`, `_`, `<mark>`, `<sup>`), junta espaços em branco e ignora maiúsculas.
- **Teste crítico, parametrizado por documento:** cada `starts_with` aparece no texto concatenado dos chunks do documento, em ordem, sem os prefixos `[título]`. A comparação usa o texto concatenado porque um trecho que cruza a quebra de página fica dividido entre dois chunks sem sobreposição.
- **Teste de métrica, único sobre o acervo:** uma seção anotada conta como identificada quando algum `section_index` dos chunks tem o mesmo título normalizado e a primeira página igual à anotada (`page` do chunk é 0-based; o gabarito é 1-based). O teste imprime o placar por documento e falha quando o total fica abaixo de `MIN_SECTION_IDENTIFICATION_RATE`.
- A extração de cada PDF roda uma vez por sessão de teste (fixture com cache), porque o teste crítico e o de métrica leem o mesmo resultado.

Alternativa: comparar `starts_with` com o início de cada chunk. Rejeitada porque o splitter pode cortar o começo da seção em qualquer ponto e o teste falharia sem perda real de texto.

### Piso da métrica

Medido no planejamento: 12 de 15 (80%). O piso fica em `0.80`, constante no módulo de teste. Quem melhorar a detecção de títulos sobe o piso no mesmo commit. A tarefa de implementação mede de novo e corrige o valor se a implementação final der um placar diferente.

### Gabarito em YAML

O usuário já preencheu o gabarito em YAML, que aceita comentários e é mais fácil de editar à mão que JSON. O `pyyaml` está no lock só como dependência transitiva, então entra como dependência de desenvolvimento declarada.

## Risks / Trade-offs

- [Mais chunks por documento: 23 para 91 no caso medido, com mais chamadas de embedding e de anonimização na ingestão] → É o custo de indexar o texto que já devia estar indexado. Medir o tempo de ingestão antes e depois na tarefa de verificação.
- [O acervo começa com um documento, então o piso de 80% reflete um único layout] → O piso é revisto a cada documento novo. Documentos novos que baixarem a média exigem decisão explícita: melhorar a detecção ou baixar o piso no mesmo commit, com justificativa.
- [Títulos falsos detectados como seções (ex.: "(TEIXEIRA, 2005).") passam a gerar chunks próprios com título ruim] → O texto já está certo; o título ruim afeta só o prefixo e o roteamento. Fica registrado como alvo da melhoria de detecção de títulos.
- [A normalização pode esconder diferenças reais, como hifenização de fim de linha] → A normalização se limita a marcação e espaços. Se um trecho falhar por hifenização, o caso fica visível no relatório do teste.

## Migration Plan

Sem migração. `process_release_pipeline` ingere o documento a cada avaliação, então cada documento passa a ter as subseções indexadas na próxima avaliação. Para reverter, basta reverter o commit.
