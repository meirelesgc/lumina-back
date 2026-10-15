## 1. Medição antes da mudança

- [ ] 1.1 Copiar para o worktree, sem adicionar ao git, os arquivos do teste de linha de base que estão só no working tree do mantenedor: `tests/conftest.py` (imagem `pgvector/pgvector:pg16`), `tests/ai/evaluation/retrieval/conftest.py`, `tests/ai/evaluation/retrieval/test_retrieval_baseline.py`, `tests/fixtures/documents/corpus.py` e `tests/fixtures/documents/research_proposal/estrategias_teste_software_llm_judge_hitl.retrieval.yaml`. Rodar `poetry run pytest tests/ai/evaluation/retrieval --run-ai -s` no código de `origin/main` (worktree separado) e registrar abaixo as frases encontradas e o contexto médio. O teste falha por falta de `baseline.yaml`; o que importa é o placar impresso.
- [x] 1.2 Rodar o classificador de escopo atual sobre os ramos do gabarito do anteprojeto e três ramos de revisão sistemática citados nas issues, com o modelo rápido real, e registrar abaixo escopo e seção esperada de cada ramo.

## 2. Testes (antes da implementação)

- [x] 2.1 Em `tests/unit/services/test_ai_stages.py`, escrever o teste que chama `retrieve_criteria_payload` com um ramo sob a taxonomia "Fundamentação da Revisão" e expansões, e verifica que a busca vetorial e a léxica recebem `<título>: <descrição>`, que cada expansão é buscada pelo próprio texto e que `retriever_query` é a consulta do ramo. Verificar que o teste falha antes da mudança.
- [x] 2.2 No mesmo arquivo, escrever o teste do ramo sem descrição: a consulta é só o título. Verificar que falha antes da mudança (hoje sai `Título: `).
- [x] 2.3 No mesmo arquivo, escrever os testes de escopo: com `ENTIRE_DOCUMENT`, `UNKNOWN` ou sem análise, a recuperação não consulta os resumos de seção e a busca vetorial usa o filtro do documento inteiro; com `SPECIFIC_SECTION` e seção dentro do limiar, a busca fica restrita a ela. Guarda: passam desde o início, porque o código já se comporta assim.
- [x] 2.4 Em `tests/unit/services/test_branch_analyzer.py`, escrever o teste que captura o pedido enviado ao modelo para um ramo da tipificação "Revisão Sistemática" e verifica que ele traz tipificação, taxonomia e ramo, cita Introdução e Metodologia e não cita "Habilitação Jurídica", "Termo de Referência" nem "edital". Verificar que o teste falha antes da mudança.
- [x] 2.5 Em `tests/unit/services/test_query_expansion_service.py`, escrever o teste que captura o pedido de expansão e verifica que ele cita artigos, revisões sistemáticas, anteprojetos e relatórios técnicos, pede formulações afirmativas, cita "o manuscrito apresenta" como palavra a evitar e não fala em "conformidade normativa". Verificar que falha antes da mudança.

## 3. Implementação

- [x] 3.1 Em `lumina/services/ai/stages/retrieval.py`, montar a consulta com o texto do ramo (mesma regra de vazio de `requirement`), usar o texto de cada expansão sem prefixo e remover `QUERY` de `lumina/prompts.py`. Verificar que os testes 2.1 a 2.3 passam.
- [x] 3.2 Reescrever `BRANCH_ANALYSIS_PROMPT` em `lumina/services/ai/branch_analyzer.py` para documentos acadêmicos e técnicos, com as seções típicas de cada tipo e a tipificação como contexto. Verificar que o teste 2.4 passa.
- [x] 3.3 Reescrever `EXPANSION_PROMPT` em `lumina/services/ai/query_expansion_service.py` para documentos acadêmicos e técnicos, pedindo formulações afirmativas no estilo do trecho esperado. Verificar que o teste 2.5 passa.
- [x] 3.4 Atualizar a seção "Recuperação de Evidências por Critério" de `docs/ia-plataforma.md` com a consulta nova e o efeito de `ENTIRE_DOCUMENT`. Verificar com `grep -n "SECTION:" docs/ia-plataforma.md` que o modelo antigo saiu.

## 4. Medição depois da mudança

- [ ] 4.1 Rodar de novo `poetry run pytest tests/ai/evaluation/retrieval --run-ai -s` e registrar abaixo o placar e o contexto médio. Se o documento encontrar menos frases que na tarefa 1.1, parar e levar o resultado ao mantenedor antes de seguir.
- [x] 4.2 Rodar o classificador novo sobre os mesmos ramos da tarefa 1.2 e registrar abaixo escopo e seção esperada de cada ramo, ao lado do resultado antigo.
- [ ] 4.3 Remover do worktree os arquivos copiados na tarefa 1.1 e restaurar `tests/conftest.py`. Verificar com `git status` que nenhum deles entra no commit.

## 5. Verificação e entrega

