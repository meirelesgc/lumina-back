<!--
SYNC IMPACT REPORT
Version change: 1.1.0 → 2.0.0
Bump rationale: MAJOR — Remoção de regras de negócio de domínio específicas (Check Tree, RAG com Coordenadas Visuais e regras de auditoria funcional) da constituição, consolidando o documento estritamente como norma suprema de engenharia e arquitetura; transferência integral do conhecimento de domínio para a Documentação Viva do MkDocs (docs/); inclusão formal da obrigatoriedade de documentar grandes mudanças arquiteturais no MkDocs com linguagem humana, direta e coesa; e ampliação e aprofundamento robusto do Princípio da Página HTML Funcional de Validação/Demo (NON-NEGOTIABLE).

Added sections:
  - Reestruturação do Princípio VI: Documentação Viva e Acessível no MkDocs (foco no humano, direto e coeso para grandes mudanças).
  - Ampliação robusta do Princípio VII: Página HTML Funcional de Validação/Demo (handoff para frontend, contratos vivos executáveis, zero build step e observabilidade visual).

Modified principles:
  - Princípio I: Arquitetura em Camadas (generalizado sem acoplamento a regras específicas de domínio).
  - Princípio II: Inteligência Artificial Responsável e Engenharia de LLMs (reorganizado do antigo Princípio III, removendo regras de negócio de domínio e preservando diretrizes de engenharia de IA).
  - Princípio VI: Documentação Viva e Acessível no MkDocs (antigo Princípio VII).
  - Princípio VII: Página HTML Funcional de Validação/Demo (antigo Princípio VIII).

Removed sections:
  - Antigo Princípio II: Base de Conhecimento (Check Tree) — transferido integralmente para docs/dominio/check-tree.md.
  - RAG com Coordenadas Visuais e verificações específicas de template/ABNT do antigo Princípio III — transferidos para docs/dominio/rag-coordenadas.md e docs/dominio/conformidade.md.

Follow-up TODOs: Nenhum.
-->

# Lumina Back Constitution

## Core Principles

### I. Arquitetura em Camadas (Service-Repository)

Todo código de aplicação DEVE respeitar a separação rígida de responsabilidades
em camadas bem delimitadas. Nenhuma camada pode ultrapassar seu escopo.

- **Routers** (`lumina/routers/`): Recebem requisições HTTP e WebSockets,
  validam payloads de entrada através de schemas Pydantic, injetam dependências,
  delegam a execução para a camada de services e retornam respostas com códigos
  HTTP apropriados. NUNCA contêm consultas SQL diretas, regras de negócio ou
  chamadas diretas a LLMs.
- **Services** (`lumina/services/`): Orquestram a lógica de negócio, regras de
  domínio, validações de integridade e coordenam chamadas a repositórios e
  serviços externos (provedores de IA, storage, cache, mensageria). Recebem
  dependências via injeção do FastAPI (`Annotated` em `core/dependencies.py`).
- **Repositories** (`lumina/repositories/`): Encapsulam o acesso e persistência
  de dados relacionais via SQLAlchemy 2.0 assíncrono (`AsyncSession`). NUNCA
  lançam `HTTPException` — o tratamento de erro de negócio é responsabilidade
  exclusiva dos services e routers.
- **Models** (`lumina/models.py`): Entidades relacionais SQLAlchemy 2.0 com
  `Mapped` e `mapped_column`. Entidades de negócio compartilham o `AuditMixin`
  (soft delete via `deleted_at`, timestamps `created_at`/`updated_at` e
  rastreamento de autoria `created_by`/`updated_by`/`deleted_by`).
- **Schemas** (`lumina/schemas/`): Contratos Pydantic de entrada, saída,
  validações de dados e enums compartilhados.
- **Features** (`lumina/features/`): Módulos autocontidos para funcionalidades
  especializadas de maior complexidade. Cada feature DEVE encapsular seus
  próprios schemas, lógica e templates de prompt, sendo orquestrada por um
  service dedicado na camada de services.
- **Core** (`lumina/core/`): Infraestrutura transversal do sistema — engine de
  banco de dados, configurações via `pydantic_settings.BaseSettings`, segurança
  e tokens JWT, injeção de dependências e clientes de cache e mensageria.

**Rationale**: O isolamento estrito garante que mudanças em componentes de
infraestrutura ou fornecedores externos não contaminem as regras de domínio,
permitindo manutenção segura e testes unitários independentes por camada.

