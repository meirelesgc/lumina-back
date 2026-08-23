# Feature Specification: AI Engine v2 — Streaming, Progress & Observability

**Feature Branch**: `001-ai-engine-v2-streaming`

**Created**: 2026-08-22

**Status**: Draft

**Input**: User description: "Motor de IA v2 com streaming de resultados, visibilidade de etapas internas, paralelização de processamento e tracing para avaliação incremental, sem quebrar o que existe hoje."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Progresso visível durante análise de documento (Priority: P1)

Ao submeter um documento para análise via `/release`, o usuário hoje aguarda em
silêncio até a análise terminar. Com esta feature, o usuário passa a ver em tempo
real quais etapas estão ocorrendo (ex.: "Lendo documento", "Analisando critérios",
"Gerando resultado") sem que qualquer detalhe técnico ou de stack seja exposto.

**Why this priority**: É o principal driver de redução de ansiedade mencionado pelo
usuário. A análise pode demorar dezenas de segundos e o silêncio atual gera
abandono e percepção de falha.

**Independent Test**: Pode ser testado isoladamente submetendo um documento e
verificando que eventos de progresso chegam ao frontend antes da conclusão da
análise, enquanto o resultado final permanece idêntico ao comportamento atual.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado envia um documento para análise,
   **When** o pipeline de release é iniciado,
   **Then** o sistema emite ao menos 3 eventos de progresso distintos via
   WebSocket antes de emitir o evento `doc.release.update` com status `complete`,
   sem expor nomes de modelos, bibliotecas ou detalhes de infraestrutura nas
   mensagens.

2. **Given** o pipeline de análise está em execução,
   **When** o frontend está conectado ao WebSocket de broadcast,
   **Then** cada evento de progresso contém: nome amigável da etapa, indicador de
   progresso percentual (0–100) e timestamp, mas NÃO contém nomes de tecnologias
   internas (ex.: "LangChain", "OpenAI", "Presidio").

3. **Given** o pipeline falha em alguma etapa intermediária,
   **When** o erro é detectado,
   **Then** o sistema emite um evento de progresso com status de erro contendo
   mensagem amigável, e o estado do release no banco reflete `failed` sem expor
   stack trace ao frontend.

---

### User Story 2 — Respostas do chat chegam em stream (Priority: P1)

O chat é um dos produtos centrais da plataforma. Hoje a resposta da IA chega de
uma só vez após processamento completo, o que pode levar vários segundos sem
qualquer feedback. Com streaming, o usuário vê as palavras da resposta chegando
progressivamente, como em experiências modernas de chat com IA.

**Why this priority**: É o carro-chefe da plataforma. A percepção de velocidade e
responsividade impacta diretamente o engajamento e a satisfação.

**Independent Test**: Pode ser testado enviando uma mensagem via WebSocket do chat
e verificando que múltiplos eventos `chat.ai.token` chegam antes do evento final
`chat.ai.message`, entregando o mesmo conteúdo total de resposta.

**Acceptance Scenarios**:

1. **Given** um usuário envia uma mensagem que requer resposta da IA via WebSocket,
   **When** o modelo começa a gerar a resposta,
   **Then** tokens ou fragmentos da resposta são emitidos progressivamente via
   WebSocket (evento `chat.ai.token`) antes da mensagem final persistida ser emitida
   (evento `chat.ai.message`), mantendo o mesmo contrato de campos da mensagem
   final atual.

2. **Given** o cliente WebSocket está conectado ao canal de chat,
   **When** a resposta em stream é concluída,
   **Then** a mensagem final persistida no banco contém o texto completo consolidado
   e as referências (`references`), idêntica ao comportamento atual da v1.

3. **Given** o endpoint HTTP `/doc/{doc_id}/message/ai` é chamado diretamente
   (sem WebSocket),
   **When** a requisição é processada,
   **Then** a resposta continua sendo retornada de forma completa e síncrona,
   mantendo retrocompatibilidade total com clientes que não suportam streaming.

---

### User Story 3 — Paralelização da análise de critérios do documento (Priority: P2)

Hoje, a análise de cada branch/critério do documento é feita em batch sequencial
(via `chain.abatch`). Com paralelização controlada, múltiplos critérios podem ser
avaliados simultaneamente, reduzindo o tempo total de análise de um documento.

**Why this priority**: Melhoria de performance significativa que beneficia todos os
usuários, mas depende da infra de streaming estar estável (P1) para ser
aproveitada com visibilidade de progresso.

**Independent Test**: Pode ser testado verificando que o tempo de análise de um
documento com N critérios diminui em relação à versão sequencial, e que todos os
resultados são persistidos corretamente no banco.

**Acceptance Scenarios**:

1. **Given** um documento com 10 ou mais critérios de avaliação,
   **When** o pipeline de release é executado,
   **Then** o tempo total de análise é pelo menos 30% menor do que o tempo da
   execução sequencial pura, sem perda de qualidade ou integridade dos resultados
   persistidos.

