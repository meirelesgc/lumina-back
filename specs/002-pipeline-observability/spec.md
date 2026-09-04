# Feature Specification: Observabilidade e Diagnóstico de Execução do Pipeline para Melhoria Contínua

**Feature Branch**: `002-pipeline-observability`

**Created**: 2026-09-05

**Status**: Draft

**Input**: User description: "SPEC - LOGS PARA MELHORIA CONTINUA: Registrar o que ocorre no pipeline de IA com transparência para melhoria contínua, modelo de execução ProcessingRun com eventos/etapas, estritamente restrito a administradores (com demo interna), persistência desacoplada em formato estruturado (preferência JSONL ou eventos desacoplados sem acoplamento a tabelas relacionais pesadas), níveis de log com proteção estrita LGPD e visualização clara de etapas e critérios em paralelo. Pontos importantes: compatibilidade direta do run_id com o id da release (run_id == release_id) para fácil localização e busca; e interface visual mantida no padrão mais simples (sem gráficos pesados, lista/tabela limpa e acordeão expansível de etapas)."

## Clarifications

### Session 2026-09-05
- Q: Como as macroetapas de Ingestão (Extração, Identificação de Seções e Anonimização) devem se conectar ao log da Release (`release_id`) no pipeline de observabilidade? → A: Consolidar no `{release_id}.jsonl`: as métricas e eventos das etapas prévias do documento (extração, identificação de seções e anonimização) são incorporadas à linha do tempo da release, garantindo que a consulta por `release_id` apresente o histórico completo das 7 macroetapas em um único arquivo.
- Q: Em quais condições a cópia integral do prompt montado e a saída bruta (raw output) da LLM devem ser gravadas no campo data dos eventos de avaliação? → A: Ativação por modo de depuração (`DEBUG_PIPELINE_RUNS` ativo por padrão em desenvolvimento/demo): quando ativo, persiste prompts integrais, raw outputs da LLM e janelas textuais de entrada no `data`; em modo produção estrito, registra métricas estruturadas, contadores de tokens, parecer final, notas e citações para otimização de I/O e disco.
- Q: Qual padrão de interface a tela de demonstração deve adotar para permitir a inspeção detalhada das variáveis de Entrada, Estado Interno e Saída de cada uma das 7 macroetapas e critérios? → A: Acordeão com sub-abas [Entrada | Estado Interno | Saída]: cada etapa e critério avaliado expande um cartão que categoriza seus dados nessas três abas lógicas, incluindo blocos de texto expansíveis com botão de cópia rápida para prompts integrais e saídas brutas da LLM, mantendo o padrão zero build step em HTML/CSS/JS vanilla.
- Q: Qual política de retenção e descarte de dados deve ser aplicada aos arquivos de log estruturado (.jsonl) no diretório de armazenamento? → A: Retenção por contagem e tempo (últimas 30 execuções ou 7 dias): rotação automática descartando registros e arquivos .jsonl mais antigos que excedam esses limites, mantendo o índice `index.jsonl` e o armazenamento em disco enxutos.
- Q: Quando a LLM retornar uma saída que quebre o contrato de schema Pydantic (DocumentReleaseFeedback) durante a avaliação de um critério, como a esteira e o log devem registrar essa falha? → A: Isolamento do critério com retentativas: executa até 3 retentativas automáticas e, persistindo a falha, registra o critério individual como `failed` no evento `CRITERION_EVALUATED` contendo o erro exato de validação no `schema_validation_error` e a saída bruta causadora, sem interromper ou invalidar os demais critérios avaliados em paralelo na release.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rastreamento Estruturado de Execuções e Etapas do Pipeline (Priority: P1)

Como um engenheiro de IA ou administrador da plataforma, desejo que cada processamento de documento pelo pipeline possua um ciclo de vida estruturado e rastreável por um identificador único de execução (`run_id`), compatível e correspondente diretamente ao identificador da release (`release_id`), para que eu possa acompanhar cronologicamente cada etapa do fluxo (extração, identificação de seções, anonimização, geração de embeddings, avaliação e síntese), seu status de sucesso ou falha, e o tempo exato consumido em cada fase, localizando a execução sem qualquer atrito ou ambiguidade.

