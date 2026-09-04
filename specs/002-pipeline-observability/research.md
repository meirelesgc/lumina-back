# Research: Observabilidade de Pipeline e Diagnóstico de Execução

**Feature**: `002-pipeline-observability`
**Date**: 2026-09-05

## Decisões Técnicas e Resolução de Premissas

### 1. Extensibilidade Dinâmica de Etapas do Pipeline (Requisito Explícito do Usuário)

- **Contexto**: O usuário exigiu explicitamente: *"Garanta que se eu adicionar / começar a registrar mais etapas posteriormente, isso va aparecer na tela da nossa interface"*.
- **Decisão**: 
  1. No backend, o nome da etapa (`stage_name`) NÃO deve ser restringido por um `Enum` estático fechado. Ele é tratado como string livre (`str`) no contrato de eventos e schemas Pydantic.
  2. A camada de consolidação de execuções (`RunLogger` / `RunEventStore`) agrupa os eventos cronologicamente por `stage_name` de forma 100% dinâmica.
  3. A API REST retorna as etapas como uma lista ordenada `stages: list[ProcessingStageDetail]`. Cada etapa contém `name`, `status`, `duration_ms`, `item_count`, `items` (subitens como critérios avaliados) e `metadata`.
  4. O frontend em JavaScript vanilla NUNCA hardcodeia nomes de etapas (ex: não faz `if (stage === 'extraction')`). Em vez disso, a interface itera dinamicamente sobre o array `run.stages.forEach(stage => ...)` e gera os elementos visuais (cartões de etapa, acordeão, badges de status, contadores e tabelas de subitens) automaticamente para qualquer nova etapa que venha a ser registrada.
- **Alternativas Rejeitadas**:
  - *Enum fechado de etapas*: Rejeitado porque qualquer nova etapa adicionada no pipeline no futuro (ex: `table_extraction`, `citation_enrichment`, `compliance_analysis`) exigiria migração de schema, alteração de enums no backend e alteração de template no frontend.
  - *Colunas fixas no banco relacional*: Rejeitado porque quebra o princípio de extensibilidade e obrigaria migrações DDL a cada nova fase.

---

### 2. Compatibilidade e Identidade 1:1 entre `run_id` e `release_id`

- **Contexto**: O usuário apontou: *"Quero compatibilidade do run_id com o id da release, é mais facil pra mim encontrar assim"*.
- **Decisão**:
  1. No fluxo de execução de documentos acionado por `POST /doc/{doc_id}/release` e orquestrado por `release_pipeline(...)` em `lumina/workers/docs/releases.py`, o `run_id` adotará exatamente o valor do `db_release.id` (`run_id = release_id`).
  2. O arquivo de logs estruturado daquela execução será nomeado e armazenado diretamente como `{release_id}.jsonl` no diretório de execuções (`lumina/storage/pipeline_runs/{release_id}.jsonl`).
  3. O endpoint `GET /processing-runs/{id}` aceita diretamente o `release_id` como identificador, permitindo que administradores copiem o ID da release do painel ou banco e localizem imediatamente todos os eventos e tempos daquela execução.
- **Alternativas Rejeitadas**:
  - *Gerar um UUID randômico avulso para `run_id` e manter tabela de mapeamento `run_id <-> release_id`*: Rejeitado por adicionar complexidade desnecessária, exigir joins ou buscas secundárias e dificultar a localização pelo operador.

---

### 3. Estratégia de Persistência: Logs Estruturados Append-Only (JSONL) vs. Tabelas Relacionais

- **Contexto**: O usuário manifestou incômodo com a criação de tabelas relacionais pesadas para registrar logs de pipeline, preferindo logs estruturados no formato JSONL ou similar.
- **Decisão**:
  1. Adotar persistência estruturada *append-only* no formato **JSON Lines (JSONL)** sob o diretório gerenciado de armazenamento `lumina/storage/pipeline_runs/`.
  2. Cada execução gera um arquivo dedicado `{run_id}.jsonl` (onde `run_id == release_id`).
  3. Cada linha do arquivo é um objeto JSON atômico e imutável representando uma transição de estado (`run_started`, `stage_started`, `criterion_evaluated`, `stage_completed`, `run_completed`, etc.).
  4. Para listagem paginada e rápida de execuções recentes sem necessidade de varrer todos os arquivos completos, manter um arquivo de índice append-only leve `lumina/storage/pipeline_runs/index.jsonl` (com campos essenciais: `run_id`, `document_id`, `status`, `started_at`, `finished_at`, `duration_ms`), atualizado nos eventos de início e conclusão.
  5. Toda a lógica de leitura e escrita é isolada na interface `PipelineRunStorage` / `JsonlRunEventStore`, permitindo que futuramente o mecanismo seja substituído ou estendido para OpenTelemetry ou banco de dados sem alterar uma única linha do pipeline.
- **Alternativas Rejeitadas**:
  - *Tabelas relacionais `processing_runs` e `processing_events` com migrações Alembic*: Rejeitada em respeito à preferência expressa do usuário e para evitar sobrecarga de I/O relacional e lock de tabelas durante batch concorrente.
  - *Bancos NoSQL ou ferramentas pesadas externas (Elasticsearch/Loki/Grafana)*: Rejeitada para manter o Lumina autocontido, leve e simples de implantar.

---

### 4. Interface Minimalista e Visualização Direta (Princípio VII da Constituição)

