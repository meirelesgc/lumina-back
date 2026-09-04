# Data Model: Observabilidade de Pipeline e Diagnóstico de Execução

**Feature**: `002-pipeline-observability`
**Date**: 2026-09-05

## 1. Visão Geral e Estratégia de Armazenamento

Para atender à exigência de evitar tabelas relacionais pesadas e garantir alta performance com baixo overhead (< 2%), a persistência de observabilidade utiliza arquivos estruturados no formato **JSON Lines (JSONL)** sob o diretório `lumina/storage/pipeline_runs/`.

Cada processamento do pipeline de release gera:
1. Um arquivo de eventos detalhado: `lumina/storage/pipeline_runs/{run_id}.jsonl` (onde `run_id == release_id`).
2. Uma entrada atualizada atomicamente no índice global de execuções: `lumina/storage/pipeline_runs/index.jsonl`.

---

## 2. Esquemas de Dados e Entidades (Pydantic / Domínio)

### 2.1 `ProcessingStatus` (Enum)

Representa os estados possíveis de uma execução global ou de uma etapa individual.

- `in_progress`: Execução ou etapa atualmente em processamento.
- `completed`: Execução ou etapa concluída com sucesso.
- `failed`: Execução ou etapa encerrada com erro/falha.

---

### 2.2 `ProcessingEventType` (Enum)

Tipos atômicos de eventos emitidos durante o ciclo de vida:

- `run_started`: Registro do início do processamento geral.
- `stage_started`: Início de uma etapa (ex: extração, anonimização, avaliação).
- `stage_progress`: Atualização de progresso intermediário de uma etapa.
- `criterion_evaluated`: Conclusão da avaliação de um critério específico em execuções concorrentes.
- `stage_completed`: Conclusão bem-sucedida de uma etapa.
- `stage_failed`: Falha em uma etapa.
- `run_completed`: Término com sucesso da cadeia de processamento.
- `run_failed`: Término da execução com erro.

---

### 2.3 `ProcessingEvent` (Registro Atômico de Linha em JSONL)

Estrutura de cada linha persistida no arquivo `{run_id}.jsonl`:

```json
{
  "id": "UUID",
  "run_id": "UUID (idêntico ao release_id)",
  "event": "run_started | stage_started | stage_completed | stage_failed | criterion_evaluated | run_completed | run_failed",
  "stage": "str (opcional, nome dinâmico da etapa)",
  "status": "in_progress | completed | failed",
  "timestamp": "ISO-8601 UTC (ex: 2026-09-05T01:30:00.123456Z)",
  "duration_ms": "int (opcional, preenchido em eventos de término/conclusão)",
  "item_count": "int (opcional, contagem de seções, chunks ou critérios processados)",
  "error": "str (opcional, mensagem de erro resumida)",
  "data": {
    "key": "valores adicionais estruturados (ex: score, citações, contagem de tokens, modelo)"
  }
}
```

---

### 2.4 `ProcessingStageDetail` (Modelo Dinâmico de Etapa)

**Atenção aos Requisitos de Extensibilidade**: O atributo `name` é do tipo `str`, sem restrição a enums fechados. Quando novas etapas forem instrumentadas no código (ex: `table_parsing`, `summary_generation`), o consolidador agrupa os eventos daquela etapa automaticamente e o schema a expõe dinamicamente.

```python
class ProcessingStageDetail(BaseModel):
    name: str  # Nome dinâmico da etapa (ex: 'extraction', 'anonymization', 'evaluation', etc.)
    status: ProcessingStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    item_count: Optional[int] = None
    error_details: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)  # Subitens (como critérios avaliados)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

### 2.5 `CriterionEvaluationRecord` (Subitem da Etapa de Avaliação)

Detalhamento de cada critério avaliado na etapa de avaliação paralela:

```python
class CriterionEvaluationRecord(BaseModel):
    criterion_id: str
    title: str
    status: ProcessingStatus
    duration_ms: int
    score: Optional[float] = None
    citations_count: int = 0
    feedback: Optional[str] = None
    error_message: Optional[str] = None
```

---

### 2.6 `ProcessingRunSummary` (Listagem de Execuções)

Schema retornado na lista paginada (`GET /processing-runs`):

```python
class ProcessingRunSummary(BaseModel):
    id: UUID  # Idêntico ao release_id
    release_id: UUID
    document_id: UUID
    document_name: Optional[str] = None
    status: ProcessingStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    stages_count: int
    error_summary: Optional[str] = None
```

---

### 2.7 `ProcessingRunDetail` (Detalhe Completo da Execução)

Schema retornado na consulta detalhada (`GET /processing-runs/{run_id}`):

```python
class ProcessingRunDetail(BaseModel):
    id: UUID  # Idêntico ao release_id
    release_id: UUID
    document_id: UUID
    document_name: Optional[str] = None
    status: ProcessingStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_summary: Optional[str] = None
    stages: List[ProcessingStageDetail]  # Lista de etapas consolidadas dinamicamente
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

