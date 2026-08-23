# Quickstart — Validação: AI Engine v2 Streaming

**Feature**: `001-ai-engine-v2-streaming`
**Data**: 2026-08-22
**Refs**: [spec.md](./spec.md) | [contracts/websocket-events.md](./contracts/websocket-events.md)

---

## Pré-requisitos

```bash
# 1. Serviços de infraestrutura rodando
docker compose up -d postgres redis

# 2. Variáveis de ambiente
# .env deve conter:
# AI_PARALLELISM=5
# TRACING_ENABLED=true
# TRACE_OUTPUT_PATH=/tmp/lumina_traces.jsonl

# 3. Dependências instaladas
poetry install

# 4. Migrações aplicadas (nenhuma nova migration nesta feature)
poetry run alembic upgrade head

# 5. Servidor rodando
poetry run task run
```

---

## Cenário 1: Streaming de Tokens no Chat (US-2 / P1)

**Objetivo**: Verificar que tokens chegam progressivamente via WebSocket.

```bash
# Conectar ao WebSocket do chat (substituir doc_id real)
wscat -c "ws://localhost:8000/doc/message/{doc_id}/ws" \
      --header "Cookie: access_token=<token>"

# Enviar mensagem
> @ai Qual é a metodologia usada no documento?

# Saída esperada (em sequência, antes da resposta completa):
< {"event":"chat.ai.token","message":"A","payload":{"doc_id":"..."}}
< {"event":"chat.ai.token","message":" metodologia","payload":{...}}
< {"event":"chat.ai.token","message":" utilizada","payload":{...}}
... (N tokens)
< {"event":"chat.ai.message","message":"{\"id\":\"...\",\"content\":\"A metodologia utilizada...\",\"references\":[...]}","payload":{}}
```

**Critério de aceite**: Pelo menos 2 eventos `chat.ai.token` chegam antes de
`chat.ai.message`. O conteúdo concatenado dos tokens é igual ao `content` da
mensagem final.

---

## Cenário 2: Retrocompatibilidade do Endpoint HTTP (FR-002)

**Objetivo**: Garantir que o endpoint HTTP não foi quebrado.

```bash
curl -X POST "http://localhost:8000/doc/{doc_id}/message/ai" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=<token>" \
  -d '{"content": "Qual é a conclusão?", "mentions": [], "quoted_message": null}'
```

**Critério de aceite**: Resposta `201 Created` com `DocumentMessagePublic` completo
(campos `id`, `content`, `references`, `mentions`, `document_id`, `release_id`,
`created_at`). Sem mudança de contrato.

---

## Cenário 3: Progresso do Pipeline de Release (US-1 / P1)

**Objetivo**: Verificar que eventos de progresso chegam durante a análise.

```bash
# Em terminal 1: conectar ao WebSocket de broadcast
wscat -c "ws://localhost:8000/ws/{user_id}"

# Em terminal 2: submeter documento para análise
curl -X POST "http://localhost:8000/doc/{doc_id}/release" \
  -H "Cookie: access_token=<token>" \
  -F "file=@documento.pdf" \
  -F "bump=patch"
```

**Saída esperada no terminal 1 (em sequência)**:
```json
{"event":"doc.release.update","message":"creating_vectors","payload":{...},"progress":10}
{"event":"doc.release.update","message":"evaluating","payload":{...},"progress":25}
{"event":"doc.release.update","message":"evaluating_3_of_10","payload":{...},"progress":41}
{"event":"doc.release.update","message":"evaluating_7_of_10","payload":{...},"progress":66}
{"event":"doc.release.update","message":"generating_description","payload":{...},"progress":90}
{"event":"doc.release.update","message":"complete","payload":{...},"progress":100}
```

**Critério de aceite**:
- Pelo menos 3 eventos com `progress` distintos antes de `complete`.
- Nenhum evento contém palavras como "LangChain", "OpenAI", "Redis", "PGVector".
- O evento final tem `"message": "complete"` e `"progress": 100`.

---

## Cenário 4: Paralelização (US-3 / P2)

**Objetivo**: Medir redução de tempo com paralelização ativa.

```bash
# Com AI_PARALLELISM=1 (sequencial forçado):
time curl -X POST "http://localhost:8000/doc/{doc_id_grande}/release" ...

# Com AI_PARALLELISM=5 (padrão):
time curl -X POST "http://localhost:8000/doc/{doc_id_grande}/release" ...
```

**Critério de aceite**: Com `AI_PARALLELISM=5`, o tempo total é ≥ 30% menor que
com `AI_PARALLELISM=1`, para documentos com ≥ 10 critérios de avaliação.

---

## Cenário 5: Tracing Opt-in (US-4 / P2)

**Objetivo**: Verificar que traces são gerados corretamente e sem PII.

```bash
# Executar análise com tracing habilitado
TRACING_ENABLED=true poetry run task run

# Após análise, verificar o arquivo de traces
cat /tmp/lumina_traces.jsonl | python3 -m json.tool | head -50
```

**Critério de aceite**:
- Cada linha é JSON válido com campos: `stage`, `started_at`, `finished_at`,
  `duration_ms`, `input_hash`, `result_summary`.
- Nenhuma linha contém conteúdo de documento, prompts ou respostas brutas.
- `input_hash` começa com `"sha256:"`.

```bash
# Verificar ausência de PII em traces
grep -i "CPF\|email\|senha\|password" /tmp/lumina_traces.jsonl
# Resultado esperado: sem output (nenhuma linha com PII)
```

---

## Suíte de Testes Automatizados

```bash
# Rodar todos os testes desta feature (sem consumo de tokens)
poetry run task test -k "streaming or progress or parallel or tracing"

# Rodar testes com LLM real (apenas quando necessário — consome tokens)
poetry run task test-ai -k "streaming"

# Verificar cobertura dos novos módulos
poetry run task cov
# Verificar coverage de:
# - lumina/services/ai_service.py
# - lumina/services/release_orchestrator.py
# - lumina/schemas/common.py (campo progress)
```

---

## Rollback (se necessário)

Esta feature é aditiva — campos opcionais e novos eventos. Para reverter:
1. Remover o campo `progress` do `WSMessage` (opcional — clientes ignoram `None`).
2. Reverter `messages.py` para usar `ai_service.create_ai_response` síncrono.
3. Reverter `release_orchestrator.py` para `apply_tree` sequencial.
4. Nenhuma migration de banco precisa ser revertida.
