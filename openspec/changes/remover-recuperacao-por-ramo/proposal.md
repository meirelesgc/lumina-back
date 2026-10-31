# Proposal

## Why

A avaliação passou a usar a seleção de seções pelo sumário (#26), mas o caminho anterior continua no código. O Lumina chama o modelo rápido para gerar expansões de consulta que nenhum fluxo lê ([issue #28](https://github.com/meirelesgc/lumina-back/issues/28)) e indexa resumos de seção que só `retrieve_criteria_payload` consulta. Essa função não tem chamador em `lumina/`. O time paga embeddings e chamadas de modelo por um caminho que só os testes executam, e o placar de recuperação mede um código fora de produção.

## What Changes

- Remover a geração de expansões de consulta: o serviço, o repositório, a tarefa `enrich-branches` e os três disparos (criação de ramo, edição de ramo e confirmação de sugestão).
- Remover a recuperação por ramo: `retrieve_criteria_payload`, o roteamento por seção, a busca léxica por ramo, a expansão de vizinhos e o reranking com a flag `CROSS_ENCODER_RERANKING_ENABLED`.
- Parar de gerar resumos de seção na ingestão e apagar os resumos já indexados.
- **BREAKING** Apagar a tabela `branch_query_expansions` e a coluna `applied_branches.expansion_generation_version`. O `downgrade` recria só a estrutura.
- Remover o placar de recuperação (`test_retrieval_baseline.py`) e manter a validação dos gabaritos, que a seleção de seções e os vereditos usam.
- Manter a recuperação do chat: busca vetorial, busca léxica e fusão RRF.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: a ingestão deixa de indexar resumos de seção, o critério de aceite de recuperação sai, a validação dos gabaritos vira requisito próprio e a busca léxica passa a descrever o chat.
- `check-tree-suggestions`: a confirmação de um ramo deixa de disparar expansão de consultas e análise de seção.

## Impact

- **Código:** `lumina/services/ai/query_expansion_service.py`, `lumina/services/ai/stages/` (`retrieval`, `reranking`, `vector_store_sql`, `sections`, `selection`), `lumina/services/ai/pipeline.py`, `lumina/services/branch_service.py`, `lumina/services/tree_suggestion_service.py`, `lumina/scripts/enrich_existing_branches.py`, `lumina/repositories/branch_query_expansion_repo.py`, `lumina/models.py`, `lumina/schemas/branch.py` e os routers de `check_tree`.
- **Banco:** nova revisão Alembic, com perda definitiva dos dados da tabela, da coluna e dos resumos indexados.
- **API:** nenhuma rota ou payload muda.
- **Operação:** a tarefa `enrich-branches` e a variável `CROSS_ENCODER_RERANKING_ENABLED` deixam de existir.
- **Testes e docs:** testes de expansão e de recuperação, gabaritos, `docs/ia-plataforma.md`, `docs/arquitetura-engenharia.md`, `docs/base-de-conhecimento.md` e `tests/fixtures/documents/README.md`.
- **Decisões anteriores:** esta mudança substitui a nota de migração de `outline-section-selection`, que preservava a versão de expansão nos vereditos gravados, e a decisão de manter `retrieve_criteria_payload` sob o placar, registrada em `docs/ia-plataforma.md`.
