## Context

O relatório `RELATORIO_RECUPERACAO_CHUNKS_E_CONTEXTO_PDF.md` (seção 2.1) documenta que a
avaliação estruturada de critérios executa uma única busca vetorial (`k=5`) por critério,
formulada como `SECTION: {taxonomia} ... --- {título}: {descrição}`. O plano de ação anexado a
esta mudança detalha 6 fases de melhoria de recuperação; apenas a Fase 1 (query expansion) e a
Fase 6 (mock de contextualização de chunk) estão no escopo desta entrega — as Fases 2 a 5
permanecem conceituais.

## Goals / Non-Goals

**Goals:**
- Permitir múltiplas formulações de consulta por critério, geradas de forma assíncrona e sem
  custo de latência na avaliação.
- Fundir a consulta original com as expansões ativas via Reciprocal Rank Fusion, preservando o
  isolamento por documento já existente (`base_filter`) e o `top_n` atual (5).
- Preservar imutabilidade histórica: o snapshot de auditoria (`AppliedBranch`) referencia a
  versão de geração das expansões usadas em cada avaliação.
- Não expor nenhum dado de enriquecimento (expansões, contexto de chunk) em contratos de API
  externos.
- Criar o ponto de extensão de contextualização de chunk como mock, sem custo de LLM adicional
  enquanto a flag estiver desligada.

**Non-Goals:**
- Roteamento por seção, expansão de vizinhos/merge de janelas, busca híbrida léxica e reranking
  com cross-encoder (Fases 2 a 5) — permanecem conceituais nesta entrega.
- Implementação real da contextualização de chunk (Fase 6) — apenas o mock e o ponto de
  extensão.

## Decisions

### 1. Tabela dedicada `branch_query_expansions`, sem relationship em `Branch`
- **Decisão**: nova tabela, sem alterar `branches`, sem `relationship` ORM em `Branch`. As
  expansões ativas são buscadas sob demanda via `branch_query_expansion_repo.list_active_grouped`
  apenas no caminho de avaliação (`pipeline.process_release_pipeline`).
- **Motivo**: `Branch` é carregado com `lazy='selectin'` em toda a árvore normativa, inclusive
  nos endpoints públicos de CRUD (`routers/check_tree/branches.py`). Uma relationship
  adicionaria uma consulta extra a esses endpoints sem necessidade e criaria uma via implícita
  para o dado de enriquecimento vazar em serializações futuras de `BranchPublic`.
- *Alternativa considerada*: relationship `viewonly=True` filtrada por `is_active`, carregada via
  selectin junto da árvore. Rejeitada por acoplar o dado de enriquecimento ao carregamento
  padrão de `Branch`.

### 2. Fusão por Reciprocal Rank Fusion (RRF) com `k=60`
- **Decisão**: `reciprocal_rank_fusion(result_lists, k=60, top_n=MAX_CHUNKS)` agrega por
  `chunk_id`, somando `1/(k+rank)` por lista e retornando os `top_n` chunks de maior score
  agregado. Com uma única lista de entrada (branch sem expansões ativas), o resultado é
  idêntico ao top-k atual — compatibilidade retroativa garantida sem *feature flag* adicional.
- *Alternativa considerada*: média simples de scores de similaridade coseno entre listas.
  Rejeitada por exigir normalização de escala entre buscas com queries diferentes, enquanto RRF
  opera apenas sobre o rank, é parametricamente estável e é o método padrão da literatura de IR
  para fusão de múltiplos rankings.

### 3. Threading de expansões por dicionário simples, não por sessão de DB em `retrieval.py`
- **Decisão**: `pipeline.process_release_pipeline` busca as expansões ativas de todos os
  branches da árvore em uma única query (`list_active_grouped`) e repassa um dicionário
  `{branch_id: (generation_version, [textos])}` para `retrieve_evaluation_payloads`.
  `lumina/services/ai/stages/retrieval.py` permanece sem dependência de `AsyncSession`.
- **Motivo**: mantém o estágio de retrieval testável sem mocks de banco de dados (como já é
  hoje) e concentra a orquestração de acesso a dados em `pipeline.py`, seu papel já estabelecido.

### 4. Disparo de regeneração em `update_branch` apenas quando título/descrição mudam
- **Decisão**: `branch_service.update_branch` compara `title` e `description` antes/depois e só
  dispara `run_branch_query_expansion_background` quando houver mudança real de conteúdo
  semântico. Mudança isolada de `taxonomy_id` não regenera expansões.
- **Motivo**: expansões são geradas a partir do texto do critério; mudar apenas a taxonomia de
  vínculo não invalida as formulações existentes.

### 5. Congelamento de `expansion_generation_version` em `AppliedBranch`
- **Decisão**: novo campo nullable `expansion_generation_version` em `AppliedBranch`, populado a
  partir do payload de avaliação (`crit_payload['expansion_generation_version']`).
- **Motivo**: extensão direta do princípio de imutabilidade histórica já aplicado ao restante da
  árvore normativa (seção 1.2 do relatório) para o novo dado de enriquecimento.

### 6. Contextualização de chunk como chamada condicional à flag, não sempre-executada
- **Decisão**: `create_chunks_from_sections` só chama `generate_chunk_context` quando
  `SETTINGS.CONTEXTUAL_CHUNK_ENRICHMENT_ENABLED` for `True`. Hoje a flag é `False` por padrão,
  logo a chamada nunca ocorre em produção.
- **Motivo**: evita custo de execução (e, quando implementada de fato, custo de LLM) enquanto a
  funcionalidade não é avaliada e ativada deliberadamente, sem exigir alteração estrutural do
  pipeline de extração quando isso ocorrer.

## Risks / Trade-offs

- **[Risco] Aumento de latência de avaliação por múltiplas buscas vetoriais por critério**:
  - *Mitigação*: buscas executadas em paralelo via `asyncio.gather`; número de expansões
    limitado a 2-4 por critério na geração.
- **[Risco] Mock global de LLM em testes (`mock_fast_model_for_tests`) retorna tipo incompatível
  (`BranchSectionRequirement`) para chamadas de `with_structured_output(QueryExpansionList)`**:
  - *Mitigação*: `generate_query_expansions` valida `isinstance(result, QueryExpansionList)` e
    cai em fallback de lista vazia, mesmo padrão defensivo já usado por
    `analyze_branch_section_requirement`.
