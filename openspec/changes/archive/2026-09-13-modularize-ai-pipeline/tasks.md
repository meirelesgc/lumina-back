## 1. Criação dos Módulos em Stages (lumina/services/ai/stages/)

- [x] 1.1 Criar `lumina/services/ai/stages/extraction.py` com `CoordinateChunker`, loaders (PyMuPDF, Docx, Txt) e sanitização de `\x00` e espaços, validando com testes de extração.
- [x] 1.2 Criar `lumina/services/ai/stages/sections.py` com detecção de macro-seções por LLM, mapeamento NFKD e carimbo em chunks, garantindo retorno consistente `(sections, first_window)`.
- [x] 1.3 Criar `lumina/services/ai/stages/anonymization.py` integrando `PresidioAnonymizer` e metadados de reversão de PII.
- [x] 1.4 Criar `lumina/services/ai/stages/indexing.py` para gravação assíncrona de embeddings no PGVector (`vstore.aadd_documents`).
- [x] 1.5 Criar `lumina/services/ai/stages/retrieval.py` com busca ponderada por seção e expansão contextual de margem (`MARGIN_SIZE=2`).
- [x] 1.6 Criar `lumina/services/ai/stages/evaluation.py` com chain LangChain, barema de 0 a 10 e execução em lote via `chain.abatch`.
- [x] 1.7 Criar `lumina/services/ai/stages/citations.py` com resolução de coordenadas físicas (`rects`), páginas e detecção de citações alucinadas.
- [x] 1.8 Criar `lumina/services/ai/stages/synthesis.py` com prompt executivo da persona OiacIA e particionamento de texto (`greeting`, `fulfilled_points`, etc.).

## 2. Implementação dos Orquestradores (lumina/services/ai/)

- [x] 2.1 Implementar `lumina/services/ai/pipeline.py` orquestrando os 8 estágios do processamento de release com telemetria via `RunLogger` e atualizações de WebSocket via Redis.
- [x] 2.2 Implementar `lumina/services/ai/chat.py` orquestrando o Chat RAG com coordenadas visuais (`POST /doc/{id}/message/ai`) e o assistente de contexto longo (`POST /chat`).

## 3. Extinção da Pasta workers/ e Consolidação de Notificações

- [x] 3.1 Mover a função `send_message` (WhatsApp via Evolution API) para `lumina/services/notification_service.py` e atualizar o import em `lumina/services/kanban_service.py`.
- [x] 3.2 Atualizar o router `lumina/routers/docs/releases.py` para importar `release_pipeline` diretamente de `lumina.services.ai.pipeline`.
- [x] 3.3 Deletar a pasta `lumina/workers/` (`docs/releases.py` e `utils.py`) e verificar que nenhuma referência residual a `lumina.workers` permanece no repositório.

## 4. Eliminação de Fachadas e Validação da Suíte de Testes

- [x] 4.1 Deletar completamente os arquivos de fachada (`vector_service.py`, `release_logic_service.py`, `release_orchestrator.py` e `ai_service.py`) e apontar callers diretamente para `lumina/services/ai/`.
- [x] 4.2 Atualizar testes para importar diretamente dos módulos de IA (`test_ai_ingestion.py`, `test_ai_stages.py`, `test_ai_chat.py`, `test_releases_integration.py` e `test_section_splitter.py`).
- [x] 4.3 Executar a suíte completa com `poetry run task test` e verificar conformidade de estilo com `poetry run ruff check lumina tests`.