### 2.8 Estrutura do Campo `data` para as 7 Macroetapas do Pipeline (FR-014)

O campo `data: Dict[str, Any]` encapsula as variáveis de entrada, estado interno e saídas estruturadas para cada uma das 7 macroetapas:

```typescript
// 1. Extração e Chunking (stage: "extraction")
{
  "pages_count": number,
  "chunks_count": number,
  "avg_chunk_size": number,
  "extractor_type": "PyMuPDF" | "Docx2txtLoader" | "TextLoader",
  "sanitization_ops_count": { "null_bytes_removed": number, "whitespace_normalized": number }
}

// 2. Identificação de Seções por LLM (stage: "sections")
{
  "input_window_text": string, // até 3.000 caracteres (em modo debug)
  "sections_detected": Array<{
    "section_name": string,
    "start_text": string,
    "end_text": string | null
  }>,
  "mapping_success_rate": number // 0.0 a 1.0 via _normalize_with_mapping
}

// 3. Anonimização LGPD Presidio (stage: "anonymization")
{
  "entities_detected_count": { "CPF": number, "CNPJ": number, "RG": number, "PHONE": number, "EMAIL": number },
  "replacement_keys": string[] // ex: ["<CPF_1>", "<CNPJ_1>"] - sem PII original
}

// 4. Recuperação Semântica Ponderada (stage: "retriever" ou dentro de evaluation)
{
  "branch_id": string,
  "query_executed": string, // Query com triplicação do nome da seção
  "initial_chunks": string[], // Lista dos 3 chunk_id da busca vetorial inicial
  "expanded_chunks": string[] // Lista final pós expansão MARGIN_SIZE=2 e deduplicação
}

// 5. Avaliação Estruturada de Ramo (stage: "evaluation", event: "criterion_evaluated")
{
  "branch_id": string,
  "retrieval": {
    "query_executed": string,
    "initial_chunks": string[],
    "expanded_chunks": string[]
  },
  "llm_interaction": {
    "model": string,
    "prompt_rendered": string, // Presente em modo DEBUG_PIPELINE_RUNS=true
    "raw_output": string,       // Saída bruta antes do parse (em debug)
    "tokens_prompt": number | null,
    "tokens_completion": number | null,
    "schema_validation_error": string | null // Preenchido se quebrar contrato Pydantic
  },
  "llm_output": {
    "fulfilled": boolean,
    "score": number,
    "feedback": string,
    "citations_provided": string[],
    "citations_hallucinated": string[]
  }
}

// 6. Resolução de Coordenadas (stage: "citations")
{
  "chunks_cited": string[],
  "hallucinated_citations_count": number,
  "resolved_boxes_count": number
}

// 7. Síntese Executiva (stage: "synthesis")
{
  "top_branches": {
    "highest_score_branch_ids": string[], // 2 critérios com maiores notas
    "lowest_score_branch_ids": string[]   // 2 critérios com menores notas
  },
  "partitioned_text": {
    "greeting": string,
    "fulfilled_points": string,
    "improvement_points": string,
    "final_guidance": string
  }
}
```

---

### 2.9 Política de Retenção e Rotação de Dados (FR-015)

O serviço `RunLogger` implementa verificação em disco a cada conclusão de release (`complete_run` ou `fail_run`):
- Limite de execuções: Mantém as **30 execuções mais recentes** (baseado em `started_at`).
- Limite de tempo: Remove logs gerados há mais de **7 dias**.
- Sincronização: Ao remover o arquivo `{run_id}.jsonl`, a linha correspondente no `index.jsonl` é descartada atomicamente.

---

## 3. Estrutura de Diretórios e Arquivos em Disco

```text
lumina/storage/
└── pipeline_runs/
    ├── index.jsonl                                 # Índice consolidado (máx 30 execuções recentes)
    ├── 60edf27e-7ca3-4592-a056-7ebcda1e5b5c.jsonl  # Log de eventos da release 1
    └── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jsonl  # Log de eventos da release 2
```

### Formato de Linha no `index.jsonl`

```json
{"id": "60edf27e-7ca3-4592-a056-7ebcda1e5b5c", "release_id": "60edf27e-7ca3-4592-a056-7ebcda1e5b5c", "document_id": "b2a0a4ce-d960-4d1f-9a62-56b77dc5af70", "document_name": "ENMC.AHP.pdf", "status": "completed", "started_at": "2026-09-05T00:07:54Z", "finished_at": "2026-09-05T00:17:13Z", "duration_ms": 558480, "stages_count": 7, "error_summary": null}
```

---

## 4. Diagrama de Transição de Estados da Execução

```text
       [Início: release_pipeline()]
                    │
                    ▼
          ┌───────────────────┐
          │    in_progress    │◄───── (Registra as 7 macroetapas e critérios)
          └─────────┬─────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
(Sucesso em todas      (Exceção não tratada
    as etapas)          em qualquer etapa)
         │                     │
         ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│    completed     │  │      failed      │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         └──────────┬──────────┘
                    ▼
          [Rotação de Logs: máx 30 runs / 7 dias]
```


