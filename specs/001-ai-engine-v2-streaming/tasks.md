# Tasks: AI Engine v2 — Streaming, Progress & Observability

**Feature**: `001-ai-engine-v2-streaming`
**Branch**: `001-ai-engine-v2-streaming`
**Date**: 2026-08-22
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1: Setup (Preparação e Caracterização)

**Purpose**: Garantir linha de base segura antes de qualquer alteração.
Sem testes de caracterização, não há como garantir retrocompatibilidade (Constituição — Princípio II, Refatoração Segura).

- [ ] T001 Verificar que `poetry run task test` passa 100% — registrar saída como baseline em `specs/001-ai-engine-v2-streaming/baseline_test_output.txt`
- [ ] T002 [P] Escrever teste de caracterização do comportamento atual de `process_release_pipeline` em `tests/unit/services/test_release_orchestrator_characterization.py` (captura: número e ordem de chamadas a `_ws_update`, valores de `message`)
- [ ] T003 [P] Escrever teste de caracterização do comportamento atual de `create_ai_response` em `tests/unit/services/test_ai_service_characterization.py` (captura: estrutura do dict retornado com chaves `answer` e `references`)
- [ ] T004 Confirmar que T002 e T003 passam com o código atual antes de prosseguir

---

## Phase 2: Foundational (Bloqueante para todas as User Stories)

**Purpose**: Modificações de schema e infraestrutura compartilhada que todas as fases dependem.

**⚠️ CRÍTICO**: Nenhuma User Story pode ser implementada antes desta fase estar completa.

- [ ] T005 Adicionar campo `progress: Optional[int] = None` em `WSMessage` em `lumina/schemas/common.py` (aditivo — retrocompat garantida por ser opcional)
- [ ] T006 Adicionar classes `PipelineStage` (dataclass com `key`, `label`, `progress`) e `ChatStreamEvent` (Pydantic com `event`, `token`, `conversation_id`, `doc_id`) em `lumina/schemas/ai.py`
- [ ] T007 Criar constante `PIPELINE_STAGES: dict[str, PipelineStage]` em `lumina/services/release_orchestrator.py` mapeando os 6 estágios (creating_vectors, evaluating, evaluating_N_of_M, generating_description, complete, failed) com labels amigáveis e progress base
- [ ] T008 [P] Escrever teste unitário para `WSMessage` validando que campo `progress=None` é retrocompatível (serializa igual à v1 quando `None`) em `tests/unit/services/test_ws_message_schema.py`
- [ ] T009 [P] Escrever teste unitário para `PipelineStage` e `ChatStreamEvent` validando campos obrigatórios e tipagem em `tests/unit/services/test_ai_schemas.py`

**Checkpoint**: WSMessage com `progress`, PipelineStage e ChatStreamEvent definidos e testados. Testes de caracterização T002/T003 ainda passam.

---

## Phase 3: User Story 1 — Progresso Visível no Pipeline de Release (P1) 🎯 MVP

**Goal**: O usuário vê em tempo real o progresso da análise do documento via WebSocket, com mensagens amigáveis e indicador percentual — sem silêncio durante o processo.

**Independent Test**: Submeter um documento e verificar que ao menos 3 eventos `doc.release.update` com `progress` distintos chegam antes do evento `complete`.

### Testes para User Story 1

- [ ] T010 [P] [US1] Escrever teste de unidade para `_ws_update` refatorado validando que emite `WSMessage` com `progress` e `message` (label amigável) corretos para cada estágio em `tests/unit/services/test_release_orchestrator.py`
- [ ] T011 [P] [US1] Escrever AI Integration Test para o pipeline completo (com `FakeListChatModel`) verificando sequência de eventos WS emitidos: `creating_vectors (10%)` → `evaluating (25%)` → `complete (100%)` em `tests/ai/test_release_pipeline_progress.py`
- [ ] T012 [US1] Escrever teste de regressão garantindo que o evento `doc.release.update` com `message="complete"` e `payload` contendo campos de `DocumentReleasePublic` ainda é emitido ao final em `tests/ai/test_release_pipeline_progress.py` (dentro do mesmo arquivo de T011)