- **Contexto**: O usuário orientou: *"Sobre a interface, vamos manter o padrão de ser algo mais simples"*.
- **Decisão**:
  1. A página HTML será implementada em `lumina/static/demos/pipeline_observability/index.html`, servida nativamente pelo FastAPI em `/demos/pipeline-observability/`.
  2. Estilo semântico e enxuto (dark theme padrão do Lumina Demos Hub), com zero build step (CSS vanilla puro e JavaScript vanilla moderno com `fetch` e `async/await`).
  3. Estrutura da interface:
     - **Barra de Controle Superior**: Seletor de token/persona de teste (Admin), campo de busca rápida por `Release ID` ou `Document ID`, e botão de recarregar.
     - **Painel de Lista**: Tabela enxuta contendo as últimas execuções: `Release ID`, `Status` (badge visual: Verde para SUCCESS, Vermelho para FAILED, Azul para IN_PROGRESS), `Duração Total` (ex: `1m42s`) e `Data/Hora`.
     - **Painel de Detalhes da Execução**: Card expansível com metadados do processamento e a cascata dinâmica de etapas.
     - **Renderizador Dinâmico de Etapas**: Para cada etapa do array `stages`, exibe o nome legível, status e tempo (ex: `✓ Extração 4.2s`, `✓ Avaliação 61.2s`).
     - **Acordeão de Subitens / Critérios**: Se a etapa contiver itens (como a avaliação paralela), o usuário pode clicar para abrir a lista simples de critérios avaliados com nota, quantidade de citações e tempo individual.
  4. Sanitização contra XSS: Função utilitária vanilla `escapeHtml(str)` para prevenir renderização arbitrária de scripts presentes em retornos de LLM ou mensagens de erro.
- **Alternativas Rejeitadas**:
  - *Gráficos de barras em Canvas / bibliotecas Chart.js*: Rejeitados nesta fase para cumprir a diretriz de simplicidade estrita e manter o carregamento instantâneo.
  - *Frameworks SPA (React/Vue)*: Rejeitados por violar o Princípio VII (Zero Build Step).

---

### 5. Segurança, RBAC e Salvaguarda LGPD

- **Contexto**: Ferramenta interna restrita a administradores. Proteção absoluta contra vazamento de dados pessoais em logs.
- **Decisão**:
  1. Os endpoints `/processing-runs` exigem injeção de `AdminUser` (`current_user.access_level == AccessType.ADMIN`). Usuários comuns ou orientadores recebem `403 Forbidden`. Requisições não autenticadas recebem `401 Unauthorized`.
  2. A função de logging de eventos (`RunLogger`) possui filtro de higienização de payload: rejeita ou omite campos marcados como sensíveis e nunca grava o texto integral do documento não-anonimizado.
  3. Modos de detalhamento controlados por configuração em `lumina/core/settings.py`:
     - `DEBUG_PIPELINE_RUNS: bool = False` (controla se artefatos de depuração e prompts detalhados de LLM são armazenados).
     - Em produção (`False`), apenas métricas, tempos, status e identificadores de critérios são persistidos.

---

### 6. Mapeamento Aprofundado das 7 Macroetapas e Estrutura de Variáveis em `data: {}`

- **Contexto**: A esteira de IA é não-determinística em pontos críticos (seções, retriever, inferência da LLM e síntese). É necessário capturar entradas, estado interno e saídas estruturadas para cada uma das 7 fases.
- **Decisão**:
  1. *Macroetapas 1 a 3 (Ingestão)*: Instrumentadas em `vector_service.py` no upload do documento, gravando métricas de páginas, chunks, tipologia do extrator (`.pdf`, `.docx`, `.txt`), sanitização de `\x00`, janelas de 3.000 chars, instâncias `SectionInfo`, taxa de sucesso de normalização e quantitativos de entidades substituídas pelo Presidio (excluindo os dados pessoais originais).
  2. *Consolidação no Release (`run_id == release_id`)*: Ao acionar a release, o orquestrador carrega e anexa os eventos de ingestão do documento ao arquivo `{release_id}.jsonl`, unificando a linha do tempo.
  3. *Macroetapas 4 a 7 (Avaliação e Síntese)*: Instrumentadas em `release_orchestrator.py` e `release_logic_service.py`, capturando query triplicada, chunks iniciais (k=3), chunks expandidos (`MARGIN_SIZE=2`), prompt integral, raw output, atributos Pydantic de feedback, citações alucinadas e divisão executiva do parecer OiacIA.
- **Alternativas Rejeitadas**:
  - *Armazenar dados em variáveis globais voláteis em memória*: Rejeitado por não sobreviver a reinicializações e não permitir auditoria histórica.

---

### 7. Política de Retenção e Rotação Automática de Logs (30 execuções ou 7 dias)

- **Contexto**: O acúmulo de arquivos `.jsonl` ricos pode degradar a performance de leitura do índice e consumir armazenamento local desnecessariamente.
- **Decisão**:
  - O serviço `RunLogger` executa uma rotina leve de rotação automática ao finalizar cada execução (`complete_run`/`fail_run`), mantendo no máximo as **30 execuções mais recentes** ou com até **7 dias de criação**.
  - Arquivos `.jsonl` que excederem esses limites são excluídos do disco e suas linhas são purgadas do `index.jsonl`.
- **Alternativas Rejeitadas**:
  - *Rotação por cron externo do Linux*: Rejeitado por introduzir acoplamento ao sistema operacional do host e dificultar execução em contêineres Docker ou ambientes de teste.

---

### 8. Padrão de Visualização em Sub-Abas [Entrada | Estado Interno | Saída] na Interface Demo

- **Contexto**: A riqueza de dados por etapa e por critério pode poluir a interface se empilhada em formato de texto contínuo.
- **Decisão**:
  - A interface adota acordeões com abas horizontais limpas (`[Entrada]`, `[Processamento / Estado]`, `[Saída]`) para cada etapa e critério.
  - Campos de texto extensos (prompts e saídas brutas) incluem botão com ícone de cópia rápida para a área de transferência (`navigator.clipboard.writeText`), facilitando o diagnóstico direto pelo engenheiro de IA.
