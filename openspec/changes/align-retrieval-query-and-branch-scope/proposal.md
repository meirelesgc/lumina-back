## Why

A recuperação monta a consulta vetorial com `SECTION: <título da taxonomia>` repetido três vezes antes do texto do ramo (issue #15). Títulos de taxonomia como "Fundamentação da Revisão" não aparecem no documento, e o embedding da consulta se aproxima de um cabeçalho que não existe. Os prompts que classificam o escopo do ramo e geram as expansões de consulta falam de editais e de "conformidade normativa" (issue #17), mas o Lumina avalia artigos, revisões sistemáticas, anteprojetos e relatórios técnicos. O escopo `ENTIRE_DOCUMENT` também não tem efeito definido na recuperação.

## What Changes

- A consulta vetorial de cada ramo passa a ser `<título do ramo>: <descrição do ramo>`, sem o título da taxonomia. As expansões de consulta entram na busca como estão, sem o cabeçalho `SECTION:`. A busca léxica continua com o mesmo texto do ramo.
- O prompt do classificador de escopo passa a usar exemplos de seções de documentos acadêmicos (Resumo, Introdução, Metodologia, Resultados, Conclusão) e a tipificação como contexto para decidir quais seções o documento costuma ter.
- O prompt de expansão de consultas passa a tratar de documentos acadêmicos e técnicos e pede formulações escritas como o trecho que responderia ao ramo, em forma afirmativa, sem palavras de enunciado como "o manuscrito apresenta".
- O escopo `ENTIRE_DOCUMENT` ganha efeito definido e testado: busca no documento inteiro, sem roteamento por seção.
- As análises e expansões já gravadas continuam valendo até serem regeneradas. O mantenedor regenera depois do merge com `poetry run task enrich-branches --force`.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: adiciona os requisitos de montagem da consulta de recuperação por ramo e de efeito do escopo de busca do ramo, e o requisito de que a análise de escopo e a expansão de consultas usem o contexto dos documentos acadêmicos atendidos.

## Impact

- **Código:** `lumina/prompts.py` (remove `QUERY`), `lumina/services/ai/stages/retrieval.py`, `lumina/services/ai/branch_analyzer.py`, `lumina/services/ai/query_expansion_service.py`.
- **API e banco:** nenhuma mudança de contrato nem de schema. O campo `retriever_query` da auditoria da avaliação passa a guardar a consulta nova.
- **Dados:** análises de escopo e expansões geradas com os prompts antigos seguem ativas até a regeneração manual.
- **Testes:** `tests/unit/services/test_ai_stages.py`, `tests/unit/services/test_branch_analyzer.py`, `tests/unit/services/test_query_expansion_service.py`.
- **Medição:** o teste de linha de base da change `measure-retrieval-on-annotated-corpus` ainda não está na `main`. Esta mudança roda esse teste localmente antes e depois e registra os números em `tasks.md`, sem versionar os arquivos dele.