### II. Inteligência Artificial Responsável e Engenharia de LLMs

A utilização de Modelos de Linguagem (LLMs) e componentes de inteligência
artificial DEVE seguir rigorosas práticas de engenharia que garantam
segurança jurídica, proteção de privacidade, determinismo e controle de custos.

- **Anonimização e Privacidade por Padrão (LGPD)**: Nenhum dado pessoal
  identificável (PII) pode ser vetorizado ou transmitido para provedores
  externos de LLM sem prévia anonimização via ferramentas dedicadas (como
  Microsoft Presidio). Mapeamentos reversíveis devem ser mantidos apenas em
  metadados restritos aos usuários autorizados.
- **Saídas Estruturadas (Structured Output)**: Toda inferência de LLM que
  alimenta regras de backend DEVE utilizar validação estruturada obrigatória
  (Pydantic models ou `JsonOutputParser`) para garantir parsing determinístico
  e prevenir quebras de contrato de dados.
- **Centralização e Versionamento de Prompts**: Prompts NUNCA devem ser
  declarados inline ou dispersos em classes de serviço. Devem residir em
  módulos dedicados de prompts (`lumina/prompts.py` ou templates Jinja2 em
  `features/prompts/`), permitindo versionamento, revisão e auditoria clara.
- **Processamento Concorrente e Eficiência**: Operações sobre múltiplos itens
  ou critérios DEVEM priorizar execução em lote (`chain.abatch`) e
  concorrência assíncrona controlada (`asyncio.gather`), mitigando latência e
  otimizando requisições.
- **Rastreabilidade de Inferência**: Chamadas a modelos devem preservar
  metadados mínimos (modelo utilizado, parâmetros de temperatura, tokens
  consumidos e versão do prompt) para auditoria e reproducibilidade.

**Rationale**: Modelos de linguagem são dependências externas estocásticas.
Tratá-los com validação de tipos, sanitização de dados prévia e contratos
estruturados transforma saídas probabilísticas em saídas de engenharia seguras.

### III. Testes Orientados a Risco (NON-NEGOTIABLE)

A suíte de testes do Lumina Back DEVE ser orientada a risco e comportamento,
e não à métrica vazia de cobertura de linhas. A metodologia canônica está
documentada na skill `.agents/skills/fastapi-testing-methodology/SKILL.md`.

- **Pirâmide de Testes (5 camadas)**:
  1. `tests/unit/services/` — Regras de negócio puras com mocks completos de
     repositórios (`AsyncMock`, `pytest-mock`).
  2. `tests/integration/repositories/` — Consultas SQL contra banco real via
     fixture `session` (savepoints).
  3. `tests/api/routers/` — Fluxos ponta a ponta com `TestClient`.
  4. Testes de segurança transversais (401/403) integrados em `tests/api/`.
  5. Testes de regressão nos diretórios pertinentes.
- **Matriz de Risco**: A profundidade de teste deve ser proporcional à
  criticidade da funcionalidade:
  - Crítico (autenticação, segurança, autorização, regras centrais): Unit +
    Repo + API + Security.
  - Alto (mutações complexas, transações financeiras/jurídicas): Unit + Repo +
    API.
  - Médio (consultas com filtros dinâmicos, relatórios): Unit + Repo (se query
    complexa).
  - Baixo (CRUDs simples, health checks): API Integration.
- **Isolamento de Banco via Testcontainers**: Provisionamento único de
  PostgreSQL por sessão de teste com aplicação de DDL e reversão de estado
  por transações aninhadas (Savepoints) a cada teste. É PROIBIDO executar
  `create_all`/`drop_all` em testes individuais.
- **Massas de Dados com Factory Boy**: Dados de teste em `tests/factories/`.
  É PROIBIDO gerar `uuid4()` avulsos para chaves estrangeiras; relacionamentos
  devem instanciar entidades válidas.
- **Separação Categórica de Testes de IA**:
  1. *AI Integration Tests*: Utilizam `FakeListChatModel` para validar fluxos
     sem consumir tokens. Executam em `poetry run task test`.
  2. *AI Contract Tests*: Validam resiliência de schemas contra JSONs
     corrompidos ou truncados. Executam em `poetry run task test`.
  3. *AI Evaluation*: Chamadas reais a LLMs com datasets padronizados
     (`tests/ai/evaluation/datasets/`). Marcados com `@pytest.mark.ai`.
     Executam SOMENTE em `poetry run task test-ai`.