**Why this priority**: A rastreabilidade por execução alinhada ao `release_id` é a fundação técnica indispensável para qualquer esforço de melhoria contínua. Sem saber onde o pipeline passa a maior parte do tempo ou em qual etapa ocorrem falhas, é impossível otimizar modelos, custos ou latência. A correspondência 1:1 entre `run_id` e `release_id` simplifica drasticamente a correlação com os registros de negócio.

**Independent Test**: Disparar o processamento de uma release de documento no pipeline (`POST /doc/{doc_id}/release`). O sistema deve inicializar uma execução estruturada cujo `run_id` é idêntico ao `release_id` gerado, registrar eventos de início e conclusão de cada etapa com timestamps e durações correspondentes, e concluir a execução com status final (`completed` ou `failed`) e duração total consolidada.

**Acceptance Scenarios**:

1. **Given** um documento válido submetido para criação de release no pipeline (`POST /doc/{doc_id}/release`), **When** o processamento é iniciado, **Then** o sistema deve atribuir à execução um `run_id` idêntico ao `release_id` da release em processamento, registrando o evento de início da execução com status `in_progress`.
2. **Given** um processamento em andamento, **When** cada etapa do pipeline (extração, seções, anonimização, embeddings, avaliação, síntese) é executada com sucesso, **Then** o sistema deve registrar a conclusão da etapa com a duração precisa em milissegundos, quantidade de itens processados e status `completed`.
3. **Given** uma falha inesperada em qualquer etapa do pipeline, **When** a exceção ocorre, **Then** a etapa atual deve ser registrada como `failed` contendo a mensagem de erro resumida, e a execução global deve transicionar para `failed` com o tempo acumulado até o erro.
4. **Given** um administrador buscando os logs pelo identificador de uma release (`release_id`), **When** consulta a API de observabilidade informando o ID da release, **Then** o sistema deve retornar imediatamente a execução correspondente (`run_id == release_id`).

---

### User Story 2 - Isolamento e Controle de Acesso Restrito a Administradores (Priority: P1)

Como um administrador do sistema, desejo que todos os registros de execução, métricas de observabilidade e diagnósticos do pipeline sejam de acesso estritamente restrito a usuários com perfil administrativo, garantindo que alunos, orientadores ou usuários comuns não tenham acesso a informações internas de auditoria, tempos operacionais ou artefatos de IA de outros processamentos.

**Why this priority**: Logs de execução interna, volumes de tokens, prompts de sistema e detalhes de erros contêm informações sensíveis de infraestrutura e governança institucional (LGPD e segurança). O vazamento desses registros para perfis não autorizados viola as diretrizes de segurança da aplicação.

**Independent Test**: Tentar consultar a lista de execuções ou o detalhe de uma execução utilizando credenciais de usuário padrão (não administrador) e verificar a recusa com código de acesso negado (`403 Forbidden`). Em seguida, realizar a mesma consulta com credenciais de administrador e verificar o retorno completo dos dados.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado sem privilégios de administrador (ex: perfil estudante ou pesquisador), **When** o usuário tenta listar execuções (`GET /processing-runs`) ou consultar detalhes de uma execução específica (`GET /processing-runs/{id}`), **Then** o sistema deve rejeitar a requisição com código `403 Forbidden`.
2. **Given** uma requisição não autenticada (sem credenciais), **When** qualquer endpoint de observabilidade de pipeline for acionado, **Then** o sistema deve rejeitar o acesso com código `401 Unauthorized`.
3. **Given** um usuário autenticado com perfil de administrador, **When** o usuário consulta a listagem ou detalhe de execuções, **Then** o sistema deve autorizar o acesso e fornecer os dados de execução solicitados.

---

### User Story 3 - Visualização e Diagnóstico Interativo Simples (Painel / Demo) (Priority: P2)

Como administrador ou líder técnico, desejo acessar uma interface visual extremamente simples, limpa e funcional servida diretamente pela aplicação (seguindo o padrão minimalista de lista de releases, indicador de status e seções expansíveis de etapas, sem gráficos complexos ou bibliotecas pesadas), para que eu possa inspecionar rapidamente o histórico recente de processamentos, selecionar uma release para visualizar o tempo gasto em cada etapa, identificar gargalos de processamento e validar fluxos em reuniões de acompanhamento.

**Why this priority**: Uma visualização enxuta, clara e sem distrações permite aos operadores responder em poucos segundos a perguntas como "quanto tempo demorou a release X?" e "onde foi gasto mais tempo?". Cumpre também o Princípio VII da Constituição (Página HTML Funcional de Validação/Demo) com zero atrito e zero build step.

