## Why

A recuperação de chunks atual (`lumina/services/ai/stages/retrieval.py`) executa uma única
busca vetorial por critério normativo (`branch`), usando exclusivamente a formulação literal de
`título: descrição` ancorada por seção. Critérios cujo vocabulário diverge do texto do documento
(sinônimos, siglas, decomposição em sub-perguntas) podem não recuperar os trechos relevantes,
mesmo quando presentes no documento.

Esta mudança implementa a Fase 1 do plano de recuperação de chunks: geração assíncrona e
versionada de formulações alternativas de consulta por critério (query expansion), fundidas com
a consulta original via Reciprocal Rank Fusion (RRF) no momento da avaliação — sem custo de
latência adicional na geração, já que as expansões são pré-computadas em background.

Adicionalmente, cria-se o ponto de extensão mockado `generate_chunk_context` (Fase 6 do plano),
posicionado no pipeline de chunking entre o fatiamento monopágina e a geração de embeddings,
controlado por uma flag desligada por padrão, preparando o terreno para contextualização de
chunks sem exigir alteração estrutural futura.

## What Changes

- **Nova tabela `branch_query_expansions`**: armazena formulações alternativas de consulta por
  critério, com versionamento (`generation_version`) e ativação/desativação (`is_active`),
  seguindo o mesmo padrão de auditoria e soft delete de `branches`.
- **Geração assíncrona de expansões**: disparada em background na criação de um `branch` e na
  atualização de `title`/`description`, via `run_branch_query_expansion_background`
  (`lumina/services/ai/query_expansion_service.py`), espelhando o mecanismo já existente de
  `run_branch_section_analysis_background`.
- **Fusão por Reciprocal Rank Fusion no retrieval**: `retrieve_criteria_payload` passa a
  executar a consulta original e as expansões ativas do critério em paralelo, fundindo os
  resultados via `reciprocal_rank_fusion`. Sem expansões ativas, o resultado é idêntico ao
  comportamento anterior (single-query top-k).
- **Congelamento da versão de expansão no snapshot de auditoria**: `AppliedBranch` passa a
  registrar `expansion_generation_version`, preservando rastreabilidade sobre quais expansões
  fundamentaram cada avaliação histórica, mesmo que sejam regeneradas posteriormente.
- **Ponto de extensão mockado para contextualização de chunk**: `generate_chunk_context`
  (`lumina/services/ai/stages/contextualization.py`), com chamada condicionada à flag
  `CONTEXTUAL_CHUNK_ENRICHMENT_ENABLED` (padrão `False`), inserida em
  `create_chunks_from_sections`.

## Capabilities

### New Capabilities
<!-- Nenhuma capacidade nova de produto; extensão interna do motor de recuperação. -->

### Modified Capabilities
- `ai-pipeline`: adiciona requisito de fusão por Reciprocal Rank Fusion de múltiplas
  formulações de consulta na avaliação estruturada de critérios.

## Impact

- **Código Afetado**:
  - `lumina/models.py`: nova classe `BranchQueryExpansion`; novo campo
    `expansion_generation_version` em `AppliedBranch`.
  - `migrations/versions/`: duas novas migrations (criação de tabela e coluna).
  - `lumina/schemas/branch.py`: `ExpansionType`, `QueryExpansionItem`, `QueryExpansionList`.
  - `lumina/repositories/branch_query_expansion_repo.py` (novo).
  - `lumina/services/ai/query_expansion_service.py` (novo).
  - `lumina/services/branch_service.py`: disparo de background task em create/update.
  - `lumina/routers/check_tree/branches.py`: `update_branch` passa a receber `BackgroundTasks`.
  - `lumina/services/ai/stages/retrieval.py`: `reciprocal_rank_fusion` e uso de expansões.
  - `lumina/services/ai/pipeline.py`: orquestração da busca de expansões ativas por release.
  - `lumina/services/ai/stages/contextualization.py` (novo, mock) e wiring em
    `lumina/services/ai/stages/chunking.py`.
  - `lumina/core/settings.py`: `CONTEXTUAL_CHUNK_ENRICHMENT_ENABLED`.
- **APIs e Interfaces Externas**: nenhuma alteração em contratos de API pública. As expansões de
  consulta e o contexto de chunk não são expostos em `BranchPublic`/`TaxonomyPublic` nem em
  nenhum DTO de resposta — uso exclusivo do motor de recuperação.
- **Testes**: novos testes unitários e de integração para o serviço de geração de expansões, o
  repositório de expansões, a fusão RRF no retrieval, o disparo de background tasks em
  `branch_service`, e a chamada condicional de `generate_chunk_context` no chunking.
