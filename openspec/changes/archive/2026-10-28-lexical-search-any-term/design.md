## Context

`retrieve_criteria_payload` monta a consulta léxica como `f'{título}: {descrição}'` e chama `vector_store_sql.lexical_search(session, query_text, source, k)`. A função lê `langchain_pg_embedding` direto pela `AsyncSession`, filtra a coleção `langchain`, o `source` do documento e os chunks sem `record_type` (exclui os resumos de seção), e casa `to_tsvector('portuguese', document)` com `plainto_tsquery('portuguese', query)`. O `plainto_tsquery` liga os termos com `&`.

Medição sem IA, com os chunks dos PDFs anotados indexados pelo caminho de produção e embeddings falsos (146 ramos, 75 com trecho esperado, top 5):

| Variante | Ramos vazios | Trecho esperado no top 5 |
| :--- | :--- | :--- |
| AND (hoje) | 146 | 0 |
| OR | 8 | 17 |
| OR sem palavras de enunciado | 13 | 16 |

Os 8 ramos vazios com OR são de `smart_tech_microgrids`, documento em inglês ([issue #38](https://github.com/meirelesgc/lumina-back/issues/38)).

## Goals / Non-Goals

**Goals:**
- Busca léxica que devolve chunks para os ramos com evidência dos documentos em português.
- Teste na suíte padrão, sem IA, que falha com a combinação AND.

**Non-Goals:**
- Remover palavras de enunciado ([issue #37](https://github.com/meirelesgc/lumina-back/issues/37)).
- Escolher a configuração de idioma por documento ([issue #38](https://github.com/meirelesgc/lumina-back/issues/38)).
- Mudar o RRF, o `k` da busca léxica ou a consulta montada em `retrieval.py`.

## Decisions

### Montagem da `tsquery`

`lexical_search` gera `plainto_tsquery('portuguese', query)`, converte para texto, troca `&` por `|` e converte de volta para `tsquery`, tudo no SQL. O `plainto_tsquery` já tira stopwords, reduz as palavras ao radical e cita cada lexema, então o texto do ramo nunca vira operador. Palavras hifenizadas continuam como frase (`<->`), porque só o `&` muda.

Alternativas descartadas:
- `to_tsquery` com `' | '.join(palavras)` montado em Python: cada palavra precisaria de escape, e um `!` ou `(` no ramo quebraria a consulta.
- `websearch_to_tsquery` com as palavras unidas por `or`: uma palavra que comece com `-` vira negação.

### Consulta só com o título e `ts_rank` normalizado

A primeira versão da correção usava título e descrição na consulta léxica e `ts_rank` sem normalização. No baseline com IA, o acerto de seção e página caiu de 0,49 para 0,47, abaixo do piso. O baseline não usa expansões, então o RRF funde só a lista densa e a léxica, com o mesmo peso: o 1º colocado léxico empata com o 1º denso, e os 5 blocos se dividem entre as duas listas. Com a descrição inteira, a busca léxica põe na frente chunks longos que repetem termos genéricos ("resultados", "metodologia", "pesquisa") e tira do top 5 os acertos da busca densa. O ramo `objetivo-analise` caiu de 4/4 para 0/4.

Medição com embeddings reais, as mesmas métricas do baseline e o mesmo índice para todas as variantes:

| Variante | Recall | Seção e página | Precisão |
| :--- | :--- | :--- | :--- |
| AND (antes desta mudança, igual a só busca densa) | 0,450 | 0,488 | 0,181 |
| OR, título e descrição, `ts_rank` | 0,442 | 0,473 | 0,184 |
| OR, título e descrição, `ts_rank` normalizado | 0,473 | 0,527 | 0,193 |
| OR, só título, `ts_rank` | 0,496 | 0,535 | 0,176 |
| OR, só título, `ts_rank(..., 1)` | 0,519 | 0,566 | 0,184 |
| **OR, só título, `ts_rank(..., 2)`** | **0,535** | **0,581** | **0,191** |
| OR, título e descrição, peso 0,5 da lista léxica no RRF | 0,450 | 0,488 | 0,181 |
| OR, título e descrição, `ts_rank_cd(..., 2)` | 0,403 | 0,457 | 0,180 |

A escolha é a consulta léxica só com o título e `ts_rank(tsvector, tsquery, 2)`, que divide a pontuação pelo tamanho do chunk. Contra o AND, ela ganha trechos em 8 ramos e perde 1 trecho em cada um de 3 ramos (`desfechos-definidos`, `formulario-extracao-definido`, `datas-busca-informadas`). Dos 11 trechos ganhos no saldo, 7 vêm de `introducao-contextualizacao`: os chunks trazem o título da seção no texto (`[1. Introdução]`), e o título do ramo casa com eles.

`retrieve_criteria_payload` passa o título do ramo para `lexical_search`. A busca vetorial e as expansões continuam com título e descrição.

### Título e descrição como reserva

Um título pode não ter nenhum termo no documento. O ramo `titulo-claro-e-objetivo` do anteprojeto tem o título "Título", e o anteprojeto não usa essa palavra. Nesse caso a busca léxica pelo título volta vazia. Quando isso acontece, a recuperação refaz a busca léxica com título e descrição, o mesmo texto da primeira versão da correção. A reserva fica numa função de `retrieval.py` (`branch_lexical_search`), que o teste de integração chama direto. O documento em inglês cai na reserva em quase todos os ramos, então o baseline com IA roda de novo depois dela.

Alternativa descartada: deixar a busca léxica vazia e registrar o ramo como exceção no teste. O usuário preferiu a reserva.

Alternativas descartadas:
- Peso menor para a lista léxica no RRF: com 0,5, nenhum chunk léxico entra no top 5 e o resultado fica igual ao AND.
- `ts_rank_cd`: pior que o AND nas três métricas.
- Remover a busca léxica: mantém o resultado do AND e abre mão do ganho medido.

### Jornada e camada do teste

Jornada: o analista envia uma revisão sistemática para avaliação e espera que o parecer de cada critério se apoie também nos trechos que repetem as palavras do critério, e não só nos trechos parecidos pela busca vetorial.

O teste fica em `tests/integration/test_lexical_search.py` e chama `lexical_search` direto, com a `session` do `conftest.py`. Passar por `POST /release` exigiria LLM falso, embeddings e a árvore no banco, e a fusão RRF esconderia se a lista léxica veio vazia. Os chunks entram pelo caminho de produção: `run_document_ingestion` sobre os PDFs anotados, num `PGVector` ligado ao `engine` do teste com `DeterministicFakeEmbedding`. A busca léxica não usa o vetor, então o embedding falso não muda o resultado. O fixture de ingestão roda uma vez por módulo e apaga a coleção no fim, como `indexed_vectorstore` faz nos testes com IA.

Os cenários da spec viram testes:
- Ramo da issue #16 sobre `smart_tech_microgrids` não serve, porque o documento está em inglês. O teste usa chunks curtos em português indexados à mão para o ramo de exemplo, com um chunk sobre a justificativa da revisão e outros sobre métodos e critérios.
- Ramos com evidência dos documentos em português do acervo: um caso parametrizado por documento, que chama `branch_lexical_search` como a recuperação, exige resultado não vazio para cada ramo com evidência e aponta os ramos vazios na falha.
- Chunk longo com termos repetidos: um chunk curto sobre a justificativa e um chunk longo que repete "justificativa" em meio a texto sem relação. Falha com `ts_rank` sem normalização.
- Descrição fora da consulta léxica: teste unitário em `tests/unit/services/test_ai_stages.py`, no padrão dos testes de `retrieve_criteria_payload` que já existem ali, com `lexical_search` substituído por um espião. Falha enquanto a recuperação passa título e descrição.
- Título sem termo no documento: teste unitário com o espião devolvendo lista vazia na primeira chamada, que confere a segunda chamada com título e descrição. Falha enquanto não houver reserva.
- Outro documento e resumos de seção: guarda, passa antes e depois da mudança.
- Símbolos de sintaxe no ramo: guarda, passa antes e depois, porque o `plainto_tsquery` já trata os símbolos como texto.
- Ramo sem termo pesquisável: guarda, passa antes e depois.

O documento em inglês fica fora do caso parametrizado, com um comentário que cita a issue #38.

### Baseline com IA

`poetry run task test-ai -k test_retrieval_baseline` roda antes da mudança, num `git worktree` do commit anterior, e depois dela. Se uma métrica subir, o piso sobe no commit da implementação, arredondado para baixo como os pisos atuais.

## Risks / Trade-offs

- [O OR traz chunks com um só termo genérico do título] → `ts_rank` põe esses chunks atrás dos que têm mais termos, e o RRF ainda combina com a busca vetorial. A issue #37 trata de pesar ou tirar termos de enunciado.
- [O ganho medido vem de 3 documentos e se concentra em um ramo] → os pisos sobem com o valor medido e o acervo cresce com novos gabaritos. Uma piora futura aparece no baseline.
- [Um título genérico, como "Análise", casa com muitos chunks] → a normalização pelo tamanho e o RRF com a busca densa limitam o efeito. O baseline mede o resultado.
- [Um lexema com `&` dentro, como parte de uma URL, teria o `&` trocado] → a troca acontece dentro do lexema citado, então a consulta continua válida. O pior caso é perder esse termo.

## Migration Plan

Sem migração. A mudança vale para as próximas avaliações, sem reingestão. Para reverter, volte `lexical_search` ao `plainto_tsquery` puro.
