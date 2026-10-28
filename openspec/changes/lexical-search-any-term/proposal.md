## Why

A recuperação de evidências funde a busca vetorial com a busca léxica por RRF, mas a busca léxica exige que um chunk contenha todos os termos do título e da descrição do ramo (`plainto_tsquery`, que combina os termos com AND). No acervo anotado, nenhum dos 146 ramos recebe chunk da busca léxica, e a fusão roda só com a busca vetorial ([issue #16](https://github.com/meirelesgc/lumina-back/issues/16)).

## What Changes

- `lexical_search` passa a aceitar chunks que contenham qualquer termo da consulta (OR). A ordenação por `ts_rank` passa a descontar o tamanho do chunk, para um chunk longo não subir só por repetir termos genéricos.
- A consulta léxica passa a usar só o título do ramo. A busca vetorial continua com título e descrição. Com a descrição inteira e o OR, o baseline com IA caiu abaixo do piso de seção e página (ver `design.md`).
- A consulta continua passando pela normalização do `plainto_tsquery` (stopwords, radicais, pontuação), então o texto do ramo não vira sintaxe de `tsquery`.
- Novo teste de integração, sem IA, sobre o acervo anotado: a busca léxica devolve chunks para os ramos com evidência dos documentos em português e para o ramo de exemplo da issue #16.
- O baseline de recuperação com IA roda antes e depois da mudança. Os pisos que subirem sobem no mesmo commit.
- Ficam fora desta mudança, com issues próprias:
  - remover palavras de enunciado da consulta, que piorou o resultado na medição sem IA ([issue #37](https://github.com/meirelesgc/lumina-back/issues/37)). Tirar a descrição da consulta léxica já tira a maior parte dessas palavras;
  - busca léxica em documentos em inglês, que a configuração `'portuguese'` fixa não encontra ([issue #38](https://github.com/meirelesgc/lumina-back/issues/38)).

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: adiciona o requisito da busca léxica por qualquer termo do critério na recuperação híbrida.

## Impact

- **Código de produção:** `lexical_search` em `lumina/services/ai/stages/vector_store_sql.py` e a consulta léxica montada em `retrieve_criteria_payload` (`lumina/services/ai/stages/retrieval.py`).
- **Testes:** novo `tests/integration/test_lexical_search.py`. Pisos de `tests/ai/evaluation/retrieval/test_retrieval_baseline.py`.
- **Comportamento:** a fusão RRF passa a receber uma lista léxica não vazia para quase todo ramo, o que muda a ordem das evidências que o avaliador recebe.
- **Custo:** nenhum em produção. O baseline com IA gera embeddings do acervo duas vezes (antes e depois).
