## Context

Hoje, ao criar ou editar um ramo, `branch_service.dispatch_branch_enrichment` dispara duas tarefas em segundo plano: a classificação de escopo (`branch_analyzer.run_branch_section_analysis_background`) e as expansões de consulta (`query_expansion_service`). A classificação grava uma linha versionada em `branch_section_requirements`. Na avaliação, `process_release_pipeline` lê as linhas ativas com `branch_section_requirement_repo.get_active_grouped` e passa um dicionário por ramo para `selection.select_evaluation_payloads`, que grava `section_requirement_version` em cada `AppliedBranch`.

A árvore que a avaliação percorre chega a `iter_tree_branches` serializada por `TypificationList`, e cada ramo usa `BranchPublic`. Um campo novo em `BranchPublic` chega ao dicionário do ramo no pipeline sem outra mudança.

`select_sections` já trata os três escopos: `ENTIRE_DOCUMENT` devolve todas as seções sem chamar o seletor, e `expected_section` entra no prompt como "Seção esperada pelo analista". Os gabaritos `<nome>.retrieval.yaml` anotam `scope` e `expected_section` por ramo com os mesmos valores do enum `SectionRequirementScope`.

### Experimento que motivou a mudança

Em 2026-10-29, o placar de `tests/ai/evaluation/retrieval/test_outline_selection.py` rodou uma vez em cada variante sobre os 146 ramos do acervo (75 com evidência, 71 sem):

| Variante | Recall de trechos (piso 0.86) | Acerto de inexistência (piso 0.46) | Segurança de inexistência (piso 0.85) |
| :--- | :--- | :--- | :--- |
| Escopo e seção do gabarito | 117/129 = 0.91 | 40/71 = 0.56 | 68/75 = 0.91 |
| Escopo do gabarito, sem seção | 110/129 = 0.85 | 28/71 = 0.39 | 66/75 = 0.88 |
| Sem marcação | 102/129 = 0.79 | 28/71 = 0.39 | 66/75 = 0.88 |

A seção indicada e o atalho de documento inteiro melhoram o contexto. Por isso a marcação manual mantém os três estados.

## Goals / Non-Goals

**Goals:**
- O configurador marca o escopo de cada ramo pela API, e a avaliação usa essa marcação.
- Nenhuma chamada de modelo classifica escopo.
- O veredito registra o escopo e a seção indicada que usou.

