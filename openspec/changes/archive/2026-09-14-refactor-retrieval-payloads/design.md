## Context

Atualmente, `lumina/services/ai/stages/retrieval.py` executa a recuperação de evidências em múltiplas passadas sequenciais:
1. `get_eval_args` valida a árvore em dicionário JSON e chama `get_branch_sessions`, que itera sobre a árvore e insere `branch['sessions']`, `branch['retriever_query']` e `branch['initial_chunks']`.
2. Em seguida, `expand_branch_sessions` itera novamente sobre a mesma árvore e substitui `branch['sessions']` pelos chunks expandidos, além de injetar `branch['expanded_chunks']`.
3. Em `pipeline.py`, `simplify_eval_args` itera uma terceira vez para achatar os branches em uma lista de payloads (`create_eval_payload`), lendo `branch.get('sessions')` e definindo `expected_session`.

Essa abordagem gera forte acoplamento temporal, mutação imprevisível de dicionários aninhados e confusão conceitual ao utilizar o termo `sessions` (com 'ss') para designar fragmentos textuais (chunks) e seções de documentos.

## Goals / Non-Goals

**Goals:**
- Consolidar a recuperação em um fluxo coeso e direto por critério (`branch`), gerando a lista de payloads de avaliação em uma única passada limpa.
- Padronizar o vocabulário de domínio: substituir `sessions` por `evidence_chunks` / `chunks` e `expected_session` por `expected_section`.
- Manter total compatibilidade do contrato de dados consumido pelos estágios downstream (`evaluation`, `citations`, `synthesis`).

**Non-Goals:**
- Não implementar paralelização ou concorrência assíncrona (`asyncio.gather`) neste momento (conforme escopo restrito aos pontos 2 e 3).
- Não alterar parâmetros de busca vetorial (`k=3`, margem de expansão $\pm 2$, embeddings ou filtros relacionais).

## Decisions

### 1. Consolidação da Recuperação por Critério
- **Decisão**: Extrair a lógica de recuperação e formatação de contexto em uma função focada por critério: `retrieve_criteria_payload(vstore, taxonomy, branch, base_filter)`.
- A função de entrada do estágio no pipeline torna-se `retrieve_evaluation_payloads(vstore, tree, db_release) -> list[dict]`, que itera a árvore uma única vez e monta a lista de payloads prontos para avaliação.
- *Alternativa considerada*: Manter a mutação in-place em 3 passadas e apenas renomear as chaves de dicionário. Rejeitada por perpetuar o anti-pattern de mutabilidade de estado transitório.

### 2. Normalização Semântica do Vocabulário
- **Decisão**: 
  - `branch['sessions']` $\rightarrow$ `evidence_chunks` (ou `chunks`).
  - `get_branch_sessions` e `expand_branch_sessions` $\rightarrow$ consolidados em helpers claros como `retrieve_branch_chunks` e `expand_chunks`.
  - `expected_session` $\rightarrow$ `expected_section` (mantendo alias para compatibilidade com prompts se necessário).
  - `_sessions` no payload $\rightarrow$ `_chunks` (mantendo alias retrocompatível se alguma etapa downstream exigir a chave legada).
- *Alternativa considerada*: Renomear apenas os métodos públicos. Rejeitada pois o termo incorreto permaneceria no miolo do processamento de RAG.

### 3. Retrocompatibilidade no Módulo
- **Decisão**: Manter aliases / wrappers de `get_eval_args` e `simplify_eval_args` apontando para a nova implementação ou marcados como compatibilidade, permitindo transição suave sem quebrar chamadas legadas em testes.

## Risks / Trade-offs

- **[Risco] Quebra em testes unitários que testam dicionários intermediários**:
  - *Mitigação*: Ajustar os testes unitários em `tests/unit/services/test_ai_stages.py` para validar as novas funções semânticas e manter aliases para as chaves do payload final (`_sessions` / `_chunks`).
