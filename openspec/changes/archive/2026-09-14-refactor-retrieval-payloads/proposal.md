## Why

A etapa atual de recuperação (`lumina/services/ai/stages/retrieval.py`) percorre a árvore normativa três vezes seguidas (`get_branch_sessions`, `expand_branch_sessions` e `simplify_eval_args`), aplicando sucessivas mutações in-place em dicionários JSON aninhados e misturando terminologias ao nomear listas de chunks de evidência como "sessions" (com 'ss').

Esta refatoração elimina o acoplamento temporal e as passadas redundantes na árvore normativa, consolidando a recuperação e formatação dos critérios em uma passagem direta e estruturada, além de padronizar a terminologia de domínio do RAG (`evidence_chunks` / `chunks` e `sections`).

## What Changes

- **Consolidação em Passada Única**: Substitui o fluxo fragmentado e mutável de `get_eval_args` + `simplify_eval_args` por uma função direta `retrieve_evaluation_payloads(vstore, tree, db_release)` que percorre cada critério (`branch`), recupera os chunks semânticos com `base_filter`, aplica a expansão de margem ($\pm 2$) e gera o payload final de avaliação sem mutações intermediárias em estruturas aninhadas.
- **Normalização Semântica de Vocabulário**:
  - Elimina a denominação errônea `sessions` (com 'ss') para se referir a blocos de texto, adotando `chunks` / `evidence_chunks`.
  - Renomeia `expected_session` para `expected_section` (mantendo compatibilidade nos prompts e consumidores downstream).
  - Renomeia funções auxiliares para refletir o propósito real do domínio (`retrieve_branch_chunks`, `expand_chunks`).
- **Compatibilidade do Contrato Downstream**: O schema dos payloads entregues para o estágio de avaliação (`evaluate_criteria_batch`), resolução de citações e síntese executiva permanece rigorosamente compatível.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade introduzida (refatoração arquitetural interna). -->

### Modified Capabilities
<!-- Nenhuma alteração em requisitos funcionais de specs (skip_specs: true). -->

## Impact

- **Código Afetado**:
  - `lumina/services/ai/stages/retrieval.py`: refatoração da lógica de iteração da árvore, formatação de payloads e nomes de funções/chaves.
  - `lumina/services/ai/pipeline.py`: simplificação da chamada de recuperação em `process_release_pipeline`.
  - `lumina/services/ai/stages/__init__.py`: atualização das funções expostas do módulo de retrieval.
- **APIs e Interfaces Externas**: Nenhuma alteração em rotas HTTP públicas ou schemas de saída de release.
- **Testes**: Atualização de testes unitários em `tests/unit/services/test_ai_stages.py` e testes de integração de pipeline.