**Non-Goals:**
- O campo no front-end.
- Copiar a classificação do LLM para os ramos existentes. O banco de desenvolvimento não é o de produção.
- Mudar o seletor, o prompt do seletor ou os pisos dos testes com IA.
- Decidir o destino das expansões de consulta (issue #28). O disparo delas continua igual.

## Decisions

### Colunas no ramo, sem versionamento

`branches` ganha `section_scope` (texto, não nulo, `server_default='UNKNOWN'`) e `expected_section` (texto, nulo). O versionamento de `branch_section_requirements` existia para regerar a classificação do LLM. Uma marcação manual muda pela edição do ramo, e a auditoria (`audit_service.register_action`) já guarda o antes e o depois, porque `old_data` e `new_data` vêm de `BranchPublic`.

O valor fica como texto validado pelo enum do Pydantic, como `branch_section_requirements.scope` já fazia, e não como tipo `ENUM` do PostgreSQL. Alternativa descartada: um `CHECK` no banco para o par escopo e seção. A API é o único caminho de escrita, e a validação no schema dá a mensagem 422 que o configurador vê.

### Nomes dos campos

`section_scope` e `expected_section`, com o enum `SectionRequirementScope` que já existe. Os valores ficam iguais aos dos gabaritos, então `test_retrieval_answer_keys.py`, `test_outline_selection.py` e `test_retrieval_baseline.py` continuam lendo os YAML sem mudança.

### Validação do par

Um `model_validator` comum a `BranchCreate` e `BranchUpdate` aplica as regras:

- `expected_section` passa por `strip()`. Vazio vira `None`.
- `SPECIFIC_SECTION` exige `expected_section`.
- `ENTIRE_DOCUMENT` e `UNKNOWN` recusam `expected_section`.

Em `BranchCreate`, `section_scope` tem padrão `UNKNOWN`. Em `BranchUpdate`, os dois campos são opcionais, e o validador olha `model_fields_set`:

- nenhum dos dois enviado: o serviço mantém a marcação atual;
- `section_scope` enviado: valida o par, com `expected_section` omitido valendo `None`;
- só `expected_section` enviado: 422.

`update_branch` só grava a marcação quando `section_scope` está em `model_fields_set`.

### Avaliação lê a marcação do ramo

`BranchPublic` ganha os dois campos. `select_evaluation_payloads` deixa de receber `section_requirements_by_branch` e monta o requisito a partir do dicionário do ramo (`{'scope': branch['section_scope'], 'expected_section': branch['expected_section']}`). `select_sections` continua recebendo o mesmo dicionário, então os testes com IA que passam o requisito do gabarito não mudam.

`SectionSelection` ganha `expected_section`, e `context_selection` passa a guardá-lo ao lado de `scope`. Assim o veredito registra a dica que o seletor recebeu, papel que `section_requirement_version` cumpria apontando para uma versão.

### O que sai

- `lumina/services/ai/branch_analyzer.py`. `BranchNormativeContext` vai para `query_expansion_service.py`, único consumidor que fica.
- `lumina/repositories/branch_section_requirement_repo.py`, o modelo `BranchSectionRequirement` e o schema Pydantic `BranchSectionRequirement` (saída estruturada do LLM).
- `lumina/scripts/analyze_existing_branches.py` e a tarefa `analyze-branches` em `pyproject.toml`.
- A parte de seção de `lumina/scripts/enrich_existing_branches.py`. O script segue gerando expansões.
- `dispatch_branch_enrichment` passa a disparar só as expansões. `tree_suggestion_service` continua chamando a mesma função.
- `AppliedBranch.section_requirement_version` e a leitura em `save_applied_snapshot`.
- O mock do analisador em `tests/conftest.py` e a menção a `branch_analyzer` em `isolate_background_task_db_writes`.
- `tests/unit/services/test_branch_analyzer.py`, `tests/unit/scripts/test_analyze_existing_branches.py` e `tests/integration/repositories/test_branch_section_requirement_repo.py`.

`retrieve_criteria_payload` em `retrieval.py` continua aceitando `section_requirement`, porque o baseline de recuperação o usa com os valores do gabarito.

### Migração

Uma revisão Alembic sobre a cabeça atual (`ad86bd43da06`):

- `upgrade`: adiciona as duas colunas em `branches`, remove `applied_branches.section_requirement_version` e remove a tabela `branch_section_requirements` com o índice `ix_branch_section_requirements_branch_active`.
- `downgrade`: recria a tabela vazia e a coluna, e remove as colunas novas. As classificações apagadas não voltam.

### Jornada e camada dos testes

Jornada: o configurador cria um ramo marcado com a seção "Metodologia", consulta o ramo e vê a marcação. Edita o título sem mandar a marcação e vê a marcação preservada. Marca o ramo como documento inteiro e depois remove a marcação. Cada passo usa as rotas `/branch` com token, em `tests/integration/routers/check_tree/test_branches.py`, onde já ficam os testes dessas rotas.

Testes focados:
- Os 422 do par escopo e seção, no mesmo arquivo de rotas, verificando que o ramo não mudou.
- A ausência de classificação: um teste de unidade em `tests/unit/services/test_branch_service.py` verifica que `dispatch_branch_enrichment` agenda só a tarefa de expansão.
- A avaliação: `tests/integration/test_release_pipeline.py` já roda o pipeline com seletor falso. Um ramo marcado como documento inteiro recebe todas as seções sem chamar o seletor, e um ramo com seção indicada leva a dica ao prompt do seletor e grava `scope` e `expected_section` em `context_selection`.
- A migração: a suíte cria as tabelas com `create_all`, então só uma base migrada pelo Alembic mostra o efeito sobre ramos existentes. O teste segue o padrão de `tests/integration/check_tree/test_document_groups_repo.py`: cria uma base separada no container, migra até `ad86bd43da06`, insere um ramo com uma linha em `branch_section_requirements`, migra até a nova cabeça e confere que o ramo ficou com `UNKNOWN`, sem seção, e que a tabela antiga não existe mais. Depois roda o `downgrade` e confere que a tabela volta vazia.

## Risks / Trade-offs

- [Até alguém marcar os ramos, a avaliação roda sem marcação, o pior caso do experimento] → O front-end ainda não marca. A marcação pode ser feita pela API, e a proposta registra a queda esperada.
- [O `PUT` deixa de ser uma substituição completa do recurso] → É o que impede o front-end atual de apagar marcações. A regra fica no schema e no teste da jornada.
- [Veredictos antigos perdem `section_requirement_version`] → A coluna só apontava para versões de uma tabela que também sai. `context_selection.scope` continua nesses veredictos.
- [O experimento rodou uma vez por variante, sem medir a variação entre execuções] → A decisão de manter três estados não depende da diferença exata. As quedas na inexistência (40 para 28) e no recall (117 para 102) são maiores que a variação que se espera de uma única execução.