### Implementação de User Story 1

- [ ] T013 [US1] Refatorar `_ws_update` em `lumina/services/release_orchestrator.py` para aceitar `progress: int` e `label: str`, emitindo `WSMessage` com o novo campo `progress` preenchido (mantendo assinatura retrocompat com valor padrão)
- [ ] T014 [US1] Substituir as 3 chamadas fixas a `_ws_update` em `process_release_pipeline` (`lumina/services/release_orchestrator.py`) por chamadas ao helper que usa `PIPELINE_STAGES` para resolver label e progress automaticamente
- [ ] T015 [US1] Adicionar emissão de evento `failed` com `progress=-1` e mensagem amigável no bloco `except` de `process_release_pipeline` em `lumina/services/release_orchestrator.py`
- [ ] T016 [US1] Validar que testes de caracterização T002 ainda passam após as mudanças; ajustar apenas se o comportamento de _ws_update mudou intencionalmente

**Checkpoint**: Pipeline de release emite eventos de progresso granulares. Evento `complete` ainda chega ao fim. Nenhum label expõe tecnologia interna. `poetry run task test` verde.

---

## Phase 4: User Story 2 — Streaming de Tokens no Chat (P1)

**Goal**: O usuário recebe fragmentos progressivos da resposta da IA via WebSocket durante a geração, antes da mensagem final consolidada. O endpoint HTTP permanece 100% compatível com a v1.

**Independent Test**: Enviar uma mensagem via WebSocket e verificar que eventos `chat.ai.token` chegam antes do evento `chat.ai.message` final. Chamar o endpoint HTTP e verificar que retorna `DocumentMessagePublic` completo sem alteração.

### Testes para User Story 2

- [ ] T017 [P] [US2] Escrever teste unitário para `create_ai_response_stream` (nova função) em `tests/unit/services/test_ai_service_streaming.py`, mockando `model.astream()` com `AsyncMock` que retorna chunks simulados, verificando que: (a) tokens são gerados na ordem correta; (b) answer consolidado = concatenação dos chunks; (c) citações resolvidas ao final
- [ ] T018 [P] [US2] Criar fixture `fake_streaming_llm` em `tests/ai/fixtures/ai_fixtures.py` usando `FakeListChatModel` com respostas simuladas para stream + citações
- [ ] T019 [US2] Escrever AI Integration Test do WebSocket do chat em `tests/ai/test_chat_streaming.py` usando `TestClient.websocket_connect`: verificar sequência `chat.ai.token` (×N) → `chat.ai.message`, e que o conteúdo final é igual ao concatenado dos tokens
- [ ] T020 [US2] Escrever teste de regressão do endpoint HTTP `POST /doc/{doc_id}/message/ai` em `tests/ai/test_chat_streaming.py` garantindo que retorna `201` com `DocumentMessagePublic` completo incluindo `references`, sem nenhum campo removido

### Implementação de User Story 2

- [ ] T021 [US2] Implementar função `create_ai_response_stream` em `lumina/services/ai_service.py` que usa `model.astream(prompt)` para gerar tokens do campo `answer` e `model.with_structured_output(AnswerWithCitations).invoke(prompt)` para resolver citações ao final — retornando um `AsyncGenerator` de tokens + dict final com `answer` e `references`
- [ ] T022 [US2] Modificar `process_user_message` em `lumina/routers/docs/messages.py` para chamar `create_ai_response_stream` quando `requires_ai_response(data)`, emitindo cada token como `chat.ai.token` via `broadcast_event`, e persistindo apenas a mensagem completa ao fim
- [ ] T023 [US2] Garantir que a função `create_ai_response` original em `lumina/services/ai_service.py` **não é modificada** — o endpoint HTTP `POST /doc/{doc_id}/message/ai` continua usando-a diretamente (zero alteração no handler HTTP)
- [ ] T024 [US2] Adicionar handler de erro no bloco de streaming em `lumina/routers/docs/messages.py`: se o stream falhar após emitir tokens parciais, emitir evento `chat.ai.error` com mensagem amigável; mensagem parcial NÃO deve ser persistida

