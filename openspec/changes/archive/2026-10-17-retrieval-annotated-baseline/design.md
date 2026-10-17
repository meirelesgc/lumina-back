## Context

`process_release_pipeline` ingere o PDF com `run_document_ingestion` (extração, anonimização, resumos de seção e indexação no PGVector) e chama `retrieve_evaluation_payloads`. Essa função percorre a árvore e chama `retrieve_criteria_payload` para cada ramo. Para um ramo, a recuperação faz:

1. Roteamento por seção (`route_candidate_sections`), só quando o requisito de seção do ramo tem `scope == SPECIFIC_SECTION`. A função busca os resumos de seção e devolve até 2 `section_title` com distância até 0,25, ou `None`.
2. Busca densa da consulta original e de cada expansão, mais busca léxica (`plainto_tsquery('portuguese', ...)`), fundidas por RRF.
3. Corte em `MAX_CHUNKS = 5` blocos e expansão de vizinhos na mesma seção e página (`expand_and_merge_neighbors`). Cada bloco final mantém os metadados do chunk âncora (`section_title`, `section_path`, `page`, `source`).

O payload devolve os blocos em `_chunks`, na ordem do ranking. Em produção, as expansões e o requisito de seção vêm do banco e são gerados por LLM. Sem eles, a recuperação usa só a consulta original e a busca sem roteamento. `CROSS_ENCODER_RERANKING_ENABLED` vale `False` por padrão.

A busca léxica e a expansão de vizinhos leem `langchain_pg_embedding` direto pela `AsyncSession`, na coleção `langchain`. O container dos testes (`postgres:16`) não tem a extensão `vector`.

`tests/unit/services/test_ingestion_sections.py` já tem a normalização de texto (`normalize`), a leitura do gabarito de seções e a extração com cache.

## Goals / Non-Goals

**Goals:**
- Um gabarito por documento, escrito à mão, que reúne a árvore de critérios e as evidências esperadas para cada ramo.
- Uma verificação sem IA que pega erros de anotação antes de gastar tokens.
- Um placar da recuperação atual, por documento e por ramo, com pisos que só sobem.

**Non-Goals:**
- Mudar a recuperação. Esta mudança só registra o estado atual.
- Medir expansões e requisitos de seção gerados por LLM. O gabarito fixa essas entradas quando o anotador quiser medir o roteamento.
- Medir o reranking por cross-encoder, a avaliação estruturada e a síntese.
- Escrever os `*.retrieval.yaml` dos documentos. O usuário anota.

## Decisions

### Jornada e camada do teste

Jornada: o analista envia um anteprojeto para avaliação com uma árvore de critérios e espera que o parecer de cada critério se apoie nos trechos do documento que tratam daquele critério, e não nos de um critério vizinho.

O teste chama `run_document_ingestion` e `retrieve_criteria_payload` direto, com a árvore lida do gabarito. Passar por `POST /release` exigiria usuário, documento, release, árvore no banco e um LLM falso para a avaliação, e não provaria nada a mais sobre quais trechos chegam ao avaliador. A ingestão e a recuperação rodam pelo mesmo código de produção, com os mesmos embeddings.

### Formato do gabarito

`<nome>.retrieval.yaml` fica ao lado de `<nome>.pdf` e exige `<nome>.sections.yaml` no mesmo lugar. O modelo comentado fica em `tests/fixtures/documents/retrieval_template.yaml`, que não casa com `*.retrieval.yaml` e por isso fica fora da descoberta.

```yaml
tree:
  - typification: <nome>
    taxonomies:
      - title: <título da taxonomia>
        branches:
          - id: <slug único no arquivo>
            title: <título do ramo>
            description: <descrição do ramo>
            section_requirement:          # opcional
              scope: SPECIFIC_SECTION     # SPECIFIC_SECTION | ENTIRE_DOCUMENT | UNKNOWN
              expected_section: <texto>
            expansions: [<consulta>, ...] # opcional
            evidence:                     # [] = o documento não atende o ramo
              - section: <título como em <nome>.sections.yaml> # opcional
                page: <página, 1 = primeira>
                contains: '<trecho do PDF, até ~150 caracteres, numa página>'
```

O teste monta cada ramo como o dicionário que `retrieve_criteria_payload` recebe (`title`, `description`) e a taxonomia com `title`. `expansions` e `section_requirement` vão nos parâmetros de mesmo nome. A tipificação só organiza o arquivo.