**Independent Test**: Acessar a página de demonstração e validação administrativa no navegador (`/demos/pipeline-observability/`), verificar a lista simples de releases com status, tempos e datas; clicar em uma release com sucesso para visualizar as etapas e suas durações em formato de lista expansível; clicar em uma release com erro para verificar o destaque do estágio da falha.

**Acceptance Scenarios**:

1. **Given** a aplicação em execução, **When** o administrador acessa `/demos/pipeline-observability/`, **Then** a interface deve carregar uma visão enxuta com campo de busca/filtro por `release_id` e a listagem das execuções recentes contendo ID da release, documento de referência, status visual (`SUCCESS`, `FAILED`, `IN_PROGRESS`), duração total formatada (ex: `1m42s`) e data/hora.
2. **Given** a listagem de execuções, **When** o administrador seleciona uma release específica, **Then** a interface deve expandir a visualização detalhada da execução, apresentando cada etapa sequencialmente com sua respectiva duração e indicador de status (ex: `✓ Extração 4.2s`, `✓ Avaliação 61.2s`).
3. **Given** uma etapa que envolveu múltiplos subitens (como a avaliação paralela de critérios), **When** o administrador clica para expandir a etapa, **Then** a interface deve exibir a lista simples dos critérios avaliados, seus tempos individuais e resultados resumidos.

---

### User Story 4 - Diagnóstico Granular de Avaliações Paralelas por Critério (Priority: P2)

Como engenheiro de IA, desejo que a etapa de avaliação registre métricas individuais para cada critério avaliado em lote ou concorrentemente, para que eu possa identificar quais critérios específicos apresentam maior latência, demandam mais tempo de inferência ou geram falhas recorrentes de validação.

**Why this priority**: A avaliação de critérios é a fase mais demorada e de maior custo computacional no processamento de documentos. A agregação cega dessa etapa impede a otimização de prompts lentos e a identificação de critérios com baixa precisão ou tempo excessivo.

**Independent Test**: Submeter um documento com dezenas de critérios para avaliação concorrente. O sistema deve registrar, para cada critério avaliado dentro da etapa de avaliação, o tempo individual de resposta, pontuação, quantidade de citações recuperadas e status de conclusão.

**Acceptance Scenarios**:

1. **Given** a execução da etapa de avaliação com múltiplos critérios concorrentes, **When** os critérios são avaliados em paralelo, **Then** o sistema deve registrar para cada critério seu identificador, duração individual em milissegundos, status e métricas resumidas (pontuação e citações).
2. **Given** que um dos critérios da avaliação apresente erro de formato ou timeout durante a execução concorrente, **When** os demais critérios concluem com sucesso, **Then** o critério falho deve ser registrado com status `failed` e detalhe do erro, enquanto os critérios bem-sucedidos permanecem preservados e acessíveis para diagnóstico.

---

### User Story 5 - Modo de Depuração Controlada com Salvaguarda de Dados Pessoais (LGPD) (Priority: P3)

Como administrador em ambiente de testes ou diagnóstico avançado, desejo ativar condicionalmente a gravação de artefatos intermediários (resumos de entradas, prompts submetidos, respostas estruturadas do modelo e contagem de tokens), mantendo uma barreira estrita que impeça a gravação de dados pessoais identificáveis (PII) em texto puro, para que eu possa diagnosticar a qualidade do modelo sem violar preceitos de privacidade e conformidade legal.

**Why this priority**: O diagnóstico detalhado de modelos estocásticos requer análise de prompts e saídas intermediárias, mas essa flexibilidade não pode comprometer a privacidade dos titulares nem sobrecarregar o armazenamento em produção.

**Independent Test**: Configurar o sistema com o modo de captura de artefatos desativado (padrão) e validar que apenas métricas e durações são persistidas. Em seguida, ativar o modo de depuração em ambiente controlado, processar um documento anonimizado e verificar que os artefatos de prompt/resposta registrados contêm apenas dados anonimizados e estruturados, sem CPF, nomes reais ou contatos.

**Acceptance Scenarios**:

1. **Given** o sistema operando em modo padrão de produção (`debug = false`), **When** um processamento de documento é concluído, **Then** o sistema deve persistir apenas metadados de execução, status, tempos e contadores, sem armazenar prompts integrais ou artefatos volumosos.
2. **Given** o sistema operando com modo de depuração ativado (`debug = true`), **When** uma etapa de inferência de IA é concluída, **Then** o sistema deve registrar o resumo da entrada, o modelo utilizado, a contagem de tokens e a saída estruturada para fins de diagnóstico.
3. **Given** qualquer modo de execução (produção ou depuração), **When** dados intermediários forem registrados, **Then** o sistema NUNCA deve persistir dados pessoais identificáveis não-anonimizados (como CPF, CNPJ, telefones ou nomes de titulares não mascarados), respeitando as diretrizes de anonimização da plataforma.

---

### Edge Cases

- **Interrupção Inesperada do Servidor ou Processo**: Se o processo do backend for encerrado ou cair durante uma etapa em andamento, o sistema deve registrar o evento de término anormal ou identificar execuções pendentes cujo tempo decorrido excedeu o limite máximo (timeout operacional), marcando-as como `failed` na leitura.
- **Processamento de Documento sem Critérios**: Se um documento for processado com lista de critérios vazia, a etapa de avaliação deve ser registrada como `completed` com duração mínima e contagem de itens igual a zero, sem gerar exceções.
- **Falha Parcial em Execuções Paralelas de Critérios**: Se 2 de 40 critérios falharem durante a avaliação concorrente, a etapa de avaliação global deve concluir reportando o número exato de sucessos e falhas, registrando os erros específicos dos 2 critérios sem invalidar os 38 critérios que foram bem-sucedidos.
- **Falha de Formatação ou Quebra de Schema pela LLM**: Caso a LLM retorne um JSON inválido ou incompatível com o schema Pydantic `DocumentReleaseFeedback`, o pipeline deve realizar até 3 retentativas automáticas. Se o erro persistir, o critério específico deve ser registrado como `failed` contendo a saída bruta e a descrição detalhada em `schema_validation_error`, sem interromper os demais critérios concorrentes da release.
- **Payloads com Tentativa de Injeção de Código (XSS) nos Artefatos de IA**: Respostas de modelos ou mensagens de erro visualizadas na interface de diagnóstico devem ser tratadas de forma restritiva e sanitizada, prevenindo a injeção ou execução arbitrária de scripts no navegador do administrador.
- **Alto Volume de Eventos e Concorrência de Escrita**: Múltiplos processamentos simultâneos gerando eventos estruturados não devem causar bloqueios ou travamentos nas operações principais do pipeline; as gravações de eventos devem ser não-bloqueantes ou atômicas em formato estruturado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE atribuir um identificador imutável de execução (`run_id`, no formato UUID) a cada ciclo de processamento do pipeline. Para processamentos originados a partir da criação de release de documento (`/doc/{doc_id}/release`), o `run_id` DEVE ser compatível e idêntico ao `release_id` correspondente (`run_id = release_id`), garantindo correlação direta 1:1 e facilitando a busca direta pelo ID da release.
- **FR-002**: O sistema DEVE registrar formalmente os eventos de transição de ciclo de vida da execução:
  - `run_started`: Início da execução do processamento.
  - `stage_started`: Início de uma etapa específica do pipeline.
  - `stage_completed`: Conclusão bem-sucedida de uma etapa, com duração e contagem de itens.
  - `stage_failed`: Falha em uma etapa, com duração até o erro e mensagem diagnóstica.
  - `stage_progress`: Atualização de progresso intermediário (ex: critérios avaliados até o momento).
  - `run_completed`: Término bem-sucedido de toda a cadeia de processamento.
  - `run_failed`: Término da execução por falha irrecuperável.
- **FR-003**: O sistema DEVE instrumentar e registrar as seguintes etapas padrão do pipeline de documentos:
  - Extração de texto e estrutura documental (`extraction`).
  - Identificação e classificação de seções (`sections`).
  - Anonimização de dados sensíveis e conformidade LGPD (`anonymization`).
  - Geração e indexação de vetores/embeddings (`embeddings`).
  - Avaliação de conformidade e critérios (`evaluation`).
  - Rastreamento e consolidação de citações (`citations`).
  - Síntese final do parecer/relatório (`synthesis`).