2. **Given** avaliações paralelas estão em curso,
   **When** uma ou mais avaliações individuais falham,
   **Then** as demais continuam e os resultados válidos são persistidos; apenas as
   falhas individuais são registradas sem abortar o pipeline completo.

3. **Given** o pipeline paralelo está ativo,
   **When** os eventos de progresso são emitidos,
   **Then** o frontend recebe atualizações indicando quantos critérios foram
   concluídos do total (ex.: "Analisando critérios: 7 de 15"), sem granularidade
   técnica excessiva.

---

### User Story 4 — Tracing e observabilidade para avaliação incremental (Priority: P2)

A equipe precisa conseguir monitorar o output do modelo em diferentes pontos do
pipeline para avaliar a qualidade das respostas, identificar regressões e fazer
ajustes incrementais com evidências. Isso inclui capturar inputs, outputs e
métricas de cada etapa de forma estruturada e acessível.

**Why this priority**: Viabiliza a evolução incremental responsável do motor de IA.
Sem observabilidade, melhorias são feitas às cegas. Menos urgente que o streaming
por ser uma feature de suporte ao desenvolvimento.

**Independent Test**: Pode ser testado verificando que, após a execução de um
pipeline, os traces são persistidos ou emitidos em formato estruturado e
consultável, contendo os campos definidos (etapa, input resumido, output, duração,
score quando aplicável).

**Acceptance Scenarios**:

1. **Given** o tracing está habilitado via configuração de ambiente,
   **When** um pipeline de release é executado,
   **Then** cada etapa principal gera um registro de trace contendo: nome da etapa,
   timestamp de início e fim, duração em ms, score/resultado quando aplicável, e
   hash do input (sem o conteúdo completo por questão de PII/privacidade).

2. **Given** os traces estão sendo coletados,
   **When** a equipe consulta os registros de trace,
   **Then** é possível identificar quais etapas consomem mais tempo, quais
   critérios têm maior taxa de `fulfilled=false`, e comparar resultados entre
   versões do modelo sem reprocessar documentos.

3. **Given** o tracing está desabilitado (variável de ambiente não configurada),
   **When** o pipeline é executado,
   **Then** o comportamento é exatamente igual ao atual (sem overhead), garantindo
   que a funcionalidade seja opt-in.

---

### Edge Cases

- O que acontece quando o cliente WebSocket desconecta no meio do streaming do
  chat? A mensagem parcial não deve ser persistida — apenas mensagens completas.
- O que acontece quando o modelo demora mais de X segundos para iniciar o stream?
  O sistema deve emitir um evento de "aguardando resposta" após um timeout
  configurável, antes de considerar falha.
- O que acontece quando a paralelização excede o rate limit da API do provedor de
  LLM? O sistema deve aplicar backoff automático sem falhar o pipeline inteiro.
- Documentos com poucos critérios (< 3) se beneficiam de paralelização? O sistema
  deve executar de forma sequencial quando o overhead de paralelização supera o
  ganho, com threshold configurável.
- O tracing captura dados sensíveis? Os traces NUNCA devem persistir o conteúdo
  completo dos chunks ou respostas do modelo — apenas hashes e métricas agregadas.

---

## Requirements *(mandatory)*

### Functional Requirements

**Streaming do Chat (WebSocket)**

- **FR-001**: O sistema MUST emitir tokens/fragmentos da resposta da IA de forma
  progressiva via WebSocket (evento `chat.ai.token`) durante a geração da resposta,
  antes de emitir a mensagem final consolidada (evento `chat.ai.message`).
- **FR-002**: O endpoint HTTP `POST /doc/{doc_id}/message/ai` MUST continuar
  funcionando de forma síncrona e completa, sem alteração no contrato de resposta,
  para manter retrocompatibilidade com clientes existentes.
- **FR-003**: A mensagem final persistida no banco MUST conter o texto completo
  consolidado e o campo `references` intactos, idênticos ao comportamento atual da
  v1.
- **FR-004**: Mensagens parciais (streaming em curso) MUST NOT ser persistidas no
  banco; apenas a mensagem completa ao final do stream é salva.

**Progresso do Pipeline de Release**

- **FR-005**: O pipeline de release MUST emitir eventos de progresso via WebSocket
  ao longo de suas etapas, com nomenclatura amigável ao usuário e indicador de
  progresso (percentual ou contagem de critérios processados).
- **FR-006**: Os eventos de progresso MUST NOT expor nomes de tecnologias internas,
  bibliotecas ou detalhes de infraestrutura (proibido: "LangChain", "OpenAI",
  "Presidio", "Redis", "PGVector").
- **FR-007**: O sistema MUST emitir um evento de progresso de erro com mensagem
  amigável quando qualquer etapa do pipeline falhar, sem expor stack traces.
