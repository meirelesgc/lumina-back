# Data Model: AI Engine v2 — Streaming, Progress & Observability

**Feature**: `001-ai-engine-v2-streaming`
**Date**: 2026-08-22

---

## Entidades Novas e Modificadas

### 1. `WSMessage` (modificada — schema existente em `lumina/schemas/common.py`)

Campo adicionado de forma aditiva (não-breaking):

```
WSMessage
├── event: str          (existente — sem alteração)
├── message: str        (existente — sem alteração)
├── payload: dict|None  (existente — sem alteração)
└── progress: int|None  (NOVO — opcional, 0-100, -1=erro, None=não aplicável)
```

**Regras de Validação**:
- `progress` aceita `None` (campos opcionais — retrocompat garantida).
- Quando `event == 'doc.release.update'`, `progress` DEVE estar presente.
- Quando `event == 'chat.ai.token'` ou `'chat.ai.message'`, `progress` é `None`.

**Estado de transição para `doc.release.update`**:
```
QUEUED → creating_vectors (10%) → evaluating_start (25%)
       → evaluating_N_of_M (25-85%) → generating_description (90%)
       → complete (100%) | failed (-1%)
```

---

### 2. `PipelineStage` (nova — internal, não persistida no DB)

Estrutura usada internamente pelo `release_orchestrator` para mapear etapas.
Não gera migration de banco.

```
PipelineStage
├── key: str            (identificador técnico interno, ex: 'creating_vectors')
├── label: str          (texto amigável, ex: 'Lendo e indexando documento')
└── progress: int       (percentual base da etapa, 0-100)
```

Implementada como `dataclass` ou `TypedDict` em `lumina/schemas/ai.py`.

---

### 3. `ChatStreamEvent` (nova — não persistida, apenas emitida via WS)

Evento WebSocket emitido durante o streaming do chat:

```
ChatStreamEvent
├── event: Literal['chat.ai.token']
├── token: str          (fragmento da resposta gerada pelo modelo)
├── conversation_id: str
└── doc_id: str
```

Serializado como JSON e emitido via `socket_manager.broadcast_to_channel`.
Não é salvo no banco — apenas transitório.

---

### 4. `PipelineTrace` (nova — persistência opt-in)

Registro de observabilidade de uma execução de etapa do pipeline.
**Somente criada quando `TRACING_ENABLED=true`.**

```
PipelineTrace
├── id: UUID                  (PK)
├── release_id: UUID          (FK → DocumentRelease, não constraint formal)
├── stage: str                (nome técnico da etapa)
├── started_at: datetime
├── finished_at: datetime
├── duration_ms: int
├── input_hash: str           (SHA-256 do input — NUNCA o conteúdo bruto)
├── result_summary: dict|None (ex: {"fulfilled_count": 7, "total": 10, "score_avg": 0.82})
└── error: str|None           (mensagem de erro se falhou)
```

**Armazenamento**: JSON Lines em arquivo de log rotativo (`/tmp/lumina_traces.jsonl`
ou path configurável via `TRACE_OUTPUT_PATH`). Não persiste no banco PostgreSQL
para não adicionar carga no fluxo principal.

**Privacidade**: `input_hash` é SHA-256 do conteúdo do input; o conteúdo bruto
nunca é armazenado. Isso atende ao FR-014 e ao Princípio V da Constituição.

---

## Entidades Sem Alteração (confirmado)

| Entidade                    | Status         | Motivo                                     |
|-----------------------------|----------------|--------------------------------------------|
| `DocumentMessage`           | ✅ Sem mudança  | Contrato de persistência mantido intacto   |
| `DocumentRelease`           | ✅ Sem mudança  | Sem novos campos no ORM                    |
| `DocumentReleasePublic`     | ✅ Sem mudança  | Schema de resposta preservado              |
| `DocumentMessagePublic`     | ✅ Sem mudança  | Resposta final do chat idêntica à v1       |
| `AnswerWithCitations`       | ✅ Sem mudança  | Estrutura interna de citações preservada   |

---

## Sem Migrations de Banco Necessárias

- `WSMessage` é um schema Pydantic (não ORM) — campo `progress` adicionado sem
  migration.
- `PipelineTrace` usa armazenamento em arquivo JSON Lines — sem alteração no
  `models.py`.
- Nenhuma migration Alembic é necessária para esta feature.

---

## Novas Variáveis de Ambiente

| Variável              | Tipo    | Padrão | Descrição                                    |
|-----------------------|---------|--------|----------------------------------------------|
| `AI_PARALLELISM`      | `int`   | `5`    | Máximo de avaliações paralelas no pipeline   |
| `TRACING_ENABLED`     | `bool`  | `false`| Habilita coleta de traces de pipeline        |
| `TRACE_OUTPUT_PATH`   | `str`   | `/tmp/lumina_traces.jsonl` | Caminho do arquivo de traces |