- **FR-004**: Para cada etapa do pipeline, o sistema DEVE registrar de forma obrigatória: identificador da execução (`run_id` / `release_id`), nome da etapa, status (`in_progress`, `completed`, `failed`), carimbo de data/hora de início e fim, duração em milissegundos, quantidade de itens processados e resumo de erro quando aplicável.
- **FR-005**: Na etapa de avaliação concorrente, o sistema DEVE registrar granularmente o resultado de cada critério avaliado em lote, incluindo identificador do critério, tempo individual de avaliação, pontuação atribuída, quantidade de citações e status de sucesso ou erro. Em caso de quebra de schema Pydantic não sanada por retentativas, o sistema DEVE registrar o status `failed` no critério acompanhado da saída bruta e do detalhamento do erro em `schema_validation_error`.
- **FR-006**: O sistema DEVE manter uma camada de abstração de observabilidade (`RunLogger` / Execution Recorder) desacoplada da lógica de negócio do pipeline, permitindo que a persistência de eventos seja realizada em formato estruturado de alta performance (como registros estruturados em arquivos append-only / JSONL ou repositório de eventos especializado) sem acoplar a execução a dependências rígidas de tabelas relacionais pesadas.
- **FR-007**: O sistema DEVE garantir a salvaguarda estrita de dados pessoais (LGPD), sendo EXPRESSAMENTE PROIBIDO registrar dados cadastrais identificáveis não-anonimizados (CPF, CNPJ, telefones, e-mails pessoais ou nomes reais não mascarados) em quaisquer eventos de log ou artefatos de depuração.
- **FR-008**: O sistema DEVE suportar níveis configuráveis de granularidade de registro através de parâmetros do ambiente:
  - *Modo Produção*: Registra identificadores, métricas estruturadas, contadores de tokens, durações, parecer técnico consolidado (`DocumentReleaseFeedback`), notas e contagem de citações com coordenadas.
  - *Modo Depuração / Diagnóstico Avançado* (`DEBUG_PIPELINE_RUNS = true`, ativo por padrão em desenvolvimento e demonstrações): Registra adicionalmente cópias integrais dos prompts montados (`DOCUMENT_ANALYSIS_PROMPT`), saídas textuais brutas (raw output) antes do parse, janelas de entrada de 3.000 caracteres e chaves do mapa de reversão anônimo, sempre submetidos à barreira de sanitização LGPD.
- **FR-009**: O sistema DEVE restringir o acesso a todas as operações de consulta, listagem e detalhamento de observabilidade de pipeline exclusivamente a usuários autenticados com papel de Administrador (`role = admin`). Qualquer tentativa de acesso por usuários não administradores DEVE retornar `403 Forbidden`.
- **FR-010**: O sistema DEVE fornecer endpoints REST para consulta administrativa de execuções:
  - `GET /processing-runs`: Listagem paginada de execuções com suporte a filtros por `release_id` / `run_id`, status, documento de referência e intervalo de datas.
  - `GET /processing-runs/{id}`: Consulta detalhada de uma execução específica (aceitando o `run_id` ou `release_id`), incluindo o sumário executivo, a lista cronológica de etapas e a decomposição de critérios paralelos.
  - `GET /processing-runs/{id}/events`: Consulta cronológica dos eventos atômicos da execução para auditoria avançada.
- **FR-011**: O sistema DEVE disponibilizar uma página HTML funcional de validação e demonstração servida diretamente pelo FastAPI em `/demos/pipeline-observability/`, construída com padrão de interface simples, limpo e direto (zero build step, HTML5 semântico, estilos CSS limpos e JavaScript vanilla, sem dependência de gráficos ou bibliotecas pesadas), contendo:
  - Campo de busca/filtro direto por `release_id` ou `document_id`;
  - Lista/tabela simples com as execuções recentes exibindo ID da Release, status visual, duração total formatada e data/hora;
  - Painel de detalhe expansível em formato de acordeão, apresentando cada etapa sequencialmente com sua duração e indicador de status;
  - Navegação em cada etapa e critério estruturada por sub-abas [Entrada | Estado Interno | Saída], permitindo inspecionar variáveis específicas (como queries executadas, chunks recuperados, parâmetros e métricas);
  - Blocos expansíveis de texto com botão de cópia rápida para prompts integrais e respostas brutas da LLM em modo de depuração;
  - Seção expansível da etapa de avaliação detalhando os critérios avaliados em paralelo (tempo individual, pontuação, citações e erros);
  - Exibição segura de textos e metadados com sanitização restritiva contra injeção de scripts (XSS).