- **Guardrail de Cobertura**: Mínimo de 80% de cobertura geral.

**Rationale**: Testes que gastam tokens ou dependem de redes externas em CI/CD
tornam a esteira cara, lenta e frágil. A tripla divisão de IA mantém o CI
rápido e determinístico, preservando a avaliação qualitativa para execuções sob
demanda.

### IV. Simplicidade e Consistência de Código

Todo código da aplicação DEVE seguir padrões rígidos de formatação e estilo,
verificados de maneira automática.

- **Limite de Linha**: 79 caracteres por linha (estilo PEP 8 / Ruff).
- **Aspas**: Aspas simples `'` por padrão em todo o código Python.
- **Ruff**: Linter e formatador único do repositório. Regras ativas:
  `['I', 'F', 'E', 'W', 'PL', 'PT']`.
- **Tipagem Estática Integral**: Funções, parâmetros, métodos e retornos DEVEM
  possuir anotações de tipo estáticas explícitas. Schemas Pydantic cuidam da
  validação nas bordas da aplicação.
- **Uso Estrito do Poetry**: NUNCA execute ferramentas de sistema diretamente.
  Sempre utilize `poetry run <comando>` ou ative o ambiente via `poetry shell`.
- **Migrações Automáticas com Alembic**: Qualquer alteração em `models.py`
  deve gerar migração via `poetry run alembic revision --autogenerate`.
  O diretório `migrations/` é excluído do linter Ruff.

**Rationale**: Consistência estilística verificada por ferramentas elimina
fricções em revisões de PR e assegura uniformidade em todo o código-fonte.

### V. Segurança e Privacidade por Padrão

- **Autenticação**: Tokens JWT (`HS256`) gerados com segredo robusto e hash
  de senhas via **Argon2** (`pwdlib`).
- **Autorização Contextual**: Acesso a recursos e documentos controlado por
  matriz de permissões (`AccessType`: owner, advisor, viewer), validada em
  services antes de repassar chamadas ao repositório.
- **Exclusão Lógica Obrigatória (Soft Delete)**: Entidades com `AuditMixin`
  utilizam `deleted_at` e `deleted_by`. Exclusões físicas são expressamente
  vedadas em rotinas normais de negócio.
- **Trilha de Auditoria**: Mutações em entidades centrais geram registros
  imutáveis na tabela `audit_logs` via `audit_service`.
- **Proteção LGPD**: Dados identificáveis sensíveis devem ser mascarados antes
  de qualquer processamento externo (conforme Princípio II).

**Rationale**: Um sistema de auditoria que falha na proteção de seus próprios
registros e credenciais perde a credibilidade técnica e legal.

### VI. Documentação Viva e Acessível no MkDocs (NON-NEGOTIABLE)

O repositório adota a prática de **Documentação Viva**. A documentação não é um
registro estático após o fato, mas um ativo sincronizado com o código, publicado
via **MkDocs** no diretório `docs/`.

- **Documentação de Grandes Mudanças**: Mudanças arquiteturais relevantes,
  alterações de governança, remoções ou adições de princípios constitucionais e
  evoluções nas regras de negócio DEVEM ser documentadas formalmente no MkDocs
  no momento em que ocorrem.
- **Linguagem Focada no Humano, Direta e Coesa**: O conteúdo no MkDocs DEVE ser
  redigido em tom claro, acessível e direto para seres humanos (desenvolvedores,
  revisores, gestores e stakeholders não-técnicos). É mandatório:
  - Focar no "o que o sistema faz", "por que foi desenhado assim" e "qual
    problema resolve".
  - Evitar jargões excessivos e pormenores de implementação voláteis.
  - Utilizar diagramas Mermaid para fluxos e relações entre componentes.
  - Apresentar exemplos práticos e tabelas comparativas concisas.
- **Repositório Central de Regras de Domínio**: Regras de negócio da aplicação
  (como a Base de Conhecimento, fatiamento de documentos, normas ABNT e modelos
  específicos) NÃO pertencem à constituição; pertencem à seção de Domínio do
  MkDocs (`docs/dominio/`).
- **Sincronização com Especificações (Spec Kit)**: Cada nova funcionalidade
  especificada em `specs/` DEVE ter sua respectiva página de resumo funcional
  criada ou atualizada em `docs/`.