**Checkpoint**: WebSocket emite tokens progressivos. Endpoint HTTP inalterado retorna resposta completa. Mensagem final persistida contém todos os campos da v1. `poetry run task test` verde.

---

## Phase 5: User Story 3 — Paralelização das Avaliações (P2)

**Goal**: Avaliações de critérios do documento rodam em paralelo com concorrência controlada, reduzindo o tempo total de análise em ≥ 30%, sem perda de integridade dos resultados.

**Independent Test**: Rodar pipeline com `AI_PARALLELISM=1` (sequencial) vs. `AI_PARALLELISM=5` (paralelo) em documento com ≥ 10 critérios e medir redução de tempo.

### Testes para User Story 3

- [ ] T025 [P] [US3] Escrever teste unitário para a nova `apply_tree_parallel` em `tests/unit/services/test_release_parallel.py`, mockando o `chain` para simular execuções com delays diferentes, verificando: (a) todas as avaliações são executadas; (b) falhas individuais não abortam o gather; (c) resultados de avaliações bem-sucedidas são persistidos
- [ ] T026 [P] [US3] Escrever teste unitário para o semáforo `asyncio.Semaphore(AI_PARALLELISM)` verificando que o número máximo de execuções concorrentes nunca excede o valor configurado em `tests/unit/services/test_release_parallel.py`
- [ ] T027 [US3] Escrever teste de integração verificando que progresso `evaluating_N_of_M` é emitido corretamente durante execução paralela em `tests/ai/test_release_pipeline_progress.py` (adicionar ao arquivo já criado em T011)

### Implementação de User Story 3

- [ ] T028 [US3] Ler variável de ambiente `AI_PARALLELISM` (padrão: `5`) em `lumina/core/settings.py`, adicionando campo `AI_PARALLELISM: int = 5` ao modelo `Settings`
- [ ] T029 [US3] Implementar função `apply_tree_parallel` em `lumina/services/release_logic_service.py` usando `asyncio.Semaphore` e `asyncio.gather(..., return_exceptions=True)`, substituindo o `chain.abatch(eval_args)` atual; erros individuais são logados e marcados com `error=True` no item sem re-raise
- [ ] T030 [US3] Integrar emissão de progresso `evaluating_N_of_M` dentro do callback de conclusão de cada avaliação individual em `apply_tree_parallel`, calculando percentual dinâmico (range 25%–85%) proporcional ao número de critérios concluídos
- [ ] T031 [US3] Substituir chamada a `apply_tree` por `apply_tree_parallel` em `process_release_pipeline` em `lumina/services/release_orchestrator.py`
- [ ] T032 [US3] Validar que `_save_eval_results` em `lumina/services/release_orchestrator.py` lida corretamente com itens que possuem `error=True` (pula persistência do `AppliedBranch` para itens com falha, sem quebrar a transação)

**Checkpoint**: Análise de documentos com múltiplos critérios é paralela. Falhas individuais são isoladas. Progresso granular `evaluating_N_of_M` é emitido. `poetry run task test` verde.

---

## Phase 6: User Story 4 — Tracing Opt-in (P2)

**Goal**: A equipe consegue monitorar inputs, outputs e métricas de cada etapa do pipeline em formato estruturado, sem afetar performance quando desabilitado.

**Independent Test**: Com `TRACING_ENABLED=true`, verificar que o arquivo JSON Lines é gerado com os campos corretos após uma análise. Com `TRACING_ENABLED=false` (padrão), verificar que nenhum arquivo é criado e a performance é idêntica ao comportamento atual.

### Testes para User Story 4

- [ ] T033 [P] [US4] Escrever teste unitário para o decorator `@trace_stage` em `tests/unit/utils/test_tracing.py` com dois cenários: (a) `TRACING_ENABLED=true`: verifica que JSON Lines é escrito com campos obrigatórios e que `input_hash` começa com `sha256:`; (b) `TRACING_ENABLED=false`: verifica que nenhuma escrita de arquivo ocorre (mock de `open`)
- [ ] T034 [P] [US4] Escrever teste unitário para verificar que `input_hash` nunca contém o conteúdo bruto do input (apenas hash), e que nenhum campo do trace contém palavras proibidas (lista: `CPF`, `email`, `senha`, `content`, `page_content`) em `tests/unit/utils/test_tracing.py`

