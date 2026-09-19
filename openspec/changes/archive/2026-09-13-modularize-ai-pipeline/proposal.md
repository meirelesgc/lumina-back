## Why

A camada de Inteligência Artificial do Lumina atualmente concentra lógicas complexas em poucos arquivos monolíticos (`vector_service.py` com 758 linhas, `release_logic_service.py` com 601 linhas, `release_orchestrator.py` com 303 linhas e `ai_service.py` com 252 linhas), além de possuir uma pasta `lumina/workers/` que não representa workers externos reais, mas apenas chamadas em background via FastAPI e mensageria WhatsApp.

Essa concentração dificulta a escrita de testes unitários isolados, gera duplicação de lógica entre o fluxo de release e o chat, e não espelha de forma limpa as macroetapas já definidas na telemetria (`RunLogger`). Modularizar a IA em estágios especializados (`stages/`), geridos por orquestradores de nível superior, e extinguir a pasta `workers/` trará desacoplamento, clareza arquitetural e facilidade de manutenção.

## What Changes

- **Modularização em Estágios (`lumina/services/ai/stages/`)**: Decomposição das responsabilidades de IA em submódulos autocontidos:
  - `extraction.py`: Leitura de arquivos (PDF/PyMuPDF, DOCX, TXT), sanitização e `CoordinateChunker`.
  - `sections.py`: Detecção de macro-seções por LLM (`ChunkSections`), mapeamento NFKD e carimbo em chunks.
  - `anonymization.py`: Anonimização LGPD determinística com Presidio.
  - `indexing.py`: Inserção de embeddings na base vetorial (PGVector).
  - `retrieval.py`: Recuperação ponderada por seção e expansão contextual de margem ($\pm 2$).
  - `evaluation.py`: Construção da chain LangChain com barema 0-10 e execução em lote (`abatch`).
  - `citations.py`: Resolução de bounding boxes (`rects`) para PDF e auditoria de citações alucinadas.
  - `synthesis.py`: Síntese executiva OiacIA e particionamento de blocos de texto.
- **Orquestradores de Nível Superior (`lumina/services/ai/`)**:
  - `pipeline.py`: Coordenação sequencial dos estágios, eventos de WebSocket, snapshots imutáveis (`Applied*`) e execução em background.
  - `chat.py`: Orquestração do Chat RAG com coordenadas (`/message/ai`) e assistente contínuo (`/chat`), reutilizando `retrieval.py` e `citations.py`.
- **Extinção da Pasta `lumina/workers/`**:
  - Remoção de `lumina/workers/docs/releases.py`, transferindo a função `release_pipeline` para `lumina.services.ai.pipeline`.
  - Remoção de `lumina/workers/utils.py`, consolidando o envio HTTP do WhatsApp (`send_message`) dentro de `lumina/services/notification_service.py`.
  - Atualização dos consumidores (`kanban_service.py` e `routers/docs/releases.py`).
- **Fachadas de Compatibilidade (`lumina/services/`)**: Manutenção temporária de re-exports em `vector_service.py`, `release_logic_service.py`, `release_orchestrator.py` e `ai_service.py` para garantir zero impacto em chamadas legadas.
- **Correção de Testes Unitários Quebrados**: Ajuste da assinatura de retorno em `sections.py` para tupla consistente `(sections, first_window)`, corrigindo os 3 testes unitários com falha no baseline.

## Capabilities

### New Capabilities
- `ai-pipeline`: Define o fluxo padronizado de processamento, anonimização, vetorização, avaliação de critérios por IA com coordenadas visuais para PDF e síntese executiva.

### Modified Capabilities
<!-- Nenhuma especificação anterior existia no repositório -->

## Impact

- **Código Afetado**: `lumina/services/ai/`, `lumina/services/notification_service.py`, `lumina/services/kanban_service.py`, `lumina/routers/docs/releases.py`, `lumina/workers/` (removido).
- **APIs / Contratos Externos**: Nenhum endpoint ou contrato de API HTTP/WebSocket é alterado.
- **Dependências**: Nenhuma nova dependência externa adicionada.
