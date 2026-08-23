# Implementation Plan: AI Engine v2 — Streaming, Progress & Observability

**Branch**: `001-ai-engine-v2-streaming` | **Date**: 2026-08-22
**Spec**: [spec.md](./spec.md)

---

## Summary

Evolução do motor de IA para entregar streaming de tokens no chat via WebSocket,
visibilidade granular de progresso no pipeline de análise de documentos,
paralelização controlada de avaliações de critérios, e tracing opt-in para
observabilidade e evolução incremental — tudo sem quebrar contratos existentes.

A abordagem é **aditiva**: novos eventos WebSocket, campo opcional em `WSMessage`,
e substituição de execução sequencial por paralela com semáforo. O endpoint HTTP
`/message/ai` e o evento `doc.release.update` final permanecem bit-a-bit
compatíveis com a v1.

---

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**:
- FastAPI (WebSocket nativo, BackgroundTasks)
- LangChain Core — `.astream()` nativo para streaming de tokens
- Redis + WebSocketManager (infra de broadcast já existente)
- asyncio — Semaphore para paralelismo controlado
- Pydantic v2 — schema `WSMessage` com campo opcional aditivo

**Storage**: PostgreSQL (SQLAlchemy 2.0 async) — sem novas tabelas.
Traces: JSON Lines em arquivo (`/tmp/lumina_traces.jsonl` — opt-in).

**Testing**:
- pytest + pytest-asyncio (existente)
- Testcontainers com Savepoints (existente — não alterar)
- `FakeListChatModel` para AI Integration Tests (sem tokens)
- `TestClient` com `websocket_connect` para testes de WebSocket
- `dependency_overrides[get_model]` para injeção de fakes
- `@pytest.mark.ai` para testes com LLM real

**Target Platform**: Linux server (async FastAPI)

**Performance Goals**:
- Primeiro token de chat: < 2s após envio da mensagem
- Redução de ≥ 30% no tempo de análise de documentos com ≥ 10 critérios

**Constraints**:
- Retrocompatibilidade total: nenhum campo existente removido
- Nenhuma nova dependência externa de APM obrigatória
- `AI_PARALLELISM` padrão = 5 (respeita rate limits de provedores LLM)
- Traces não armazenam conteúdo bruto de documentos (Constituição — Princípio V)

**Scale/Scope**:
- Afeta 3 módulos principais: `ai_service.py`, `release_orchestrator.py`,
  `messages.py` (router)
- 4 User Stories priorizadas (P1 e P2)
- Sem migrations de banco

---

## Constitution Check

*GATE: pré-fase de design. Todos os gates aprovados.*

| Princípio Constitucional                 | Status  | Evidência                                           |
|------------------------------------------|:-------:|-----------------------------------------------------|
| I. Separação de camadas                  | ✅ PASS  | Streaming fica no service/router, não no modelo ORM |
| I. Tipagem estática + Pydantic           | ✅ PASS  | `WSMessage.progress`, `ChatStreamEvent` tipados     |
| I. Poetry + Ruff 79 chars                | ✅ PASS  | Nenhuma ferramenta global; limite de linha mantido  |
| I. Git branch isolada                    | ✅ PASS  | Branch `001-ai-engine-v2-streaming` dedicada        |
| II. Foco em risco e comportamento        | ✅ PASS  | Matriz de risco em research.md; sem coverage cega   |
| II. Savepoints em testes                 | ✅ PASS  | Estrutura de testes existente não alterada          |
| II. Segregação @pytest.mark.ai           | ✅ PASS  | Fakes para CI; real LLM apenas em test-ai           |
| II. Refatoração segura                   | ✅ PASS  | Testes de caracterização antes de alterar orchestrator |
| III. Constantes HTTP                     | ✅ PASS  | Sem novos endpoints; existentes preservados         |
| III. Sem exposição de stack trace        | ✅ PASS  | Evento `failed` com mensagem amigável               |
| III. Retrocompat de contratos            | ✅ PASS  | Campos aditivos; nenhum removido (FR-016, FR-017)   |
| IV. Async nativo                         | ✅ PASS  | `.astream()`, `asyncio.gather`, `asyncio.Semaphore` |
| IV. Anti-N+1                             | ✅ PASS  | Paralelismo não adiciona queries; usa gather        |
| V. Anonimização antes de LLMs            | ✅ PASS  | Pipeline de Presidio inalterado; streaming pós-anon |
| V. Traces sem PII                        | ✅ PASS  | Apenas SHA-256 de inputs; sem conteúdo bruto        |
| Additional. Sem segredos hardcoded       | ✅ PASS  | `AI_PARALLELISM` e `TRACING_ENABLED` via env vars   |
| Dev Workflow. Spec-Kit                   | ✅ PASS  | specify → plan → tasks → implement seguido           |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-engine-v2-streaming/
├── plan.md              ← este arquivo
├── research.md          ← decisões técnicas e resoluções de unknowns
├── data-model.md        ← entidades novas/modificadas e variáveis de env
├── quickstart.md        ← cenários de validação manual e comandos de teste
├── contracts/
│   └── websocket-events.md  ← contratos WS e HTTP completos
├── checklists/
│   └── requirements.md ← checklist de qualidade da spec
└── tasks.md             ← gerado pelo /speckit-tasks (próximo passo)
```

### Source Code — Arquivos Afetados

```text
lumina/
├── schemas/
│   ├── common.py                   ← adicionar progress: Optional[int] em WSMessage
│   └── ai.py                       ← adicionar PipelineStage, ChatStreamEvent
│
├── services/
│   ├── ai_service.py               ← adicionar create_ai_response_stream()
│   └── release_orchestrator.py     ← refatorar apply_tree() para parallel;
│                                      expandir _ws_update() com progress
│
└── routers/docs/
    └── messages.py                 ← adicionar streaming no WS handler;
                                       HTTP endpoint intacto

