## 1. Gabaritos

- [x] 1.1 Criar `tests/fixtures/documents/retrieval_template.yaml` e a seção "Expected retrieval" em `tests/fixtures/documents/README.md`, e verificar que `retrieval_template.yaml` não casa com `*.retrieval.yaml`.
  - Feito no planejamento, para o usuário anotar antes da implementação.
- [x] 1.2 (Usuário) Anotar `<nome>.retrieval.yaml` ao lado dos PDFs escolhidos do acervo. Verificar que existe ao menos um gabarito e que cada um tem o `<nome>.sections.yaml` correspondente. A implementação só começa depois desta tarefa.

## 2. Infraestrutura de teste

- [x] 2.1 Trocar a imagem do container em `tests/conftest.py` de `postgres:16` para `pgvector/pgvector:pg16`. Verificar que `poetry run task test` passa com a mesma contagem de testes de antes.
- [x] 2.2 Extrair `normalize`, `expected_sections`, a extração com cache e a descoberta de gabaritos de `tests/unit/services/test_ingestion_sections.py` para `tests/fixtures/answer_keys.py`. Acrescentar a leitura do `*.retrieval.yaml`, os chunks anonimizados com cache e a remoção dos prefixos `[título]` no início de cada linha. Verificar que `poetry run pytest tests/unit/services/test_ingestion_sections.py -s` passa e imprime o mesmo placar de antes.

## 3. Testes

- [x] 3.1 Criar `tests/unit/services/test_retrieval_answer_keys.py`, parametrizado por gabarito: `id` único, `scope` válido, `evidence` presente, seção existente em `<nome>.sections.yaml` quando informada e `contains` presente num chunk anonimizado da página anotada e da seção, quando informada, com a mensagem indicando onde o trecho aparece quando não está no lugar anotado. É uma guarda: passa desde o início se o gabarito estiver certo. Verificar que o teste falha ao trocar, numa cópia temporária de um gabarito, a página de um trecho e depois a seção, e que a mensagem aponta documento, ramo e trecho. Verificar também que uma evidência sem `section` passa quando o trecho está na página anotada. Se um gabarito do usuário falhar, relatar a falha ao usuário em vez de editar o YAML.
- [x] 3.2 Criar `tests/ai/evaluation/retrieval/test_retrieval_baseline.py` com `@pytest.mark.ai`: `PGVector` do teste ligado ao container, ingestão de todos os PDFs anotados por `run_document_ingestion` numa fixture de sessão, recuperação de todos os ramos por `retrieve_criteria_payload` com espião em `route_candidate_sections`, verificação crítica de `source` por documento, as quatro métricas com placar por documento e por ramo, e os pisos com valor provisório `0.0`. É uma guarda do estado atual. Verificar que `poetry run pytest tests/ai/evaluation/retrieval -s --run-ai -m ai` passa e imprime o placar, e que a verificação crítica falha ao trocar temporariamente o filtro por um sem `source`.
- [x] 3.3 Rodar o teste da tarefa 3.2 três vezes e gravar em `MIN_EVIDENCE_RECALL`, `MIN_SECTION_PAGE_HIT_RATE`, `MIN_BRANCH_PRECISION` e `MIN_ROUTING_HIT_RATE` o menor valor medido de cada métrica, arredondado para baixo na segunda casa decimal. Registrar aqui o placar das três execuções. Verificar que o teste passa com os pisos gravados.
  - Resultado: as três execuções deram o mesmo placar, ramo a ramo, sobre `research_proposal/estrategias_teste_software_llm_judge_hitl.retrieval.yaml`. Pisos gravados: `MIN_EVIDENCE_RECALL = 0.54`, `MIN_SECTION_PAGE_HIT_RATE = 0.54`, `MIN_BRANCH_PRECISION = 0.21`, `MIN_ROUTING_HIT_RATE = 0.0`.

    | Ramo | Trechos | Seção e página | 1º bloco do ramo | Blocos (do ramo / de outro / sem anotação) | Roteamento |
    | :--- | ---: | ---: | :---: | :---: | :--- |
    | `titulo-claro-e-objetivo` | 0/2 | 0/2 | nenhum | 0 / 3 / 1 | `None` (fora do piso) |
    | `introducao-contextualizacao` | 0/7 | 0/7 | nenhum | 0 / 3 / 1 | `None` |
    | `metodologia-percurso` | 8/8 | 8/8 | 1 | 2 / 0 / 1 | `None` |
    | `objetivo-geral` | 0/2 | 0/2 | nenhum | 0 / 3 / 1 | `None` |
    | `objetivos-especificos` | 5/5 | 5/5 | 2 | 1 / 2 / 1 | `None` |
    | **Total** | 13/24 = 0,54 | 13/24 = 0,54 | | precisão 3/14 = 0,21 | 0/4 = 0,00 |

    Os blocos devolvidos caem quase todos em "5. Metodologia" e "4. Justificativa", inclusive nos ramos de título, introdução e objetivo geral. O roteamento devolve `None` para todos os ramos: a menor distância entre "1. Introdução" e os resumos de seção foi 0,50, acima de `SECTION_ROUTING_MAX_DISTANCE = 0.25`, então a busca roda sem filtro de seção.

## 4. Documentação

- [x] 4.1 Acrescentar a `docs/arquitetura-engenharia.md` a seção "Validação da Recuperação sobre Acervo Anotado", com o gabarito, os dois testes, as métricas e a regra dos pisos, e atualizar `.agents/skills/testing-methodology/references/06-projeto-lumina.md` com o novo gabarito e o comando do teste. Verificar que os nomes de arquivos, constantes e comandos citados existem no código.

## 5. Verificação

- [x] 5.1 Rodar `poetry run task test` e `poetry run ruff check` e `poetry run ruff format --check` nos arquivos alterados, e registrar aqui o resultado.
  - Resultado: 343 testes passam e 2 são pulados (os de `@pytest.mark.ai`), contra 340 antes da mudança. A cobertura de `lumina/` fica em 75%, a mesma de antes, porque a mudança não altera código de produção. `ruff check` e `ruff format --check` passam nos cinco arquivos Python alterados.
- [x] 5.2 Rodar `poetry run pytest tests/ai/evaluation/retrieval -s --run-ai -m ai` e registrar aqui o placar final por documento e o tempo da execução.
  - Resultado: 2 testes passam. Placar de `research_proposal/estrategias_teste_software_llm_judge_hitl.retrieval.yaml`: recall de trechos 13/24 (0,54), acerto de seção e página 13/24 (0,54), precisão entre ramos 3/14 (0,21), roteamento 0/4 (0,00). A execução leva 29 s no total (13,5 s de pytest, depois do container no ar), com a ingestão e os embeddings de um documento.
