## Why

Um LLM rápido classifica o escopo de seção de cada ramo (`branch_analyzer.py`) com um prompt escrito para editais, e nenhum teste mede o acerto dele ([issue #17](https://github.com/meirelesgc/lumina-back/issues/17)). O escopo e a seção esperada decidem o contexto que o avaliador recebe: no acervo anotado, o seletor de seções perde 15 de 129 trechos e 12 de 71 acertos de inexistência quando roda sem eles (ver `design.md`). Quem configura a árvore conhece os critérios melhor que o classificador, então a marcação passa a ser dela.

## What Changes

- O ramo ganha dois campos, `section_scope` e `expected_section`. `section_scope` aceita `SPECIFIC_SECTION`, `ENTIRE_DOCUMENT` ou `UNKNOWN` (padrão, "sem marcação"). `expected_section` guarda o nome da seção que o seletor procura no sumário.
- `POST /branch` e `PUT /branch` aceitam os dois campos. O `PUT` que omite os campos mantém a marcação atual, para o front-end de hoje não apagar uma marcação ao editar o título.
- A API recusa com 422 `SPECIFIC_SECTION` sem `expected_section` e `expected_section` com os outros escopos.
- `BranchPublic` devolve os dois campos, e a avaliação lê a marcação do próprio ramo.
- O registro da seleção de cada veredito (`context_selection`) passa a guardar a seção indicada, além do escopo.
- **BREAKING:** sai o classificador por LLM: `branch_analyzer.py`, o disparo em segundo plano ao criar ou editar um ramo, o script `analyze-branches`, a parte de seção do script `enrich-branches`, a tabela `branch_section_requirements` e a coluna `applied_branches.section_requirement_version`.
- Os ramos existentes começam sem marcação. A migração não copia a classificação do LLM.
- Fica fora desta mudança:
  - o campo de marcação no front-end, que o time faz depois;
  - o destino das expansões de consulta, que continuam a cargo da [issue #28](https://github.com/meirelesgc/lumina-back/issues/28).

## Capabilities

### New Capabilities

- `criteria-branches`: configuração dos ramos da árvore de critérios pela API, começando pela marcação do escopo de seção.

### Modified Capabilities

- `ai-pipeline`: a seleção de seções passa a usar a marcação do ramo, e a seção indicada entra como dica do seletor.

## Impact

- **API:** `POST /branch`, `PUT /branch` e as respostas que trazem `BranchPublic`, inclusive a árvore de tipificações.
- **Banco:** migração que adiciona `branches.section_scope` e `branches.expected_section`, remove a tabela `branch_section_requirements` e a coluna `applied_branches.section_requirement_version`.
- **Código de produção:** `lumina/models.py`, `lumina/schemas/branch.py`, `lumina/services/branch_service.py`, `lumina/services/tree_suggestion_service.py`, `lumina/services/ai/pipeline.py`, `lumina/services/ai/stages/selection.py`, `lumina/services/ai/query_expansion_service.py`, `lumina/scripts/enrich_existing_branches.py`, `pyproject.toml`. Saem `lumina/services/ai/branch_analyzer.py`, `lumina/repositories/branch_section_requirement_repo.py` e `lumina/scripts/analyze_existing_branches.py`.
- **Comportamento:** até alguém marcar os ramos pela API, toda avaliação roda sem marcação. No acervo anotado isso equivale a recall de trechos 0.79 contra 0.91 com a marcação do gabarito.
- **Custo:** uma chamada de LLM a menos por ramo criado ou editado.