- **Validação de Build**: A documentação deve compilar com zero erros através
  de `poetry run task docs-build` (ou `mkdocs build`).

**Rationale**: Códigos e especificações técnicas atendem bem agentes e
engenheiros, mas uma documentação viva, humana e coesa é indispensável para a
continuidade do projeto e comunicação com stakeholders.

### VII. Página HTML Funcional de Validação/Demo (NON-NEGOTIABLE)

Toda especificação (spec) que adicionar ou alterar comportamento observável no
backend DEVE incluir uma **página HTML funcional de demonstração e validação**.

Esta página NÃO é um frontend definitivo de produção. Trata-se de um artefato
pragmático de validação, documentação interativa e referência viva.

- **Objetivos Centrais**:
  1. *Validação Manual Ponta a Ponta*: Permitir que o engenheiro ou agente
     valide o fluxo de ponta a ponta em segundos, sem depender de Postman ou
     comandos curl complexos.
  2. *Contrato Executável e Handoff para o Frontend*: Servir como guia vivo
     para os desenvolvedores de frontend entenderem imediatamente como chamar
     os endpoints, quais cabeçalhos enviar, o formato real do payload de
     resposta e o comportamento em situações de erro.
  3. *Demonstração Imediata*: Permitir demonstrar funcionalidades em reuniões
     de alinhamento sem necessitar que o frontend de produto esteja pronto.
- **Diretrizes Técnicas de Construção**:
  - **Zero Build Step**: Construída estritamente com HTML5 semântico, estilos
    limpos (CSS vanilla ou Tailwind CSS via CDN) e JavaScript moderno
    (`fetch`, `async/await`). É EXPRESSAMENTE VEDADO o uso de frameworks
    pesados (React, Vue, Angular) ou bundlers para páginas de demo.
  - **Servida pelo Próprio FastAPI**: As demos DEVEM ser armazenadas em
    `lumina/static/demos/<nome-da-spec>/` e servidas diretamente pela montagem de
    arquivos estáticos em `/demos/<nome-da-spec>/`. NUNCA suba servidores web
    ou processos paralelos.
  - **Catálogo Central**: Toda nova demo deve ser listada com título, badge e
    descrição clara no catálogo geral em `lumina/static/demos/index.html`.
  - **Consumo Real**: A demo interage diretamente com os endpoints reais da API
    em execução, sem dados mockados no cliente.
  - **Autenticação e Personas**: A demo deve conter controles visuais para
    informar token JWT ou alternar rapidamente entre personas de teste (ex:
    Aluno, Orientador, Administrador), reutilizando as rotas reais de auth.
  - **Transparência e Observabilidade na Interface**:
    - Campos claros para parâmetros de entrada;
    - Botões autoexplicativos para disparar ações;
    - Indicador visual de processamento em andamento;
    - Exibição legível do status HTTP e payload de resposta retornado;
    - Alerta visual explícito (etiquetas destacadas) em ações que persistam,
      alterem ou deletem dados reais no banco de dados.
- **Isolamento Arquitetural e Desacoplamento**:
  - A demo NÃO pode conter lógica ou validações de negócio no JavaScript;
    toda regra reside no backend.
  - Nenhuma linha do código de produção pode depender da existência da demo.
  - A demo DEVE poder ser excluída a qualquer momento com zero impacto no
    sistema.
  - NUNCA crie endpoints inseguros ou contorne o RBAC do backend apenas para
    facilitar a demo.
- **Definition of Done (DoD) para Specs com Backend**:
  - [ ] Backend implementado e aderente à arquitetura em camadas.
  - [ ] Testes automatizados cobrindo a matriz de risco.
  - [ ] Página HTML de validação criada em `lumina/static/demos/<spec-name>/`.
  - [ ] Card descritivo adicionado em `lumina/static/demos/index.html`.
  - [ ] Página servida diretamente pela montagem `/demos/` do FastAPI.
  - [ ] Fluxo de autenticação/personas funcionando na interface.
  - [ ] Todos os critérios de aceitação exercitáveis manualmente pela página.
  - [ ] Payloads de sucesso e de erro visíveis de forma clara.
  - [ ] Mudança e resumo funcional documentados no MkDocs em linguagem humana.
  - [ ] Validação de zero acoplamento (a demo é puramente consumidora e
    descartável).

