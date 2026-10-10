## Context

Ver `proposal.md` (Why) e `specs/check-tree-suggestions/spec.md` (requisitos). Estado atual relevante:

- A árvore é `Source` ←N:N→ `Typification` → `Taxonomy` (N:N com `Source`) → `Branch`, com unicidade de título por escopo (índices parciais `deleted_at IS NULL`) e soft delete via `AuditMixin`.
- Os services `source_service`, `typification_service`, `taxonomy_service` e `branch_service` validam, registram auditoria (`audit_service.register_action`) e **fazem `commit` internamente**. `branch_service.create_branch/update_branch` disparam, após o commit, `run_branch_section_analysis_background` e `run_branch_query_expansion_background`.
- A extração de PDF (`lumina/services/ai/stages/extraction.py`: `extract_raw_markdown_and_pages`, `build_sections_tree_from_markdown`, `create_chunks_from_sections`) já gera markdown, mapa de páginas, árvore de seções e chunks com `page`/`section_title`.
- O trabalho assíncrono do projeto usa `BackgroundTasks` do FastAPI, ou `asyncio.create_task`, e abre uma sessão própria com `async_session` (padrão do `branch_analyzer`). Não há fila de jobs.
- LLMs: `get_model()` (gpt-5-mini) e `get_fast_model()` (gpt-4o-mini, com override para testes), usados com `with_structured_output`.
- A telemetria por etapa fica em `run_logger` (JSONL em `PIPELINE_RUNS_DIRECTORY`).

## Goals / Non-Goals

**Goals:**
- Pipeline de geração determinístico nas bordas (extração, validação de evidência, deduplicação), com o LLM restrito a extrair e consolidar candidatos.
- Confirmação atômica: entidade aplicada e item marcado `confirmed` na mesma transação.
- Reutilizar as regras de negócio dos CRUDs existentes sem duplicá-las.
- Testável sem rede: o gerador recebe o modelo por injeção, e os testes usam o override do `get_fast_model`/`get_model`.

**Non-Goals:**
- Formatos além de PDF (DOCX, HTML) e OCR de PDFs escaneados.
- Propor remoções ou mover itens entre taxonomias/tipificações.
- Reprocessar ou regenerar uma sessão existente; para tentar de novo, cria-se uma nova sessão.
- Fila de jobs distribuída ou retomada após restart; o timeout cobre esse caso (ver Riscos).
- Front-end (só a API é coberta aqui).
- Edição dos campos de `document_group_id`/`document_group_item_id` da tipificação; eles ficam nulos nas tipificações criadas por sugestão.

## Decisions

### 1. Modelo de dados: `tree_suggestion_sessions` + `tree_suggestion_items`

**Sessão** (`TreeSuggestionSession`, com `AuditMixin`):
- `id`, `mode` (`create` | `enrich`), `status` (`processing` | `ready` | `failed` | `completed`), `target_typification_id` (FK nullable);
- `file_path`, `original_filename`, `page_count`;
- `error_message`, `run_id` (UUID da telemetria), `generation_model`, `processing_started_at`, `processing_finished_at`.

**Item** (`TreeSuggestionItem`):
- `id`, `session_id` (FK), `kind` (`source` | `typification` | `taxonomy` | `branch`), `operation` (`create` | `update`), `status` (`pending` | `confirmed` | `discarded`);
- `parent_item_id` (FK self, nullable) **ou** `parent_entity_id` (UUID da entidade existente, nullable), com no máximo um preenchido. Itens `source`, `typification` (modo create) e `update` não têm pai;
- `target_entity_id` (para `update`) e `target_snapshot` (JSONB com `title`, `description` e `updated_at` capturados na geração);
- `proposed_title`, `proposed_description`; `final_title`, `final_description` (gravados na confirmação). Para Source/Typification, o campo de título guarda `name`;
- `evidence` (JSONB: lista de `{quote, pages: [int]}`), `rationale`;
- `similar_to_id`, `similarity_note`;
- `applied_entity_id`, `reviewed_by` (FK users), `reviewed_at`, `position` (ordem estável para exibição).

*Alternativas consideradas:* JSON único com a árvore inteira na sessão. Foi descartado porque complica o lock por item, a cascata e as consultas de status. Também foram descartadas tabelas separadas por `kind`, que multiplicariam o código para pouco ganho, já que os campos são quase idênticos.

Os enums ficam em `String` com validação via `Enum` Python/Pydantic, seguindo o padrão do projeto (`role_type`, `scope`).

### 2. Geração em etapas (`lumina/services/ai/tree_suggestion/`)

Função pública `generate_tree_suggestions(pdf_path, mode, existing_tree, model) -> GenerationResult`, sem acesso ao banco: recebe a subárvore existente já carregada e devolve candidatos validados. As etapas:

1. **Extração**: reutiliza `extract_raw_markdown_and_pages` + `build_sections_tree_from_markdown` + `create_chunks_from_sections`. Resultado: texto completo, seções e páginas.
2. **Escopo**: uma chamada ao LLM com o *outline* (títulos de seções e os primeiros parágrafos) e o início do documento. Retorna nome e descrição do Source e, no modo `create`, a lista de tipos documentais regulados. No modo `enrich`, o tipo é a tipificação alvo.
3. **Extração de regras (map)**: agrupa as seções em lotes até um orçamento de caracteres (`TREE_SUGGESTION_BATCH_CHARS`). Para cada lote, o LLM retorna candidatos `{typification_ref, taxonomy_title, taxonomy_description, branch_title, branch_description, quote, rationale}`. Os lotes rodam com concorrência limitada (`asyncio.Semaphore`, `TREE_SUGGESTION_MAX_CONCURRENCY`).
4. **Validação de evidência (determinística)**: normaliza (casefold, espaços e hifenização de quebra de linha) e procura o `quote` no texto completo. Aceita correspondência exata ou, quando não houver, a melhor janela com `rapidfuzz.fuzz.partial_ratio >= TREE_SUGGESTION_EVIDENCE_MIN_SCORE` (padrão 90). As páginas vêm do offset encontrado e do `page_map`. Candidatos sem evidência válida são descartados e contados na telemetria.
5. **Consolidação (reduce)**: agrupa os candidatos por tipificação e por título de taxonomia normalizado. Depois, uma chamada ao LLM por tipificação recebe os candidatos agrupados **e a subárvore existente** e retorna a árvore final: taxonomias e ramos unificados, cada um marcado como `new`, `update_of:<id>` ou `similar_to:<id>`. As evidências são herdadas da união dos candidatos de origem. As referências a IDs devolvidas pelo LLM são validadas contra a subárvore carregada, e IDs inexistentes são ignorados.
6. **Duplicatas (determinístico, complementar)**: para cada item `create`, compara o título normalizado com entidades ativas do mesmo escopo; no modo `create`, as tipificações são comparadas globalmente. Uma correspondência preenche `similar_to_id`, mesmo que o LLM não a tenha sinalizado.

*Por que map-reduce em vez de uma única chamada:* normas universitárias passam de 50 páginas. Lotes por seção mantêm o contexto do modelo focado e permitem paralelismo, e a etapa de consolidação resolve a fragmentação entre lotes.

*Modelo:* `get_model()` nas etapas 3 e 5, onde a qualidade importa; `get_fast_model()` na etapa 2. O nome do modelo usado fica registrado em `generation_model`.

### 3. Execução assíncrona e ciclo de vida

- `POST /tree-suggestion` valida o tipo (content-type `application/pdf` **e** magic bytes `%PDF-`), o tamanho e o número de páginas (via `pymupdf`, antes de criar a sessão). Em seguida salva o arquivo via `Storage`, cria a sessão em `processing`, faz commit e agenda `run_tree_suggestion_background(session_id)` com `BackgroundTasks`.
- O background abre sua própria sessão de banco (`async_session`), carrega a subárvore existente, chama o gerador e persiste os itens. Tudo isso acontece em uma transação que muda o status para `ready`. Em exceção, faz rollback dos itens e grava `failed` + `error_message` (sanitizada com `sanitize_pii`, sem stack trace).
- Telemetria: `run_logger.start_run/start_stage/complete_stage` com as etapas `extraction`, `scope`, `rules`, `evidence`, `consolidation` e contagens (candidatos, descartados por evidência, itens finais).
- **Timeout preguiçoso**: na leitura (GET de sessão ou lista), sessões em `processing` com `processing_started_at` anterior a `now - TREE_SUGGESTION_PROCESSING_TIMEOUT_MINUTES` passam a `failed` ("timeout"). Isso cobre restart do servidor sem precisar de scheduler.

### 4. Confirmação atômica reutilizando os services

Os services atuais fazem commit internamente. Vamos adicionar um parâmetro opcional `commit: bool = True` a `source_service.create_source`, `typification_service.create_typification`, `taxonomy_service.create_taxonomy/update_taxonomy` e `branch_service.create_branch/update_branch`:
- Com `commit=False`, a função faz apenas `flush` e devolve a entidade. Também **não** dispara as tarefas de background do Branch.
- Expomos `branch_service.dispatch_branch_enrichment(background_tasks, branch, context)` para o fluxo de sugestão disparar as análises **após** o próprio commit.

Fluxo de `confirm`:
1. `SELECT ... FOR UPDATE` no item. Se não estiver `pending` → 409. Se a sessão não estiver em `ready` → 409.
2. Resolve o pai: com `parent_item_id`, o pai precisa estar `confirmed` (usa `applied_entity_id`), senão → 409; com `parent_entity_id`, a entidade precisa estar ativa, senão → 409.
3. Para `update`: compara o `updated_at`, o `title` e a `description` atuais com o `target_snapshot`. Se divergirem ou a entidade tiver sido excluída → 409.
4. Chama o service com `commit=False`, usando os valores finais (sobrescrita do corpo, ou os propostos). Se o Source da sessão já estiver confirmado, inclui o `source_id` em `source_ids` (tipificação e taxonomia criadas). Em `update`, cria o vínculo `TaxonomySource` se ainda não existir.
5. Marca o item (`confirmed`, `final_*`, `applied_entity_id`, `reviewed_by`, `reviewed_at`). Se não restar nenhum `pending`, a sessão vira `completed`. Faz **um** commit.
6. Se o item for branch, chama `dispatch_branch_enrichment`.