tests/
├── unit/
│   └── services/
│       ├── test_ai_service_streaming.py   ← streaming logic, token concat
│       └── test_release_parallel.py       ← semáforo, gather, falhas isoladas
│
├── ai/
│   ├── fixtures/
│   │   └── ai_fixtures.py          ← adicionar fake_streaming_llm fixture
│   └── evaluation/
│       └── datasets/
│           └── streaming_chat_golden.json  ← golden dataset para eval
│
└── routers/  (ou api/)
    └── test_messages_streaming.py  ← AI Integration Tests via WS
```

**Structure Decision**: Single project — backend FastAPI. Frontend não é
alterado nesta feature; os novos eventos WebSocket são aditivos e ignorados
por clientes antigos que não os consomem.

---

## Complexity Tracking

Nenhuma violação constitucional identificada. Tabela omitida.

---

## Plano de Execução por Fase

### Fase A: Preparação e Caracterização (P0 — antes de tocar no código)

1. Escrever **Testes de Caracterização** para `release_orchestrator.py` e
   `ai_service.py` — capturar comportamento atual como linha de base antes
   de qualquer refatoração.
2. Confirmar que `poetry run task test` passa 100% antes de iniciar.

### Fase B: WSMessage + Progresso do Pipeline (US-1 / P1)

1. Adicionar `progress: Optional[int] = None` em `WSMessage`.
2. Refatorar `_ws_update` para aceitar `progress` e `label`.
3. Adicionar constante `PIPELINE_STAGES` com mapeamento etapa → label → progress.
4. Emitir eventos de progresso granulares ao longo do `process_release_pipeline`.
5. Testes unitários do novo `_ws_update` e da lógica de progresso.

### Fase C: Streaming do Chat (US-2 / P1)

1. Implementar `create_ai_response_stream()` em `ai_service.py` usando
   `.astream()` para tokens e `.invoke()` para citações ao final.
2. Modificar `process_user_message` no WebSocket handler para chamar a versão
   stream, emitindo `chat.ai.token` por fragmento.
3. Garantir que o endpoint HTTP `/message/ai` continua chamando
   `create_ai_response()` síncrona — sem alteração.
4. AI Integration Tests com `FakeListChatModel` e `TestClient.websocket_connect`.

### Fase D: Paralelização (US-3 / P2)

1. Substituir `chain.abatch(eval_args)` por `asyncio.gather` com
   `asyncio.Semaphore(AI_PARALLELISM)`.
2. Usar `return_exceptions=True` para isolar falhas individuais.
3. Integrar emissão de progresso `evaluating_N_of_M` com percentual dinâmico.
4. Testes de unidade para semáforo e comportamento de falha isolada.

### Fase E: Tracing Opt-in (US-4 / P2)

1. Implementar decorator `@trace_stage(name)` em módulo `lumina/utils/tracing.py`.
2. Verificar `TRACING_ENABLED` antes de qualquer I/O.
3. Hash SHA-256 do input; armazenar apenas métricas em JSON Lines.
4. Aplicar decorator nas etapas principais de `release_orchestrator.py`.
5. Testes unitários: tracing habilitado vs. desabilitado (zero overhead).

### Fase F: Golden Dataset e Qualidade (transversal)

1. Criar `tests/ai/evaluation/datasets/streaming_chat_golden.json` com casos:
   - Happy path: resposta com citações
   - Missing information: documento sem resposta relevante (`fulfilled=false`)
   - Prompt injection attempt
2. Marcar testes de avaliação com `@pytest.mark.ai`.

---

## Riscos e Mitigações

| Risco                                        | Probabilidade | Impacto | Mitigação                                  |
|----------------------------------------------|:-------------:|:-------:|--------------------------------------------|
| Streaming degrada qualidade de citações       | Média         | Alto    | 2 chamadas ao LLM: stream para texto, invoke para JSON estruturado |
| Rate limiting do provedor com paralelismo     | Alta          | Médio   | Semáforo padrão 5; backoff automático no `apply_tree` existente |
| WS cliente desconecta durante stream          | Média         | Baixo   | Try/except existente no handler; mensagem parcial não persistida |
| Traces crescem sem limite em disco            | Baixa         | Médio   | Rotação de arquivo configurável; tracing é opt-in |
| Testes de WebSocket flaky por assincronismo   | Média         | Médio   | Usar `anyio` backend no pytest-asyncio; fixtures determinísticas |