**Rationale**: Swagger define tipos e testes automatizados validam lógica, mas
uma demo HTML executável valida a experiência real da API, elimina ruídos no
handoff com o frontend e comprova o valor de negócio de forma tangível.

## Workflow de Desenvolvimento com Agentes

Regras que governam como agentes e desenvolvedores operam ao trabalhar no
Lumina Back:

- **Git Worktrees para Paralelização**: Em tarefas complexas que permitam
  decomposição em subtarefas independentes, DEVE-SE utilizar git worktrees
  separados (`git worktree add`) para execução paralela sem conflitos de working
  tree.
  - Padrão de branch: `feature/<feature-name>/<subtask-name>`.
  - Agentes NUNCA realizam merge direto em `develop` ou `main`. A consolidação
    final é sempre conduzida ou autorizada pelo desenvolvedor responsável.
- **Atomicidade e Conventional Commits**: Commits devem ser atômicos e seguir o
  padrão Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
- **Validação Pré-Entrega**: Nenhuma entrega é aceita sem a aprovação completa
  de `poetry run task test`. Testes que envolvem IA real (`task test-ai`) devem
  ser executados e seus resultados relatados quando aplicável.
- **Limpeza de Worktrees**: Ao concluir, os worktrees devem ser removidos
  (`git worktree remove`) mantendo o repositório organizado.

## Stack Tecnológica e Infraestrutura

Definição canônica dos componentes e versões do projeto:

| Categoria | Tecnologia | Versão/Constraint |
|---|---|---|
| Linguagem | Python | ≥3.13, <3.14 |
| Framework Web | FastAPI | ≥0.120.1 |
| ORM | SQLAlchemy 2.0 (Async) | ≥2.0.44 |
| Migrações | Alembic | ≥1.17.0 |
| Banco de Dados | PostgreSQL 17 + pgvector | pgvector/pgvector:pg17 |
| Cache/Pub-Sub | Redis | ≥7.0.1 |
| Mensageria | RabbitMQ (Pika) | ≥1.3.2 |
| LLM Framework | LangChain + LangChain OpenAI | ≥1.0.2 |
| Vectorstore | PGVector (LangChain) | ≥0.0.16 |
| Embeddings | OpenAI text-embedding-3-small | — |
| PDF Processing | PyMuPDF (fitz) | ≥1.26.5 |
| Anonimização LGPD | Microsoft Presidio | ≥2.2.360 |
| Relatórios PDF | ReportLab | ≥4.4.4 |
| Storage | Local / S3 (aioboto3) | Configurável via `STORAGE_PROVIDER` |
| Notificações | Evolution API (WhatsApp) | v2.3.6 |
| Documentação Viva | MkDocs + MkDocs Material | ≥1.6.1 / ≥9.7.7 |
| Gerenciador de Pacotes | Poetry | ≥2.0.0 |
| Linter/Formatter | Ruff | ≥0.12.11 |
| Testes | Pytest + Testcontainers + Factory Boy | — |
| Automação de Tarefas | Taskipy | ≥1.14.1 |
| Containerização | Docker + Docker Compose | — |

## Governance

Esta constituição é o documento normativo supremo do projeto Lumina Back.
Todas as práticas de desenvolvimento, revisão de código e decisões
arquiteturais DEVEM obedecer aos princípios aqui estabelecidos.

- **Supremacia**: Em caso de conflito entre esta constituição e qualquer outro
  documento (AGENTS.md, skills, guias locais), a constituição prevalece.
  O `AGENTS.md` atua como guia operacional complementar, nunca contraditório.
- **Emendas e Versionamento SemVer**:
  - **MAJOR**: Remoção, redefinição incompatível de princípios ou alteração nos
    limites arquiteturais fundamentais.
  - **MINOR**: Adição de novo princípio ou expansão material de orientações.
  - **PATCH**: Clarificações de redação, correções ortográficas e refinamentos
    não-semânticos.
  - Toda emenda DEVE incluir o preenchimento do Sync Impact Report no topo do
    arquivo.
- **Revisão de Conformidade**: Todo pull request deve ser inspecionado quanto à
  sua aderência aos princípios. Desvios ou complexidades anômalas devem ser
  justificados explicitamente.

**Version**: 2.0.0 | **Ratified**: 2026-08-31 | **Last Amended**: 2026-09-05