- **FR-012**: O catálogo geral de demonstrações em `lumina/static/demos/index.html` DEVE ser atualizado com a inclusão do card descritivo e link direto para a demonstração de observabilidade do pipeline.
- **FR-013**: O sistema DEVE consolidar no arquivo de log da release (`{release_id}.jsonl`) os registros e métricas das macroetapas prévias de ingestão do documento (extração e chunking, identificação de seções por LLM e anonimização LGPD), apresentando na mesma linha do tempo cronológica a ingestão e a esteira ativa de release (recuperação semântica, avaliação estruturada, resolução de coordenadas e síntese).
- **FR-014**: O sistema DEVE capturar e estruturar no objeto `data` dos eventos os pontos de observabilidade específicos de cada macroetapa do pipeline:
  1. *Extração e Chunking*: Quantidade de páginas processadas, total de chunks gerados, tamanho médio dos chunks (verificação do limiar de 500 caracteres), tipologia de extração aplicada (PyMuPDF, Docx2txtLoader, TextLoader) e contagem de operações de sanitização executadas (remoção de `\x00` ou espaços duplos).
  2. *Identificação de Seções*: Texto delimitado da janela de entrada (até 3.000 caracteres), lista de instâncias `SectionInfo` (`section_name`, `start_text`, `end_text`) e taxa de sucesso na localização dos marcos de texto via `_normalize_with_mapping`.
  3. *Anonimização LGPD*: Tipos e quantitativos de entidades sensíveis identificadas e substituídas (CPF, CNPJ, RG, etc.) e chaves geradas para o mapa de reversão (`<CPF_1>`, `<CNPJ_1>`), com exclusão estrita dos dados originais correspondentes.
  4. *Recuperação Semântica (Retriever)*: Identificador do ramo avaliado, string da query executada com triplicação do nome da seção, lista dos 3 `chunk_id` retornados na busca vetorial inicial e lista final dos `chunk_id` resultantes após expansão contextual de margem (`MARGIN_SIZE = 2`) e deduplicação.
  5. *Avaliação Estruturada (Chain LLM)*: Prompt integral (`DOCUMENT_ANALYSIS_PROMPT`), saída textual bruta da LLM antes do parser, atributos mapeados no schema Pydantic `DocumentReleaseFeedback` (parecer, flag `fulfilled`, nota `score` e citações) e eventuais erros de validação de schema.
  6. *Resolução de Coordenadas*: Relação de identificadores `chunk_id` citados pelo modelo e quantitativo de citações não resolvidas devido a IDs alucinados pelo modelo na checagem cruzada com metadados.
  7. *Síntese Executiva (OiacIA)*: Relação dos 2 ramos com maiores notas e 2 com menores notas selecionados para o prompt e texto particionado da resposta gerada nas categorias: saudação, pontos atendidos, pontos a aprimorar e orientação final.
- **FR-015**: O sistema DEVE aplicar política de retenção e rotação automática de logs estruturados, mantendo no máximo as últimas 30 execuções ou arquivos com até 7 dias de criação no diretório `lumina/storage/pipeline_runs/`, expurgando arquivos `.jsonl` e sincronizando as linhas correspondentes do índice `index.jsonl` para evitar esgotamento de disco.

### Key Entities

- **ProcessingRun**: Representa a unidade global de execução de um ciclo completo de processamento de documento.
  - *Atributos principais*: `id` (UUID imutável, compatível e idêntico ao `release_id` no processamento de releases), `release_id` (UUID da release correspondente), `document_id` (identificador do documento processado), `pipeline_version` (versão da esteira de processamento), `status` (enum: `in_progress`, `completed`, `failed`), `started_at` (timestamp de início), `finished_at` (timestamp de término), `duration_ms` (duração total em milissegundos), `error_summary` (resumo de erro em caso de falha), `metadata` (dados contextuais da execução).
- **ProcessingStage**: Representa uma etapa lógica delimitada dentro de uma execução do pipeline.
  - *Atributos principais*: `id` (UUID), `run_id` (vínculo com a execução / `release_id`), `name` (nome da etapa: extração, seções, anonimização, embeddings, avaliação, citações, síntese), `status` (enum: `in_progress`, `completed`, `failed`), `started_at` (timestamp de início), `finished_at` (timestamp de término), `duration_ms` (duração da etapa), `item_count` (número de seções, chunks ou critérios processados), `error_details` (descrição detalhada do erro na etapa, se houver).
