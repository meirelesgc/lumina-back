# Research: AI Engine v2 — Streaming, Progress & Observability

**Feature**: `001-ai-engine-v2-streaming`
**Date**: 2026-08-22
**Status**: Complete — all unknowns resolved

---

## 1. Streaming de Tokens no Chat (WebSocket)

### Decisão
Usar `model.astream(prompt)` do LangChain combinado com o `WebSocketManager`
já existente. O modelo atual (`Model`) suporta `.astream()` nativamente via
LangChain Core. Não é necessário adicionar novas dependências.

### Rationale
- O `WebSocketManager` em `lumina/core/cache.py` já publica via Redis PubSub
  (`broadcast_to_channel`). Podemos emitir eventos `chat.ai.token` por chunk
  enquanto itera o stream, e emitir `chat.ai.message` com a mensagem consolidada
  ao fim — reaproveitando 100% da infra existente.
- O `structured_output` (com `AnswerWithCitations`) é incompatível com streaming
  token-by-token puro, pois o JSON não é válido parcialmente. A estratégia é:
  fazer streaming apenas do campo `answer` (texto livre) e resolver as citações
  ao final com a resposta estruturada completa. Isso preserva o contrato atual.
- O endpoint HTTP `/message/ai` permanece intacto usando `model.invoke()`.

### Alternativa Considerada e Rejeitada
- **SSE (Server-Sent Events)** via um novo endpoint HTTP: Rejeitada porque o
  canal principal já é WebSocket; adicionar SSE duplicaria a complexidade do
  frontend sem benefício.
- **Streaming direto da resposta estruturada**: Incompatível com `with_structured_output`
  do LangChain — JSON parcial não pode ser parsed. Rejeitada.

### Estratégia de Streaming Híbrido para o Chat
```
1. model.astream(prompt)  →  emite tokens de `answer` via chat.ai.token
2. model.with_structured_output(AnswerWithCitations).invoke(prompt)
   →  resolve citations ao final
3. Persiste mensagem completa → emite chat.ai.message (contrato atual preservado)
```
Custo: 2 chamadas ao LLM por mensagem. Pode ser otimizado em v2.1 usando
`ainvoke` com streaming habilitado e parser parcial, mas é fora do escopo atual.

---

## 2. Progresso Visível no Pipeline de Release

### Decisão
Estender o `_ws_update` existente em `release_orchestrator.py` com um campo
`progress` (inteiro 0-100) e uma nova etapa `stage_label` amigável. O esquema
`WSMessage` recebe um campo `progress: Optional[int]` sem quebrar clientes
existentes (campo é opcional).

### Mapeamento de Etapas
| Etapa técnica interna        | Label amigável ao usuário       | Progress |
|------------------------------|---------------------------------|----------|
| `creating_vectors`           | "Lendo e indexando documento"   | 10       |
| `evaluating` (início)        | "Iniciando análise de critérios"| 25       |
| `evaluating` (por critério)  | "Analisando critérios: N de M"  | 25–85    |
| `generating_description`     | "Gerando resultado"             | 90       |
| `complete`                   | "Análise concluída"             | 100      |
| `failed`                     | "Não foi possível concluir"     | -1       |

### Retrocompatibilidade
- `WSMessage` ganha campo `progress: Optional[int] = None` — clientes que
  não leem este campo continuam funcionando normalmente.
- O evento `doc.release.update` continua sendo emitido com `complete` ao fim.

---

## 3. Paralelização com Semáforo Assíncrono

### Decisão
Substituir `chain.abatch(eval_args)` por `asyncio.gather` com um
`asyncio.Semaphore` configurável via variável de ambiente `AI_PARALLELISM` (padrão: 5).

### Rationale
- `abatch` do LangChain já faz alguma paralelização internamente, mas sem
  controle de concorrência. Com `asyncio.Semaphore` temos controle explícito
  de rate limiting sem dependências externas.
- Cada avaliação é independente (sem estado compartilhado entre branches), o
  que torna o paralelismo trivialmente seguro.
- Falhas individuais: cada task usa `asyncio.gather(..., return_exceptions=True)`
  para isolar falhas sem abortar o gather completo.

### Alternativa Considerada
- `asyncio.TaskGroup` (Python 3.11+): Mais moderno, mas cancela todas as tasks
  ao primeiro erro. Rejeitada pela spec (FR-010: falhas individuais não abortam
  o pipeline).