O `HTTPException` 409/404 vindo dos services (ex.: colisão de título) propaga e causa rollback, então o item continua `pending`.

**Confirmação do Source:** cria o Source com `file_path` da sessão (a mesma URL de storage, sem copiar o arquivo). Depois vincula às tipificações e taxonomias com `applied_entity_id` já confirmadas na sessão e, no modo `enrich`, à tipificação alvo. Os vínculos usam `TypificationSource`/`TaxonomySource` com `created_by`, e o vínculo só é criado se ainda não existir.

*Alternativa considerada:* duplicar a lógica de criação no novo service. Foi descartada por divergir das regras (unicidade, auditoria) com o tempo.

### 5. Descarte

`discard` de item: `FOR UPDATE` no item, CTE recursiva sobre `parent_item_id` para coletar os descendentes `pending` e `UPDATE` em lote para `discarded`, com `reviewed_by/at`. Depois recalcula se a sessão está `completed`. `discard` de sessão faz o mesmo para todos os `pending`. Itens `confirmed` nunca são revertidos.

### 6. API

Router `lumina/routers/check_tree/tree_suggestions.py`, prefixo `/tree-suggestion`, tag `árvore de verificação, sugestões`, protegido por `CurrentUser`:

| Método | Rota | Resposta |
|---|---|---|
| POST | `/tree-suggestion` (multipart: `file`, `typification_id?`) | 202 `TreeSuggestionSessionPublic` |
| GET | `/tree-suggestion?status=&offset=&limit=` | 200 `TreeSuggestionSessionList` (sem itens) |
| GET | `/tree-suggestion/{session_id}` | 200 `TreeSuggestionSessionDetail` (com itens) |
| POST | `/tree-suggestion/{session_id}/items/{item_id}/confirm` (corpo `{title?, description?}`) | 200 `TreeSuggestionItemPublic` |
| POST | `/tree-suggestion/{session_id}/items/{item_id}/discard` | 200 `TreeSuggestionSessionDetail` (para refletir a cascata) |
| POST | `/tree-suggestion/{session_id}/discard` | 200 `TreeSuggestionSessionDetail` |

Os itens são devolvidos como lista plana, ordenada por `position`, com `parent_item_id`/`parent_entity_id`. O front monta a árvore. Isso evita esquemas recursivos e facilita a cascata.

Para exibição, a leitura resolve rótulos das entidades existentes: `target_typification_name` na sessão e `parent_entity_title` em cada item com `parent_entity_id`. Esses campos são calculados na leitura, não persistidos. A demo em `/demos/tree_suggestions/` usa esse payload como referência visual para o front-end.

### 7. Configuração (`Settings`)

`TREE_SUGGESTION_MAX_FILE_MB=20`, `TREE_SUGGESTION_MAX_PAGES=300`, `TREE_SUGGESTION_PROCESSING_TIMEOUT_MINUTES=30`, `TREE_SUGGESTION_BATCH_CHARS=24000`, `TREE_SUGGESTION_MAX_CONCURRENCY=4`, `TREE_SUGGESTION_EVIDENCE_MIN_SCORE=90`.

## Risks / Trade-offs

- [Alucinação do LLM gerando regras inexistentes] → validação determinística de evidência (etapa 4), mais a revisão humana obrigatória.
- [Fragmentação ou duplicação entre lotes] → etapa de consolidação e deduplicação determinística. O que escapar ainda passa pela revisão humana.
- [Restart do servidor deixa sessões presas em `processing`] → timeout preguiçoso na leitura. O usuário cria uma nova sessão.
- [Custo e latência de LLM em documentos grandes] → limites de páginas e tamanho, concorrência limitada e modelo rápido na etapa de escopo. As contagens ficam na telemetria para calibrar.
- [Mudar a assinatura dos services] → parâmetro opcional com padrão `commit=True`, o que mantém o comportamento atual. Os testes existentes dos CRUDs continuam como regressão.
- [`rapidfuzz` como nova dependência] → biblioteca leve, sem dependências nativas pesadas. Alternativa sem dependência: `difflib.SequenceMatcher`, mais lento. Se for preferível não adicionar a dependência, a troca fica isolada na função de verificação.
- [Arquivo da sessão órfão quando o Source é descartado] → o arquivo é mantido como registro da sessão. A limpeza fica fora do escopo.
- [Concorrência entre revisores] → `FOR UPDATE` no item. O segundo revisor recebe 409.

## Migration Plan

1. Migração Alembic criando as duas tabelas, com índices em `(status)` e `(created_at)` da sessão e em `(session_id, status)` e `(parent_item_id)` dos itens.
2. Deploy aditivo: nenhuma rota existente muda.
3. Rollback: `downgrade` remove as tabelas. Entidades já aplicadas na árvore permanecem, pois são registros normais com auditoria.
