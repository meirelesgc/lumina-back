## Context

`process_release_pipeline` chama `run_document_ingestion`, que extrai os chunks (`extract_pdf_chunks`), anonimiza, gera os resumos de seção e indexa tudo no PGVector, sem devolver nada. Depois carrega as expansões de consulta e os requisitos de seção ativos e chama `retrieve_evaluation_payloads`, que percorre a árvore e chama `retrieve_criteria_payload` para cada ramo. Ramos cujo `document` volta vazio ficam fora da lista e não recebem veredito. `evaluate_criteria_batch` dispara uma chamada por ramo e `save_applied_snapshot` grava um `AppliedBranch` por item.

O payload de cada ramo tem `id`, `document` (texto formatado por `format_context`, com `[FONTE] chunk_id: ...` antes de cada chunk), `source`, `requirement`, `expected_section`, `query`, `presidio_mapping` e `_chunks`, que `process_citations` usa para resolver `chunk_id` em retângulos.

Cada chunk anonimizado carrega `section_index`, `section_title`, `section_path`, `page`, `chunk_index_in_section`, `char_start`, `char_end`, `chunk_id` e `rects`. As seções do acervo são identificadas com título e página corretos (63 de 63), mas alguns títulos falsos viram seção ("(TEIXEIRA, 2005)" no dengue).

O prompt `DOCUMENT_ANALYSIS_PROMPT` chama o contexto de "Trechos recuperados do documento" e manda considerar apenas o que está nos trechos.

Os gabaritos `<nome>.retrieval.yaml` têm 146 ramos em 3 documentos: 75 com evidência e `fulfilled` anotado (45 contemplam), 71 com `evidence: []`, e 11 com escopo `ENTIRE_DOCUMENT`. `tests/fixtures/answer_keys.py` já entrega os chunks anonimizados de cada PDF com cache.

## Goals / Non-Goals

**Goals:**
- Contexto da avaliação escolhido por seções inteiras, com a escolha registrada e auditável.
- Medição do seletor com os gabaritos existentes e do veredicto contra o `fulfilled` anotado, antes e depois da troca.