- **FR-008**: O evento `doc.release.update` com status `complete` MUST continuar
  sendo emitido ao final do pipeline, mantendo retrocompatibilidade com o frontend
  atual que já consome este evento.

**Paralelização**

- **FR-009**: O sistema MUST suportar execução paralela das avaliações de critérios
  (branches) do documento, com grau de concorrência configurável via variável de
  ambiente.
- **FR-010**: Falhas em avaliações individuais de critérios MUST NOT abortar o
  pipeline completo; critérios com falha MUST ser registrados com status de erro
  isolado.
- **FR-011**: O sistema MUST aplicar mecanismo de controle de taxa (rate limiting /
  backoff) para respeitar limites do provedor de LLM sob carga paralela.

**Tracing e Observabilidade**

- **FR-012**: O sistema MUST suportar tracing opt-in via variável de ambiente, sem
  qualquer overhead quando desabilitado.
- **FR-013**: Cada trace MUST conter: nome da etapa, timestamps (início/fim),
  duração em ms, e métricas de resultado (score, fulfilled) quando aplicável.
- **FR-014**: Os traces MUST NOT persistir conteúdo completo de documentos,
  prompts ou respostas do modelo; apenas hashes e métricas agregadas são
  permitidos, em conformidade com o Princípio V da Constituição (Data Sovereignty).
- **FR-015**: Os traces MUST ser emitidos em formato estruturado (JSON) compatível
  com ferramentas de análise e visualização sem integração proprietária obrigatória.

**Retrocompatibilidade**

- **FR-016**: Todos os campos existentes nos contratos de resposta dos endpoints
  afetados MUST ser preservados. Novos campos podem ser adicionados, mas nenhum
  campo existente pode ser removido ou ter seu tipo alterado.
- **FR-017**: O contrato atual do evento WebSocket `doc.release.update` (com campos
  `event`, `message`, `payload`) MUST ser preservado; novos campos de progresso
  podem ser adicionados ao payload.

### Key Entities

- **PipelineStage**: Representa uma etapa nomeada do pipeline de análise. Atributos:
  nome amigável, nome técnico interno (não exposto), percentual de progresso
  associado.
- **ProgressEvent**: Evento WebSocket de progresso. Atributos: `event` (string),
  `stage` (nome amigável), `progress` (0–100), `detail` (string opcional, sem PII
  técnico), `timestamp`.
- **PipelineTrace**: Registro de observabilidade de uma etapa. Atributos: `stage`,
  `started_at`, `finished_at`, `duration_ms`, `input_hash`, `result_summary`
  (score, fulfilled_count), `release_id`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário percebe progresso visível durante a análise de um documento
  em 100% das execuções do pipeline; nenhuma análise ocorre em "silêncio total".
- **SC-002**: Usuários do chat recebem o primeiro fragmento da resposta da IA em
  menos de 2 segundos após o envio da mensagem, independentemente do tamanho total
  da resposta.
- **SC-003**: O tempo total de análise de documentos com 10 ou mais critérios
  reduz em pelo menos 30% em relação à execução sequencial atual, sem perda de
  integridade dos resultados.
- **SC-004**: Nenhuma funcionalidade existente regride; 100% dos testes automatizados
  da v1 continuam passando após a implementação da v2.
- **SC-005**: A equipe consegue identificar, via traces, as 3 etapas mais lentas do
  pipeline para qualquer análise realizada com tracing habilitado.
- **SC-006**: Nenhum dado pessoal identificável (PII) ou segredo de autenticação
  aparece em qualquer evento de progresso, log ou trace gerado pelo sistema.

---

## Assumptions

- O frontend já está conectado ao WebSocket de broadcast (`ws:broadcast`) para
  receber eventos `doc.release.update`; a infraestrutura de WebSocket existente
  será reaproveitada sem substituição.
- O chat via WebSocket (`/doc/message/{doc_id}/ws`) é o canal principal de entrega
  de respostas e será o foco do streaming; o endpoint HTTP `/message/ai` mantém
  comportamento síncrono como fallback.
- LangChain (já presente na stack) suporta streaming nativo via `.astream()` e
  será a ferramenta primária para streaming de tokens do chat, sem necessidade de
  bibliotecas adicionais.
- A paralelização do pipeline de release usará `asyncio.gather` ou semáforos
  assíncronos nativos do Python, aproveitando a stack async já existente.
- O tracing será implementado como uma camada de decoradores/middleware opt-in,
  sem dependência de ferramentas de APM proprietárias externas na fase inicial.
- A nomenclatura das etapas visíveis ao usuário será definida em conjunto com o
  time de produto antes da implementação (assumido: "Lendo documento",
  "Analisando critérios", "Finalizando", "Concluído").
- Retrocompatibilidade total é obrigatória: nenhum campo existente será removido.
  Novos campos são aditivos.
- O grau máximo de paralelização será limitado por padrão a 5 avaliações
  simultâneas para evitar rate limiting, configurável via variável de ambiente.