- Worker pool dedicado (Celery/RQ): Overhead desnecessário para o volume atual.

---

## 4. Tracing Opt-in

### Decisão
Implementar um decorator/context manager `@trace_stage(name)` que:
1. Verifica `TRACING_ENABLED=true` no ambiente antes de executar qualquer I/O.
2. Captura `started_at`, `finished_at`, `duration_ms`, `result_summary`.
3. Persiste em um log estruturado (JSON lines para arquivo ou Redis stream).
4. **NÃO** persiste conteúdo de documentos, prompts ou respostas — apenas hashes
   SHA-256 dos inputs e métricas numéricas de output.

### Rationale
- Sem dependência de ferramentas de APM externas (Datadog, Sentry, etc.) na
  fase inicial — JSON Lines é portável e suficiente para análise incremental.
- Opt-in via env var garante zero overhead em produção quando não necessário.
- A estrutura é compatível com ingestão futura em OpenTelemetry se necessário.

---

## 5. Estratégia de Testes (Metodologia fastapi-testing-methodology)

### Matriz de Risco da Feature

| Componente                          | Risco        | Camadas de Teste           |
|-------------------------------------|:------------:|----------------------------|
| Streaming chat WebSocket            | **Crítico**  | Unit + AI Integration + Security |
| Retrocompat endpoint HTTP /message/ai | **Crítico** | API Integration (regressão) |
| Progresso release via WSMessage     | **Alto**     | Unit + AI Integration      |
| Paralelismo + isolamento de falhas  | **Alto**     | Unit (asyncio.gather mock) |
| Tracing opt-in (sem PII)            | **Médio**    | Unit                       |
| Semáforo de concorrência            | **Médio**    | Unit                       |

### Abordagem por Categoria (AI Testing Standards)

**A. AI Integration Tests (determinísticos, sem tokens)**
- Usar `FakeListChatModel` com respostas simuladas de stream
  (`FakeStreamingListLLM` ou sequência de chunks).
- Validar que `chat.ai.token` events chegam antes de `chat.ai.message`.
- Validar que endpoint HTTP retorna resposta completa sem mudança de contrato.
- Usar `dependency_overrides[get_model]` para injetar o fake.

**B. AI Contract Tests**
- Validar que o parsing de `AnswerWithCitations` tolera respostas com campos
  ausentes ou tipos incorretos sem quebrar o pipeline.
- Garantir que o campo `references` continua populado mesmo em edge cases.

**C. AI Evaluation (Golden Datasets — @pytest.mark.ai_eval)**
- Avaliar se o streaming não degrada a qualidade das citações vs. modo síncrono.
- Dataset: `tests/ai/evaluation/datasets/streaming_chat_golden.json`.

### Fixtures de Mock para Streaming
```python
# FakeStreamingModel: retorna chunks token por token
from langchain_community.chat_models.fake import FakeListChatModel

@pytest.fixture
def fake_streaming_llm():
    """Simula resposta em streaming para o chat."""
    return FakeListChatModel(responses=[
        '{"answer": "Resposta simulada.", "citations": []}',
        "Descricao gerada.",  # para release description
    ])
```

### Isolamento de WebSocket em Testes
- Usar `TestClient` do FastAPI com `with client.websocket_connect(...)` para
  testar o fluxo completo de WebSocket sem broker real.
- Substituir `WebSocketManager` por um fake em memória nos testes de unidade.

### Regra de Segregação de IA (Constituição — Princípio II)
- Testes de streaming que chamam modelos reais: `@pytest.mark.ai`
- Testes com FakeListChatModel: sem marcação especial (rodam no CI).

---

## Conclusão: Todas as NEEDS CLARIFICATION resolvidas

| Interrogação original                          | Resolução                                    |
|------------------------------------------------|----------------------------------------------|
| LangChain suporta streaming sem deps extras?   | ✅ `.astream()` nativo, sem deps adicionais   |
| Como manter retrocompat do endpoint HTTP?      | ✅ Endpoint síncrono permanece inalterado     |
| Como paralelizar sem quebrar falhas isoladas?  | ✅ `asyncio.gather(return_exceptions=True)`   |
| Como testar streaming sem tokens reais?        | ✅ `FakeListChatModel` + WebSocket test client|
| Onde persistir traces?                         | ✅ JSON Lines opt-in, sem APM externo         |
| Como nomear etapas sem expor tecnologia?       | ✅ Mapeamento explícito em tabela acima       |