### Implementação de User Story 4

- [ ] T035 [US4] Criar módulo `lumina/utils/tracing.py` com: (a) função `hash_input(data: str) -> str` que retorna `f"sha256:{hashlib.sha256(data.encode()).hexdigest()}"`; (b) classe `PipelineTrace` como dataclass; (c) função `write_trace(trace: PipelineTrace) -> None` que grava JSON Lines se `TRACING_ENABLED=true`, no-op caso contrário; (d) context manager `async_trace_stage(stage: str, release_id: UUID, input_data: str)` que mede duração e chama `write_trace`
- [ ] T036 [US4] Adicionar `TRACING_ENABLED: bool = False` e `TRACE_OUTPUT_PATH: str = '/tmp/lumina_traces.jsonl'` em `lumina/core/settings.py`
- [ ] T037 [US4] Aplicar `async_trace_stage` nas etapas principais de `lumina/services/release_orchestrator.py`: (a) ao redor de `create_vectors`; (b) ao redor de cada avaliação individual em `apply_tree_parallel`; (c) ao redor de `generate_description_prompt` + `model.invoke`
- [ ] T038 [US4] Criar diretório `tests/unit/utils/` com `__init__.py` se não existir em `tests/unit/utils/__init__.py`

**Checkpoint**: Traces gerados em JSON Lines quando habilitado. Zero overhead quando desabilitado. Nenhum PII ou conteúdo bruto nos traces. `poetry run task test` verde.

---

## Phase 7: Golden Dataset e AI Evaluation (Transversal)

**Purpose**: Criar assets de avaliação qualitativa para o streaming, garantindo que a nova abordagem não degrada a qualidade das citações em relação à v1.

- [ ] T039 [P] Criar arquivo `tests/ai/evaluation/datasets/streaming_chat_golden.json` com ao mínimo 3 casos: (a) happy_path: pergunta com resposta presente no documento + citações esperadas; (b) missing_information: pergunta cuja resposta não existe no documento (`expected_behavior: "fulfilled=false"`); (c) injection_attempt: tentativa de prompt injection que não deve alterar a resposta estruturada
- [ ] T040 [P] Escrever teste de avaliação `@pytest.mark.ai` em `tests/ai/evaluation/test_streaming_quality.py` que carrega o golden dataset e verifica que o streaming não degrada qualidade vs. modo síncrono: (a) answer concatenado dos tokens == answer do invoke; (b) citações resolvidas corretamente nos dois modos
- [ ] T041 Criar `tests/ai/evaluation/__init__.py` e `tests/ai/evaluation/datasets/` se não existirem

---

## Phase 8: Polish & Verificação Final

**Purpose**: Verificação de conformidade, linting e validação end-to-end do quickstart.

- [ ] T042 [P] Executar `poetry run ruff check --fix` e `poetry run ruff format` em todos os arquivos modificados por esta feature; corrigir eventuais violações de 79 chars ou aspas duplas
- [ ] T043 [P] Atualizar `lumina/core/settings.py` com as 3 novas variáveis de ambiente (`AI_PARALLELISM`, `TRACING_ENABLED`, `TRACE_OUTPUT_PATH`) e adicionar validação de tipo com Pydantic (se ainda não feito em T028/T036)
- [ ] T044 Executar todos os cenários do `quickstart.md` manualmente contra ambiente local e marcar cada cenário como `[PASS]` ou `[FAIL]` no arquivo `specs/001-ai-engine-v2-streaming/quickstart.md`
- [ ] T045 Executar `poetry run task test` e verificar que **todos** os testes passam, incluindo os de caracterização T002/T003 (prova de retrocompatibilidade)
- [ ] T046 Executar `poetry run task cov` e verificar cobertura de: `lumina/services/ai_service.py`, `lumina/services/release_orchestrator.py`, `lumina/utils/tracing.py` — gaps críticos devem ser documentados
- [ ] T047 Executar `speckit-analyze` para validar consistência entre spec, plan e tasks antes do merge

