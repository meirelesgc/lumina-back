## Context

Consulte `proposal.md` para a motivação do desacoplamento. O sistema Lumina processa documentos complexos de compras públicas utilizando RAG com coordenadas físicas, barema de avaliação de 0 a 10 e síntese executiva. Atualmente, os 4 arquivos principais de serviço misturam I/O, LLM, algoritmos de geometria e persistência.

A observabilidade do sistema (`RunLogger`) já opera conceitualmente sobre 7 a 8 macroetapas bem definidas (`extraction`, `sections`, `anonymization`, `indexing`, `retrieval`, `evaluation`, `citations`, `synthesis`).

## Goals / Non-Goals

**Goals:**
- Decompor as operações de IA em módulos de função única na pasta `lumina/services/ai/stages/`.
- Unificar a orquestração em `lumina/services/ai/pipeline.py` e o chat em `lumina/services/ai/chat.py`.
- Eliminar completamente a pasta `lumina/workers/`, migrando `release_pipeline` para o orquestrador e `send_message` para `lumina/services/notification_service.py`.
- Manter 100% de compatibilidade retroativa nos routers e fachadas legadas.
- Corrigir os testes unitários quebrados por divergência de assinatura na identificação de seções.

**Non-Goals:**
- Não alterar contratos de schemas públicos (Pydantic) de entrada ou saída das rotas HTTP/WebSocket.
- Não alterar a lógica de prompts de avaliação, parâmetros de temperatura ou provedores de IA.
- Não introduzir dependências pesadas de fila (como Celery ou RQ); o processamento assíncrono permanece gerenciado pelo `fastapi.BackgroundTasks`.

## Decisions

### Decisão 1: Pacote `lumina/services/ai/stages/`
- **Abordagem Escolhida**: Criar submódulos especializados dentro de `lumina/services/ai/stages/` (`extraction.py`, `sections.py`, `anonymization.py`, `indexing.py`, `retrieval.py`, `evaluation.py`, `citations.py`, `synthesis.py`).
- **Alternativa Considerada**: Criar uma pasta raiz `lumina/ai/`. Descartada para preservar o padrão arquitetural em camadas do projeto (Service-Repository) estabelecido em `docs/arquitetura-engenharia.md`.

### Decisão 2: Extinção de `lumina/workers/`
- **Abordagem Escolhida**: Deletar `lumina/workers/`. A função `release_pipeline` passa a ser `run_release_pipeline` em `lumina/services/ai/pipeline.py`. A função `send_message` passa para `lumina/services/notification_service.py`.
- **Alternativa Considerada**: Manter `workers/` como proxy. Descartada pois gerava falso entendimento de que havia workers externos e criava dependência circular com `notification_service`.

### Decisão 3: Eliminação Total de Arquivos de Fachada (*No Facades*)
- **Abordagem Escolhida**: Deletar completamente `vector_service.py`, `release_orchestrator.py`, `release_logic_service.py` e `ai_service.py`. Todos os routers, serviços e testes foram atualizados para importar diretamente de `lumina/services/ai/`.
- **Justificativa**: Evita duplicidade e scripts puramente de compatibilidade no projeto, reduzindo arquivos obsoletos e mantendo a arquitetura limpa e explícita.

## Risks / Trade-offs

- **[Risco] Mismatch de imports em testes existentes** → **Mitigação**: Atualização de todos os testes unitários e de integração para apontar para `lumina.services.ai.pipeline`, `lumina.services.ai.chat` e `lumina.services.ai.stages.*`.
- **[Risco] Regressão na telemetria do RunLogger** → **Mitigação**: Os ganchos `run_logger.start_stage` e `run_logger.complete_stage` são mantidos com os mesmos nomes de etapas (`extraction`, `sections`, `anonymization`, `evaluation`, `citations`, `synthesis`).

## Migration Plan

1. Criar a nova estrutura em `lumina/services/ai/stages/` com os módulos migrados.
2. Implementar `lumina/services/ai/pipeline.py` e `lumina/services/ai/chat.py`.
3. Migrar `send_message` para `notification_service.py` e atualizar consumidores (`kanban_service.py`, `routers/docs/releases.py`).
4. Deletar `lumina/workers/`.
5. Atualizar chamadas em routers e testes para importar diretamente de `lumina/services/ai/`.
6. Remover definitivamente os arquivos legados `vector_service.py`, `release_orchestrator.py`, `release_logic_service.py` e `ai_service.py`.
7. Executar suíte de testes completa e linting com Ruff.