**Non-Goals:**
- Tabela de seções no banco: o sumário sai dos chunks da própria ingestão, em memória.
- Análise com vários documentos, chat, frontend e agente com ferramentas (#27).
- Remover a geração de embeddings ou o serviço de expansões.

## Decisions

### Jornada e camada dos testes

Jornada: o analista envia um documento para avaliação e espera que o parecer de cada critério se apoie nas partes do documento que tratam dele. Quando o documento não trata do critério, espera ler "não contempla". O seletor e a montagem do payload são funções puras sobre chunks e um modelo, então os testes unitários usam modelo falso e os testes com IA usam o acervo. A integração com `process_release_pipeline` tem um teste com modelos falsos que verifica o veredito de todos os ramos e a seleção gravada.

### Sumário a partir dos chunks

`stages/outline.py` agrupa os chunks por `section_index`, na ordem de leitura. Cada seção recebe o id `s` + `section_index + 1` com dois dígitos, as páginas inicial e final, os tokens estimados (caracteres ÷ 4) e os primeiros 200 caracteres do texto, sem o prefixo `[título]`. O texto da seção é a sequência dos seus chunks. O Markdown do sumário indenta pela profundidade do `section_path`:

```
- [s05] 2. Materials and Methods · p2–p3 · ~610 tokens
  "The methodological approach of the systematic literature review (SLR) was developed..."
  - [s06] 2.1. Eligibility Criteria and Data Collection · p3 · ~450 tokens
    "The descriptors from the Institute of Electrical and Electronics Engineers..."
```

Alternativa: tabela de seções no banco. Adiada: ingestão e avaliação rodam na mesma execução, e só o chat ou o agente (#27) precisariam ler seções depois.

### Laço do seletor

`stages/selection.py` usa o modelo rápido (`get_fast_model`) com `with_structured_output` num schema de rodada: `section_ids` (lista), `reason`, `enough` e `not_found`. O prompt fica em `lumina/prompts.py` e começa pelas instruções fixas e pelo sumário, que se repetem para todos os ramos do documento e aproveitam o cache de prompt. Depois vêm a taxonomia, o título, a descrição, a dica `expected_section` quando existir e, a partir da segunda rodada, o texto das seções já lidas.

Regras do laço:
1. Identificadores fora do sumário são ignorados e registrados.
2. A seleção termina quando `enough` é verdadeiro, quando nenhum id novo e válido é pedido ou ao fim da terceira rodada. Nos três casos, o contexto é o conjunto das seções lidas.
3. `not_found` só vale depois de ao menos uma rodada de leitura. Na primeira rodada ele é ignorado. Se a primeira rodada não trouxer nenhum id válido, o ramo recebe o documento inteiro.
4. Uma saída fora do schema é repetida até 2 vezes. Depois disso, o ramo recebe o documento inteiro e a seleção registra a falha.
5. Os ramos rodam em paralelo, limitados por um semáforo de 8.

A seleção de cada ramo vira um registro com escopo, rodadas (ids pedidos, ids inválidos, motivo e flags), seções finais, tokens enviados, modelo e resultado (`selected`, `entire_document`, `not_found` ou `fallback`).

`ENTIRE_DOCUMENT` não chama o seletor: o contexto são todas as seções. `SPECIFIC_SECTION`, `UNKNOWN` e ramo sem requisito passam pelo seletor.

Alternativa: o avaliador pedir seções ele mesmo. Rejeitada pelo usuário: a seleção separada usa modelo menor e pode ser medida com os gabaritos de recuperação, sem veredictos.

### Payload da avaliação

`select_evaluation_payloads` devolve um payload por ramo com as mesmas chaves que `evaluate_criteria_batch` e `save_applied_snapshot` já leem. `document` é `format_context` sobre os chunks das seções escolhidas, na ordem de leitura, e `_chunks` são esses chunks. A sobreposição de 150 caracteres entre chunks vizinhos continua no texto, porque cortá-la mudaria os limites que as citações usam. O payload ganha `context_selection`.

Para `not_found`, o payload já sai com `fulfilled = False`, `score = 0`, `references = []`, um parecer padrão que lista as seções inspecionadas e `skip_evaluation = True`. `evaluate_criteria_batch` não envia esses itens ao modelo.

### Integração no pipeline

`run_document_ingestion` passa a devolver os chunks anonimizados. `process_release_pipeline` mantém a carga dos requisitos de seção, deixa de carregar as expansões e troca `retrieve_evaluation_payloads` por `select_evaluation_payloads`. `retrieve_evaluation_payloads` sai do código junto com os testes dela em `test_ai_stages.py`. `retrieve_criteria_payload` fica, porque o placar de recuperação o mede e o chat ou o agente podem usá-lo depois.

O prompt de avaliação troca "Trechos recuperados do documento" por "Seções do documento" e "trechos" por "seções" nas regras, mantendo as regras de citação por `chunk_id`.

### Registro da seleção

Nova coluna `context_selection` (JSON, opcional) em `applied_branches`, criada por migração Alembic, com o campo correspondente em `AppliedBranch`. `save_applied_snapshot` grava o registro do payload. A coluna não entra nos schemas públicos, então o frontend não muda.

### Auditoria

Com `DEBUG_INGESTION_AUDIT=True`, a seleção grava `05_outline/<documento>.md`, com o sumário exatamente como o seletor recebe, e `06_selection/<documento>/<ramo>.md`, com as rodadas, o contexto final, os tokens e o veredito. `<documento>` é o nome do PDF sem extensão, como nas etapas atuais, e os arquivos são sobrescritos a cada execução.

### Gabarito de veredictos

`fulfilled` é booleano, obrigatório nos ramos com evidência e opcional nos ramos com `evidence: []`, onde só pode ser `false`. Atendimento parcial é `false`. `test_retrieval_answer_keys.py` ganha essa verificação, e o template e o README do acervo a documentam.

### Medição e critério de aceite

`tests/ai/evaluation/retrieval/test_outline_selection.py` (`@pytest.mark.ai`) roda o seletor sobre os chunks anonimizados de cada gabarito, sem PGVector, com escopo e `expected_section` do YAML. Métricas sobre o acervo:

| Métrica | Acerto | Denominador |
| :--- | :--- | :--- |
| Recall de trechos | o `contains` está no texto do contexto enviado ao avaliador | trechos anotados |
| Erro de inexistência | o seletor concluiu `not_found` num ramo com evidência | ramos com evidência |
| Acerto de inexistência | o seletor concluiu `not_found` num ramo com `evidence: []` | ramos com `evidence: []` |

O relatório também traz, por ramo, as seções escolhidas, as rodadas e o resultado, e, por documento, os tokens enviados contra os tokens do documento inteiro.

`tests/ai/evaluation/verdicts/test_verdict_accuracy.py` (`@pytest.mark.ai`) monta o payload de cada ramo, roda `evaluate_criteria_batch` com o modelo principal e compara o `fulfilled` com o anotado. Ramos com `evidence: []` esperam `false`. O relatório traz acerto, matriz de confusão por documento e os ramos errados. Na linha de base, o payload vem de `retrieve_criteria_payload` sobre o PGVector, como no placar de recuperação, e um ramo sem texto recuperado conta como "não contempla", o equivalente ao ramo sem veredito de hoje. Depois do seletor, o payload vem de `select_evaluation_payloads`.

Cada medição roda três vezes. A comparação usa a mediana de cada lado. O critério de aceite é:
- recall do seletor acima de 0,44; e
- mediana do acerto de `fulfilled` com o seletor maior ou igual à mediana da linha de base.

Se o `gpt-6-luna` não atingir os dois, o `gpt-6.1-sol` é testado como seletor. Se nenhum atingir, a integração não acontece e os resultados ficam registrados em `tasks.md`. Os pisos novos (`MIN_SELECTION_RECALL`, `MIN_FULFILLED_ACCURACY`) recebem o menor valor das três execuções, arredondado para baixo na segunda casa.

### Modelo do avaliador: decisão de custo depois do aceite

O aceite foi medido com o `gpt-6.1-sol` como avaliador: acerto de 0,86 com o seletor, contra 0,79 da recuperação. Depois da integração, o usuário trocou o uso médio para `gpt-6-luna` com `reasoning.effort = medium`, por custo. O `gpt-6.1-sol` custa 20 vezes mais por token (US$ 2 e US$ 10 por milhão de tokens de entrada e saída, contra US$ 0,10 e US$ 0,50). Com o `gpt-6-luna` avaliando, o acerto volta a 0,79 (115 e 116 de 146 em duas execuções), e o erro dominante é "falso não contempla" com as seções certas no contexto. O seletor mantém o recall de 0,87. Uma avaliação completa do acervo de 146 ramos custa cerca de US$ 0,19 com `gpt-6-luna`, contra cerca de US$ 1,50 estimados com o `gpt-6.1-sol`. `MIN_FULFILLED_ACCURACY` desce de 0,84 para 0,78 por essa decisão.

## Risks / Trade-offs

- [Um `not_found` errado vira "não contempla" sem avaliador] → `not_found` só depois de uma leitura. O placar conta o erro de inexistência, e o critério de aceite do veredicto pega o efeito.
- [Títulos falsos de seção poluem o sumário] → O início do texto de cada seção ajuda o seletor. A métrica de títulos do acervo continua valendo para melhorar a detecção.
- [Latência: até 3 chamadas do modelo rápido mais 1 do principal por ramo] → Semáforo de 8 e cache do prefixo. Tokens e tempo por release ficam registrados.
- [A sobreposição entre chunks repete cerca de 15% do texto no contexto] → Aceita para não mudar as citações. O placar registra os tokens enviados.
- [Veredictos variam entre execuções] → Três execuções e comparação por mediana.
- [Com o `gpt-6-luna` no avaliador, o acerto de `fulfilled` não melhora em relação à recuperação antiga] → Decisão de custo do usuário. O teste de veredictos imprime o consumo por etapa, e trocar o modelo do avaliador é uma constante em `lumina/core/llm.py`.
- [O serviço de expansões continua gerando consultas que a avaliação não usa] → A issue #28 decide o destino dele. Fica fora desta mudança.
- [Documentos muito longos geram contextos grandes em `ENTIRE_DOCUMENT` ou no teto de rodadas] → O acervo vai até ~21 mil tokens. Os tokens por ramo ficam registrados. Limite e filtro ficam para quando aparecer o caso.

## Migration Plan

A migração Alembic cria `applied_branches.context_selection`, opcional. Vereditos antigos ficam com o campo vazio. Para reverter: `alembic downgrade` da revisão e reverter os commits.