`section` é opcional. O anotador o omite quando o trecho fica fora de qualquer seção do `<nome>.sections.yaml`, como a capa e a folha de rosto, que não têm título no PDF. Anotar o rótulo que a ingestão gera para essas páginas compararia o motor com ele mesmo.

O limite de cerca de 150 caracteres vem da sobreposição de 150 caracteres do splitter: um trecho desse tamanho dentro de uma página cabe inteiro em algum chunk. Um trecho que serve a dois ramos aparece nos dois.

Alternativas: só a seção esperada (modelo A) não separa dois ramos da mesma seção. Um inventário de trechos com rótulo de ramo (modelo C) evita repetir trechos, mas obriga a cruzar duas listas para revisar um ramo. O usuário escolheu o modelo B.

### Leitura compartilhada dos gabaritos

`normalize`, `expected_sections`, a extração com cache e a descoberta de gabaritos saem de `test_ingestion_sections.py` para `tests/fixtures/answer_keys.py`, que ganha a leitura do `*.retrieval.yaml` e os chunks anonimizados com cache. `test_ingestion_sections.py` passa a importar desse módulo, sem mudar o comportamento. A normalização ganha a remoção dos prefixos `[título]` no início de cada linha, porque um bloco com vizinhos unidos traz um prefixo por chunk.

A normalização também trata como iguais as aspas retas e curvas (`"`, `“`, `”`, `'`, `‘`, `’`) e o hífen e os travessões (`-`, `‐`, `–`, `—`). O anotador copia os trechos de um leitor de PDF ou digita à mão, e o PDF usa a tipografia do editor. No microgrids, 10 trechos falharam na consistência só por aspas e travessões. Exigir a tipografia exata obrigaria o anotador a reproduzir o caractere do PDF sem mudar o que o trecho diz. A regra só deixa a comparação mais tolerante, então o teste de seções mantém o placar.

### Teste de consistência do gabarito, sem IA

`tests/unit/services/test_retrieval_answer_keys.py`, na suíte padrão, parametrizado por gabarito. Tolerância zero, porque um gabarito errado distorce todas as métricas:

- `id` único no arquivo, `scope` válido e `evidence` presente, mesmo vazio.
- Cada `section` informada existe em `<nome>.sections.yaml`, entre seções e subseções.
- Cada `contains` aparece, normalizado, em algum chunk anonimizado (`extract_pdf_chunks` seguido de `anonymize_chunks`) da página anotada e, quando a evidência tem `section`, cujo `section_path` contém a seção. Quando o trecho não aparece ali, a mensagem diz onde ele aparece no documento, se aparecer, para o anotador corrigir a seção ou a página. O teste usa o texto anonimizado porque a recuperação só vê esse texto: um trecho com nome próprio que o Presidio troca precisa ser substituído.

### Teste de avaliação da recuperação

`tests/ai/evaluation/retrieval/test_retrieval_baseline.py`, com `@pytest.mark.ai`, roda em `poetry run task test-ai`.

**Infraestrutura.** `tests/conftest.py` troca a imagem para `pgvector/pgvector:pg16`. O teste cria um `PGVector` com os mesmos parâmetros de `lumina/core/vectorstore.py` (`OpenAIEmbeddings(model='text-embedding-3-small')`, `use_jsonb=True`, `async_mode=True`, coleção padrão `langchain`), ligado ao container. Uma fixture de sessão ingere todos os PDFs anotados na mesma coleção com `run_document_ingestion`, como em produção, e roda a recuperação de todos os ramos uma vez. Os testes leem esse resultado. O filtro de cada documento vem de `get_base_filter` sobre um objeto com o `file_path` do PDF.

**Observação do roteamento.** O teste envolve `route_candidate_sections` com um espião que guarda os candidatos devolvidos por ramo. Assim o teste observa o roteamento sem repetir a regra que monta a consulta de roteamento.

**Verificação crítica, parametrizada por documento.** Todo bloco devolvido tem o `source` do próprio documento. Com os quatro documentos na mesma coleção, uma falha do filtro aparece aqui.

**Métricas, somadas sobre o acervo.** Um bloco é cada documento de `_chunks`. O texto do bloco passa pela mesma normalização do gabarito. Ramos com `evidence: []` ficam fora das métricas.