---

## Dependencies & Execution Order

### Dependências entre Fases

```
Phase 1 (Setup/Caracterização)
  └─► Phase 2 (Foundational — WSMessage, Schemas)
        ├─► Phase 3 (US1 — Progresso Release)     [pode iniciar após Phase 2]
        ├─► Phase 4 (US2 — Streaming Chat)         [pode iniciar após Phase 2]
        ├─► Phase 5 (US3 — Paralelização)          [pode iniciar após Phase 3]
        └─► Phase 6 (US4 — Tracing)                [pode iniciar após Phase 2]
              └─► Phase 7 (Golden Dataset)         [qualquer momento após Phase 4]
                    └─► Phase 8 (Polish)           [após todas as stories]
```

### Dependências entre Tarefas

- **T004** depende de T002, T003
- **T007** depende de T005, T006
- **T013, T014, T015** dependem de T007, T010, T011 (testes primeiro)
- **T016** depende de T013, T014, T015
- **T021** depende de T017, T018 (fixtures antes da impl)
- **T022** depende de T021 (stream service antes do router)
- **T023** é independente (garantia de não-mudança)
- **T029** depende de T028 (Settings antes da impl paralela)
- **T030, T031** dependem de T029
- **T032** depende de T031
- **T035** depende de T033, T034 (testes primeiro)
- **T037** depende de T035, T036
- **T044–T047** dependem de todas as phases anteriores

### Paralelismo por Story

```bash
# Phase 2 — paralelo:
T005 (WSMessage)  ||  T006 (Schemas AI)  →  T007 (PIPELINE_STAGES)
T008 (test WSMsg) ||  T009 (test Schemas)

# Phase 3 — paralelo na escrita de testes:
T010 (unit _ws_update)  ||  T011 (integration pipeline)  →  T013+ (impl)

# Phase 4 — paralelo na escrita de testes e fixtures:
T017 (unit stream)  ||  T018 (fixture)  →  T019, T020  →  T021+

# Phase 5 — paralelo:
T025 (unit parallel)  ||  T026 (unit semaphore)  →  T028  →  T029+

# Phase 6 — paralelo:
T033 (unit trace)  ||  T034 (unit PII)  →  T035  →  T036  →  T037
```

---

## Implementation Strategy

### MVP (User Story 1 + User Story 2 — foco máximo, entrega de P1)

1. ✅ Completar Phase 1 (Setup)
2. ✅ Completar Phase 2 (Foundational)
3. ✅ Completar Phase 3 (US1 — Progresso Release)
4. ✅ Completar Phase 4 (US2 — Streaming Chat)
5. **PARAR e VALIDAR**: `poetry run task test` verde + quickstart cenários 1, 2 e 3 passando
6. **DEMO/DEPLOY**: MVP reduz ansiedade do usuário nos dois canros-chefes

### Entrega Incremental

1. MVP (US1+US2) → deploy → feedback
2. US3 (Paralelização) → deploy → medir ganho de performance
3. US4 (Tracing) → deploy → começar avaliação incremental
4. Golden Dataset + AI Evaluation → fechar o ciclo de qualidade

### Estratégia com Desenvolvedor Solo

```
Semana 1: Phase 1 → Phase 2 → Phase 3 (US1 completo)
Semana 2: Phase 4 (US2 completo) → MVP validado
Semana 3: Phase 5 (US3) → Phase 6 (US4)
Semana 4: Phase 7 + Phase 8 + Polish
```

---

## Notes

- `[P]` = tarefa paralelizável (arquivos diferentes, sem dependência incompleta)
- `[US1/2/3/4]` = rastreabilidade com User Story da spec
- Testes de caracterização (T002, T003) são a rede de segurança da refatoração
- `create_ai_response` original **nunca deve ser modificada** — T023 é uma garantia explícita
- Commit atômico recomendado após cada Checkpoint de fase
- Nenhuma migration de banco é necessária nesta feature
