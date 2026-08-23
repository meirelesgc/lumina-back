# Contratos: WebSocket Events — AI Engine v2

**Feature**: `001-ai-engine-v2-streaming`
**Date**: 2026-08-22

Todos os eventos WebSocket seguem o envelope `WSMessage`. Novos campos são aditivos.

---

## Eventos Existentes (preservados — retrocompat garantida)

### `user.connect` / `user.disconnect`
```json
{
  "event": "user.connect",
  "message": "User connected to channel - ws:doc:{doc_id}:chat",
  "payload": {}
}
```

### `chat.message` (mensagem de usuário broadcast)
```json
{
  "event": "chat.message",
  "message": "<texto enviado pelo usuário>",
  "payload": {}
}
```

### `chat.ai.message` (resposta completa da IA — existente, contrato preservado)
```json
{
  "event": "chat.ai.message",
  "message": "<JSON serializado de DocumentMessagePublic>",
  "payload": {}
}
```
O campo `message` contém o `DocumentMessagePublic` completo serializado, incluindo
`references`, `mentions`, `content`, etc. **Sem alteração.**

### `doc.release.update` (existente — progresso adicionado como campo opcional)
```json
{
  "event": "doc.release.update",
  "message": "evaluating",
  "payload": {
    "<...campos existentes de DocumentReleasePublic...>"
  },
  "progress": 25
}
```
- Campo `progress` é **novo e opcional**. Clientes que não o leem continuam funcionando.
- `message` continua sendo o identificador de etapa (ex: `"complete"`, `"evaluating"`).

---

## Eventos Novos (AI Engine v2)

### `chat.ai.token` (NOVO — streaming de tokens do chat)

Emitido repetidamente durante a geração da resposta. **Nunca persistido no banco.**

```json
{
  "event": "chat.ai.token",
  "message": "<fragmento de texto gerado pelo modelo>",
  "payload": {
    "doc_id": "<uuid>",
    "conversation_id": "<uuid>"
  }
}
```

**Comportamento**:
- Emitido N vezes (um por chunk do stream) antes do `chat.ai.message` final.
- `message` contém o token/fragmento bruto — pode ser uma ou várias palavras.
- O cliente deve concatenar os tokens para montar a pré-visualização progressiva.
- Quando o stream termina, `chat.ai.message` é emitido com a resposta completa e
  persistida.

**Sequência de eventos por requisição de chat**:
```
chat.message           →  mensagem do usuário
chat.ai.token (×N)     →  fragmentos progressivos da resposta
chat.ai.message        →  resposta final completa (persisted)
```

### `doc.release.update` com progresso granular (EVOLUÇÃO do evento existente)

Emitido em múltiplos momentos do pipeline com o campo `progress` preenchido:

| `message` value             | `progress` | Descrição amigável              |
|-----------------------------|:----------:|---------------------------------|
| `creating_vectors`          | `10`       | Lendo e indexando documento     |
| `evaluating`                | `25`       | Iniciando análise de critérios  |
| `evaluating_N_of_M`         | `25–85`    | Analisando critérios: N de M    |
| `generating_description`    | `90`       | Gerando resultado               |
| `complete`                  | `100`      | Análise concluída               |
| `failed`                    | `-1`       | Não foi possível concluir       |

**Exemplo com progresso parcial**:
```json
{
  "event": "doc.release.update",
  "message": "evaluating_7_of_15",
  "payload": { "<...DocumentReleasePublic...>" },
  "progress": 58
}
```

---

## Contratos HTTP (sem alteração)

### `POST /doc/{doc_id}/message/ai` — PRESERVADO INTEGRALMENTE

**Request** (sem alteração):
```json
{
  "content": "Qual é a conclusão do documento?",
  "mentions": [],
  "quoted_message": null
}
```

**Response** (sem alteração — `DocumentMessagePublic`):
```json
{
  "id": "<uuid>",
  "content": "A conclusão do documento indica...",
  "references": [
    {
      "chunk_id": "abc123",
      "page": 5,
      "text_snippet": "trecho do documento",
      "rects": [{"x1": 10, "y1": 20, "x2": 300, "y2": 50}]
    }
  ],
  "mentions": [{"id": "<uuid>", "type": "AI", "label": "OiacIA"}],
  "author": null,
  "document_id": "<uuid>",
  "release_id": "<uuid>",
  "created_at": "2026-08-22T23:00:00Z",
  "updated_at": null
}
```

---

## Contrato de Trace (opt-in, formato JSON Lines)

Cada linha do arquivo de trace é um objeto JSON independente:

```json
{
  "release_id": "<uuid>",
  "stage": "evaluating_branch",
  "started_at": "2026-08-22T23:00:00.000Z",
  "finished_at": "2026-08-22T23:00:04.230Z",
  "duration_ms": 4230,
  "input_hash": "sha256:<hash_do_input>",
  "result_summary": {
    "fulfilled": true,
    "score": 0.95,
    "criteria_id": "<uuid>"
  },
  "error": null
}
```
