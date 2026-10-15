## 1. Medição antes da mudança

- [ ] 1.1 Copiar para o worktree, sem adicionar ao git, os arquivos do teste de linha de base que estão só no working tree do mantenedor: `tests/conftest.py` (imagem `pgvector/pgvector:pg16`), `tests/ai/evaluation/retrieval/conftest.py`, `tests/ai/evaluation/retrieval/test_retrieval_baseline.py`, `tests/fixtures/documents/corpus.py` e `tests/fixtures/documents/research_proposal/estrategias_teste_software_llm_judge_hitl.retrieval.yaml`. Rodar `poetry run pytest tests/ai/evaluation/retrieval --run-ai -s` no código atual e registrar abaixo as frases encontradas e o contexto médio. O teste falha por falta de `baseline.yaml`; o que importa é o placar impresso.
- [ ] 1.2 Rodar o classificador de escopo atual sobre os ramos do gabarito do anteprojeto, com o modelo rápido real, e registrar abaixo escopo e seção esperada de cada ramo.

## 2. Testes (antes da implementação)

- [ ] 2.1 Em `tests/unit/services/test_ai_stages.py`, escrever o teste que chama `retrieve_criteria_payload` com um ramo sob a taxonomia "Fundamentação da Revisão" e expansões, e verifica que a busca vetorial e a léxica recebem `<título>: <descrição>`, que cada expansão é buscada pelo próprio texto e que nenhuma consulta nem `retriever_query` contém o título da taxonomia. Verificar que o teste falha antes da mudança.
- [ ] 2.2 No mesmo arquivo, escrever o teste do ramo sem descrição: a consulta é só o título. Verificar que falha antes da mudança (hoje sai `Título: `).
- [ ] 2.3 No mesmo arquivo, escrever o teste do escopo `ENTIRE_DOCUMENT`: a recuperação não consulta os resumos de seção e a busca vetorial usa o filtro do documento inteiro. Guarda: passa desde o início, porque o código já trata `ENTIRE_DOCUMENT` como busca global.
- [ ] 2.4 Em `tests/unit/services/test_branch_analyzer.py`, escrever o teste que captura o pedido enviado ao modelo para um ramo da tipificação "Revisão Sistemática" e verifica que ele traz tipificação, taxonomia e ramo, cita Introdução e Metodologia como exemplos e não cita "Habilitação Jurídica", "Termo de Referência" nem "edital". Trocar os exemplos de edital dos testes existentes desse arquivo por ramos acadêmicos. Verificar que o teste novo falha antes da mudança.
- [ ] 2.5 Em `tests/unit/services/test_query_expansion_service.py`, escrever o teste que captura o pedido de expansão e verifica que ele cita artigos, revisões sistemáticas, anteprojetos e relatórios técnicos, pede formulações afirmativas no estilo do texto do documento e não fala em "conformidade normativa". Verificar que falha antes da mudança.

## 3. Implementação

- [ ] 3.1 Em `lumina/services/ai/stages/retrieval.py`, montar a consulta com o texto do ramo (mesma regra de vazio de `requirement`), usar o texto de cada expansão sem prefixo e remover `QUERY` de `lumina/prompts.py`. Verificar que os testes 2.1 a 2.3 passam.
- [ ] 3.2 Reescrever `BRANCH_ANALYSIS_PROMPT` em `lumina/services/ai/branch_analyzer.py` para documentos acadêmicos e técnicos, com exemplos de seção desses documentos e a tipificação como contexto. Verificar que o teste 2.4 passa.
- [ ] 3.3 Reescrever `EXPANSION_PROMPT` em `lumina/services/ai/query_expansion_service.py` para documentos acadêmicos e técnicos, pedindo formulações afirmativas no estilo do trecho esperado. Verificar que o teste 2.5 passa.

## 4. Medição depois da mudança

- [ ] 4.1 Rodar de novo `poetry run pytest tests/ai/evaluation/retrieval --run-ai -s` e registrar abaixo o placar e o contexto médio. Se o documento encontrar menos frases que na tarefa 1.1, parar e levar o resultado ao mantenedor antes de seguir.
- [ ] 4.2 Rodar o classificador novo sobre os mesmos ramos da tarefa 1.2 e registrar abaixo escopo e seção esperada de cada ramo, ao lado do resultado antigo.
- [ ] 4.3 Remover do worktree os arquivos copiados na tarefa 1.1 e restaurar `tests/conftest.py`. Verificar com `git status` que nenhum deles entra no commit.

## 5. Verificação e entrega

- [ ] 5.1 Rodar `poetry run task test`, `poetry run ruff check` e `poetry run ruff format --check`. Registrar abaixo o resultado que de fato rodou.
- [ ] 5.2 Commitar os artefatos do OpenSpec (`docs(openspec): ...`) separados do código e dos testes (`feat(retrieval): ...`), abrir o PR citando as issues #15 e #17 e incluir no PR o passo pós-merge `poetry run task enrich-branches --force`.

## Registro

(preenchido durante a implementação)
