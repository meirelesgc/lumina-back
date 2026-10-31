# Design

## Context

Motivação em `proposal.md`. Estado do código na `main` (`5a47ad9`):

- `process_release_pipeline` monta o sumário, chama `select_evaluation_payloads` e avalia. Ele não chama nada de recuperação.
- `create_ai_response`, do chat, usa `get_base_filter`, `lexical_search`, `reciprocal_rank_fusion` e `build_chunk_prompts`.
- `select_payload` usa `format_context`, em `retrieval.py`.
- Só `route_candidate_sections` lê os resumos de seção. A nota em `docs/ia-plataforma.md` diz que eles servem ao chat, mas `get_base_filter` os exclui das buscas do chat.
- Só o próprio `enrich-branches` lê `branch_query_expansions`, para pular ramos. Fora o modelo e a escrita da pipeline, nada lê `expansion_generation_version`.
- `entrypoint.sh` roda `alembic upgrade head` antes de subir a API.

## Goals / Non-Goals

**Goals:**

- Eliminar as chamadas de modelo e os embeddings sem leitor.
- Deixar um único caminho de avaliação no código.
- Manter o comportamento do chat, da seleção de seções e da API.

**Non-Goals:**

- Medir a qualidade do chat. Ele continua sem placar próprio, e a mudança propõe uma issue para isso.
- Mudar `section_scope` e `expected_section`, que a seleção usa como dica.
- Renomear `retrieval.py` ou os gabaritos `<nome>.retrieval.yaml`. O nome gera ruído no diff sem mudar comportamento.
- Editar mudanças arquivadas do OpenSpec.

## Decisions

### Uma mudança só para expansões e recuperação

As duas remoções têm a mesma causa, e as expansões são um parâmetro de `retrieve_criteria_payload`. Separar a remoção manteria a função órfã até uma segunda entrega. A alternativa de transformar as expansões em dica do seletor foi descartada: mantém tabela e chamadas de modelo sem dado que justifique, e o acervo só tem expansões em três ramos.

### Migração apaga dados sem backup

A revisão sobre `0adaecd70bea` faz três operações:

1. `DROP TABLE branch_query_expansions`.
2. `DROP COLUMN applied_branches.expansion_generation_version`.
3. `DELETE` em `langchain_pg_embedding` das linhas com `cmetadata->>'record_type' = 'section_summary'`.

O `DELETE` só roda se `to_regclass('langchain_pg_embedding')` não for nulo, porque `PGVector` cria essa tabela em tempo de execução e uma base nova chega à migração sem ela.

O `downgrade` recria a tabela, o índice e a coluna vazios. Ele não recria os resumos. Se a equipe reverter, os documentos ficam sem resumos, e nenhum código da `main` anterior em produção os lê.

Esta decisão substitui a nota de `outline-section-selection`, que preservava a versão de expansão nos vereditos gravados. A coluna não tem leitor, e `context_selection` registra como cada veredito novo escolheu o contexto.

### `record_type` sai dos filtros

A migração apaga os únicos registros com esse campo, então `get_base_filter` passa a devolver só `source`, e `lexical_search` perde a condição sobre `record_type`. Como o `entrypoint.sh` migra antes de subir a API, nenhum processo novo encontra resumos. Manter o filtro seria código de compatibilidade sem caso de uso. `get_section_filter` e `SECTION_SUMMARY_RECORD_TYPE` saem junto.

### `background_tasks` sai de ramos e da confirmação

`create_branch`, `update_branch` e `confirm_item` só usavam o parâmetro para o disparo removido, e as rotas de `routers/check_tree/branches.py` e o `confirm` de `tree_suggestions.py` só o repassavam. O `_dispatch_background`, `dispatch_branch_enrichment` e `build_branch_context` saem. A geração de sugestões continua com o seu `background_tasks`.

### O que fica em `retrieval.py`

Ficam `get_base_filter`, `format_context`, `reciprocal_rank_fusion` e `build_chunk_prompts`, mais as constantes que eles usam. Em `vector_store_sql.py` fica `lexical_search`. `reranking.py` sai.

### Validação do gabarito continua

`test_retrieval_answer_keys.py` fica, porque a seleção e os vereditos dependem do mesmo gabarito. O campo `expansions` sai dos YAMLs e do modelo. `section_requirement` fica, com o comentário do modelo reescrito para falar da dica do seletor em vez do roteamento.

## Risks / Trade-offs

- [Perda irreversível dos dados apagados] → Nada lê esses dados. Quem quiser guardá-los faz o dump antes do deploy, e o PR registra esse aviso.
- [Script externo depende da tarefa, da tabela ou da flag] → O usuário confirmou a abordagem depois de receber este alerta. O PR lista o que sai.
- [O repositório perde a medição de recuperação vetorial] → O placar não media o chat, que usa outro `k` e não roteia. A issue proposta cobre uma avaliação própria do chat.
- [Migração lenta com muitos embeddings] → O `DELETE` filtra por JSONB sem índice dedicado e faz varredura da tabela. O custo é pontual e roda antes de a API subir.
- [Quem reverter o código fica sem resumos] → Sem efeito: a avaliação e o chat da versão anterior não os leem.

## Migration Plan

1. Fazer o dump da tabela, se a equipe quiser guardar os dados.
2. Fazer o deploy: `entrypoint.sh` aplica a migração e sobe a API.
3. Para reverter, rodar `alembic downgrade -1` e voltar a imagem anterior.