- [ ] 5.1 Rodar `poetry run task test`, `poetry run ruff check` e `poetry run ruff format --check`. Registrar abaixo o resultado que de fato rodou.
- [ ] 5.2 Commitar os artefatos do OpenSpec (`docs(openspec): ...`) separados do código e dos testes (`feat(retrieval): ...`), abrir o PR citando as issues #15 e #17 e incluir no PR o passo pós-merge `poetry run task enrich-branches --force`.

## Registro

### Tarefas 1.2 e 4.2: classificador de escopo

`gpt-4o-mini` (modelo rápido do `.env`), mesmos ramos e mesmo contexto. Duas execuções do prompt final deram o mesmo resultado, com uma exceção: "Estado da arte" saiu `SPECIFIC_SECTION (Introdução)` na primeira e `ENTIRE_DOCUMENT` na segunda.

| Tipificação | Ramo | Prompt de edital | Prompt acadêmico |
|---|---|---|---|
| Validação de Ante-Projeto | Contextualização do problema | SPECIFIC_SECTION (Contextualização do Problema) | SPECIFIC_SECTION (Problema de Pesquisa) |
| Validação de Ante-Projeto | Relevância do problema com base na literatura | ENTIRE_DOCUMENT | SPECIFIC_SECTION (Justificativa) |
| Validação de Ante-Projeto | Trabalhos relacionados | SPECIFIC_SECTION (Trabalhos Relacionados) | SPECIFIC_SECTION (Trabalhos Relacionados) |
| Validação de Ante-Projeto | Lacunas, limitações e aspectos pouco explorados | ENTIRE_DOCUMENT | ENTIRE_DOCUMENT |
| Validação de Ante-Projeto | Delimitação do contexto da pesquisa | SPECIFIC_SECTION (Delimitação do Contexto da Pesquisa) | SPECIFIC_SECTION (Problema de Pesquisa) |
| Validação de Ante-Projeto | Hipóteses ou proposições | SPECIFIC_SECTION (Hipóteses ou Proposições) | SPECIFIC_SECTION (Problema de Pesquisa) |
| Validação de Ante-Projeto | Questão principal de pesquisa | SPECIFIC_SECTION (Questão de Pesquisa) | SPECIFIC_SECTION (Problema de Pesquisa) |
| Validação de Ante-Projeto | Alinhamento com os objetivos | ENTIRE_DOCUMENT | SPECIFIC_SECTION (Objetivos) |
| Revisão Sistemática | Existência de justificativa da revisão | SPECIFIC_SECTION (Justificativa da Revisão) | SPECIFIC_SECTION (Justificativa) |
| Revisão Sistemática | Revisões semelhantes identificadas | ENTIRE_DOCUMENT | ENTIRE_DOCUMENT |
| Revisão Sistemática | Estado da arte | ENTIRE_DOCUMENT | ENTIRE_DOCUMENT |

O anteprojeto tem as seções Introdução, Problema de pesquisa, Objetivos, Justificativa, Metodologia e Referências. Com o prompt de edital, quatro dos oito ramos receberam nomes de seção que o documento não tem. Com o prompt acadêmico, todos os nomes existem no documento. Segundo as páginas do gabarito, "Contextualização do problema" e "Relevância do problema" têm a evidência na Introdução, e o classificador aponta para outra seção. Ver o risco correspondente em `design.md`.

Duas versões intermediárias do prompt foram descartadas. A primeira, sem a lista de seções por tipo, sugeriu "Discussão" para um anteprojeto. A segunda, sem a regra "na dúvida, documento inteiro", devolveu `SPECIFIC_SECTION` para os onze ramos.

### Expansões de consulta (amostra)

"Existência de justificativa da revisão", prompt de edital:
- [paraphrase] O manuscrito fornece uma explicação convincente para a necessidade da Revisão Sistemática?
- [section_hint] A seção de justificativas do manuscrito aborda a importância da Revisão Sistemática?

Prompt acadêmico:
- [paraphrase] A justificativa para a realização da Revisão Sistemática é apresentada de forma clara e fundamentada, evidenciando a relevância do tema abordado.
- [sub_question] A fundamentação da Revisão Sistemática é sustentada por evidências que demonstram a lacuna existente na literatura, justificando assim a sua execução.

### Tarefas 1.1 e 4.1: recuperação sobre o acervo

Pendente: o Docker não estava disponível no WSL durante a implementação, e o teste sobe o banco por Testcontainers.

### Tarefa 5.1: verificação

- `ruff check` e `ruff format --check` nos 7 arquivos alterados: sem apontamentos.
- `test_ai_stages.py`, `test_branch_analyzer.py` e `test_query_expansion_service.py` rodaram com um `conftest.py` temporário, fora do git, que desliga a criação do banco: 36 passaram. `test_persist_branch_expansions_versions_and_deactivates` precisa do banco e não rodou.
- `poetry run task test`: pendente, depende do Docker.