| Métrica | Acerto | Denominador |
| :--- | :--- | :--- |
| Recall de trechos | o `contains` aparece no texto de algum bloco do ramo | trechos anotados |
| Acerto de seção e página | algum bloco do ramo tem a página anotada e, quando a evidência tem `section`, a seção no `section_path` | trechos anotados |
| Precisão entre ramos | o bloco contém um trecho do próprio ramo | blocos que contêm trecho de algum ramo do mesmo documento |
| Acerto do roteamento | algum candidato é a seção de um trecho do ramo; `None` conta como erro | ramos com `scope: SPECIFIC_SECTION` e ao menos um trecho com `section` |

O acerto de seção e página separa dois defeitos: a recuperação chegou ao lugar certo e cortou o trecho, ou foi para outro lugar. A precisão entre ramos mostra quando um ramo recebe a evidência de outro.

O teste imprime, por documento e por ramo: trechos e seções acertados, a posição do primeiro bloco com trecho do ramo, os candidatos do roteamento e a contagem de blocos do próprio ramo, de outro ramo e sem anotação. Para os ramos com `evidence: []`, imprime as seções dos blocos devolvidos e os candidatos. Para um ramo com `SPECIFIC_SECTION` sem nenhum trecho com `section`, imprime os candidatos sem contar o ramo no roteamento.

**Pisos.** Quatro constantes no módulo: `MIN_EVIDENCE_RECALL`, `MIN_SECTION_PAGE_HIT_RATE`, `MIN_BRANCH_PRECISION` e `MIN_ROUTING_HIT_RATE`. Na implementação, depois da anotação, o teste roda três vezes e cada piso recebe o menor valor medido, arredondado para baixo na segunda casa decimal. Os pisos só sobem. Quando uma métrica não tem casos (nenhum ramo com `SPECIFIC_SECTION`, por exemplo), o teste informa "sem casos" e não verifica aquele piso.

Alternativa: um teste por ramo, aprovado ou reprovado. Rejeitada pelo motivo da seção "Extração determinística" de `05-ia.md`: a heurística não acerta todos os casos, e um teste vermelho para sempre leva alguém a apagar os casos difíceis.

## Risks / Trade-offs

- [Embeddings da OpenAI podem variar um pouco entre chamadas e trocar a ordem de blocos empatados] → O piso usa o menor de três valores medidos, arredondado para baixo.
- [O `PGVector` do teste copia os parâmetros de `lumina/core/vectorstore.py` e pode divergir deles] → Um comentário no teste aponta o arquivo de produção. Extrair uma fábrica do `PGVector` em produção resolveria a duplicação, mas muda código de produção e fica fora desta mudança.
- [O placar reflete o acervo anotado, de 1 a 4 documentos, com poucos ramos] → Cada documento ou ramo novo pode baixar uma métrica. A decisão segue a regra do piso: melhorar a recuperação ou baixar o piso numa mudança do OpenSpec, com a justificativa registrada. Esta mudança já passou por isso: o primeiro placar veio de 1 documento com 5 ramos, e a árvore ampliada tem 3 documentos com 146 ramos. Os pisos refeitos ficam registrados no grupo 6 de `tasks.md`.
- [Trechos de tabela com palavras hifenizadas (`net-‖works`, `mi- crogrids`) não casam com o texto extraído] → O anotador escolhe a parte do trecho que não quebra. A correção da extração fica na issue #25.
- [O nome de autoria em maiúsculas passa pela anonimização e vira título de seção na capa] → O gabarito não anota esse rótulo. A correção fica na issue #22.
- [A ingestão completa a cada `task test-ai` gera embeddings de todos os chunks e roda o Presidio em todo o acervo] → O custo é de centavos por execução. A fixture de sessão ingere cada PDF uma vez.
- [O teste de consistência roda o Presidio na suíte padrão e exige o modelo `pt_core_news_lg`] → `test_metadata_anonymization.py` já roda o Presidio real na suíte padrão.
- [Expansões e requisitos de seção fixados à mão medem um roteamento que a produção talvez não alcance com os valores gerados por LLM] → Fica fora desta mudança, na issue #23. O limite de distância que hoje desliga o roteamento fica na issue #24.

## Migration Plan

Sem migração e sem mudança em produção. A troca da imagem do container afeta só os testes. Para reverter, basta reverter os commits.