- **ProcessingEvent**: Representa um registro atômico de evento de ciclo de vida ou marco intermediário.
  - *Atributos principais*: `id` (UUID), `run_id` (vínculo com a execução / `release_id`), `stage_name` (etapa associada, se aplicável), `event_type` (enum: `run_started`, `stage_started`, `stage_completed`, `stage_failed`, `stage_progress`, `run_completed`, `run_failed`), `timestamp` (carimbo temporal), `payload` (dados estruturados do evento: métricas, contagem de tokens, resumos ou artefatos em modo depuração).
- **CriterionEvaluationRecord**: Representa o desdobramento granular da avaliação de um critério específico dentro da etapa concorrente de avaliação.
  - *Atributos principais*: `criterion_id` (identificador do critério avaliado), `run_id` (vínculo com a execução / `release_id`), `status` (enum: `completed`, `failed`), `duration_ms` (tempo de avaliação do critério), `score` (pontuação ou resultado da avaliação), `citations_count` (quantidade de evidências/citações vinculadas), `error_message` (erro de inferência ou validação estruturada, se houver).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos processamentos de documentos acionados no pipeline geram um registro de execução com identificador único (`run_id`) compatível e idêntico ao `release_id`, com rastreabilidade temporal ponta a ponta.
- **SC-002**: O impacto de sobrecarga (overhead) computacional e de latência gerado pelo registro de observabilidade não ultrapassa 2% da duração total de execução do pipeline em modo padrão de produção.
- **SC-003**: Um administrador do sistema consegue localizar uma execução informando diretamente o `release_id`, identificar a etapa de maior latência e visualizar o motivo de uma falha em menos de 10 segundos através da interface simples de diagnóstico.
- **SC-004**: 100% das tentativas de acesso aos endpoints e dados de observabilidade do pipeline por perfis não administrativos ou usuários não autenticados são rejeitadas com os códigos de segurança adequados (`403 Forbidden` ou `401 Unauthorized`).
- **SC-005**: 100% dos registros de eventos estruturados e artefatos de depuração permanecem livres de dados pessoais identificáveis não-anonimizados (PII), comprovado por testes automatizados de auditoria de dados.
- **SC-006**: A página de demonstração e validação (`/demos/pipeline-observability/`) adota padrão visual simples (sem gráficos ou scripts externos pesados), carregando no navegador em menos de 1 segundo e permitindo exercitar e inspecionar todos os cenários de sucesso, erro e expansão de critérios paralelos.

## Assumptions

- **Compatibilidade Direta Release-Run**: No fluxo principal de processamento de documentos, o identificador de execução (`run_id`) adota o próprio identificador da release (`release_id`), simplificando a correlação para o operador e eliminando a necessidade de mapeamentos intermediários.
- **Interface Minimalista e Direta**: O design da interface de validação administrativa prioriza a simplicidade, legibilidade e rapidez de diagnóstico (formato em tabela/lista de releases com acordeão de etapas), evitando o uso de gráficos complexos, bibliotecas de canvas ou dashboards sobrecarregados nesta fase inicial.
- **Perfil de Usuário e Autenticação Existentes**: A plataforma já dispõe de mecanismo de autenticação via JWT e controle de privilégios de acesso baseado em papéis (RBAC), permitindo a validação direta do perfil `admin`.
- **Desacoplamento de Armazenamento**: A persistência de eventos de execução prioriza formatos estruturados de alta velocidade e baixo acoplamento (como append-only estruturado em arquivos JSONL ou repositório de eventos especializado), isolada por uma interface de abstração que permite evolução transparente para soluções de telemetria e tracing sem refatoração do pipeline.
- **Pipeline por Etapas Delimitadas**: O pipeline de processamento de documentos possui fronteiras claras de execução (extração, seções, anonimização, embeddings, avaliação paralela, citações e síntese), permitindo a inserção de ganchos (hooks) de observabilidade no início e no final de cada etapa.
- **Comportamento Padrão Econômico e Seguro**: Por padrão em ambiente de produção, o armazenamento de artefatos intermediários volumosos (prompts completos e respostas de modelos) permanece desativado, evitando crescimento desordenado de dados e garantindo economia de armazenamento.
- **Interface Segura e Restritiva**: A renderização de textos e resumos na página de validação utiliza sanitização rigorosa para prevenir riscos de injeção de scripts (XSS), convertendo apenas um subconjunto seguro de formatação textual.
