<!--
SYNC IMPACT REPORT
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR — Adicionado Princípio VIII: Página HTML Funcional de Validação/Demo (NON-NEGOTIABLE).

Added sections:
  - VIII. Página HTML Funcional de Validação/Demo (NON-NEGOTIABLE)

Modified principles: N/A
Removed sections: N/A
Follow-up TODOs: Nenhum.
-->

# Lumina Back Constitution

## Core Principles

### I. Arquitetura em Camadas (Service-Repository)

Todo código de aplicação DEVE respeitar a separação rígida de responsabilidades
em camadas. Nenhuma camada pode ultrapassar seu escopo.

- **Routers** (`lumina/routers/`): Recebem requisições HTTP/WebSocket,
  validam entrada via schemas Pydantic, delegam para services e retornam
  respostas. NUNCA contêm lógica de negócio, queries SQL ou chamadas a LLMs.
- **Services** (`lumina/services/`): Orquestram regras de negócio, validações
  de domínio e coordenam chamadas a repositórios e serviços externos (IA,
  storage, cache). Recebem dependências via injeção do FastAPI (`Annotated`
  types em `core/dependencies.py`).
- **Repositories** (`lumina/repositories/`): Encapsulam consultas SQLAlchemy
  puras (queries, joins, agregações). NUNCA lançam `HTTPException` — essa
  responsabilidade é exclusiva dos services/routers.
- **Models** (`lumina/models.py`): Entidades SQLAlchemy 2.0 com `Mapped` e
  `mapped_column`. Modelos compartilham o `AuditMixin` (soft delete via
  `deleted_at`, timestamps `created_at`/`updated_at` e rastreamento de
  `created_by`/`updated_by`/`deleted_by`).
- **Schemas** (`lumina/schemas/`): Contratos Pydantic de entrada/saída,
  validações customizadas e tipos compartilhados (ex: `AccessType`, enums).
- **Features** (`lumina/features/`): Módulos especializados e autocontidos
  para funcionalidades complexas (ex: `abnt_check/`, `template_check/`).
  Cada feature DEVE conter seus próprios schemas, lógica e prompts, sendo
  orquestrada por um service dedicado na camada de services.
- **Core** (`lumina/core/`): Infraestrutura transversal — database engine,
  settings, security/JWT, LLM provider, vectorstore, storage provider e
  cache/WebSocket manager. Configurações via `pydantic_settings.BaseSettings`
  carregadas do `.env`.

**Rationale**: A separação garante que mudanças em uma camada (ex: trocar o
ORM ou o provedor de LLM) não propaguem efeitos colaterais para camadas
adjacentes, e permite testes isolados por camada.

### II. Base de Conhecimento (Check Tree)

O sistema de auditoria documental é fundamentado em uma árvore hierárquica de
conhecimento normativo que DEVE ser mantida com integridade referencial
completa.

- **Hierarquia**: `Typification` → `Taxonomy` → `Branch`, com `Source`
  vinculada como referência normativa/legal de cada critério.
  - `Typification`: Perfil documental (ex: Edital de Obras, Artigo Científico).
  - `Taxonomy`: Seção ou tópico obrigatório (ex: Qualificação Técnica,
    Introdução).
  - `Branch`: Critério normativo específico com título, descrição e pergunta
    de verificação para a IA avaliar.
  - `Source`: Fonte legal que embasa os critérios (ex: Lei 14.133/21,
    NBR 6023).
- **Snapshots de Release (`Applied*`)**: Quando uma `DocumentRelease` é
  processada, a árvore ativa DEVE ser congelada em tabelas
  `AppliedTypification`, `AppliedTaxonomy`, `AppliedBranch` e
  `AppliedSource`. Resultados da avaliação (`fulfilled`, `score`, `feedback`,
  `references`, `presidio_mapping`) são persistidos no `AppliedBranch`.
- **Imutabilidade Histórica**: Uma vez criado, o snapshot de uma release
  NUNCA pode ser alterado — ele representa o estado exato da base de
  conhecimento no momento da avaliação.
- **CRUDs do Check Tree**: Endpoints em `routers/check_tree/` (projects,
  document_groups, project_documents, typifications, taxonomies, branches,
  sources) DEVEM validar integridade relacional e soft-delete antes de
  qualquer operação.

**Rationale**: A rastreabilidade normativa exige que cada avaliação de IA
seja reprodutível e auditável, mesmo que a árvore de conhecimento evolua
ao longo do tempo.

### III. Inteligência Artificial Responsável

Todo uso de IA no Lumina DEVE seguir práticas que garantam rastreabilidade,
reprodutibilidade, proteção de dados e contenção de custos.

- **RAG com Coordenadas Visuais**: O `CoordinateChunker`
  (`services/vector_service.py`) divide PDFs em blocos de até 500 caracteres,
  preservando coordenadas geométricas (`rects: [x0, y0, x1, y1]`) e número
  de página. Citações retornadas pela LLM (`Citation(chunk_id,
  text_snippet)`) DEVEM ser resolvidas para coordenadas via
  `resolve_citations`, permitindo highlight visual no documento original.
- **Anonimização LGPD (Presidio)**: Antes de qualquer texto ser vetorizado
  ou enviado a LLMs externas, ele DEVE passar pelo `PresidioAnonymizer`
  (`utils/PresidioAnonymizer.py`) para substituir CPFs, CNPJs, RGs,
  telefones, valores monetários, e-mails e outras PII por placeholders
  indexados (`<CPF_1>`, `<CNPJ_1>`). O mapeamento DEVE ser persistido
  nos metadados do chunk para desanonimização posterior.
- **Structured Output**: Respostas de LLMs DEVEM utilizar `structured_output`
  (Pydantic models ou `JsonOutputParser`) para garantir parsing
  determinístico. Schemas de saída residem em `schemas/ai.py` e nos schemas
  internos de cada feature.
- **Modelos e Prompts**: Prompts centralizados em `lumina/prompts.py` e
  templates Jinja2 em `features/prompts/`. Configuração de modelos em
  `core/llm.py` (LangChain `ChatOpenAI` para chat/RAG) e diretamente via
  OpenAI SDK nos módulos de features (`gpt-5.4` para ABNT, `gpt-4o` para
  visão de templates).
- **Avaliação por Lote**: O pipeline de release em
  `services/release_logic_service.py` executa avaliações via `chain.abatch`
  para processar múltiplos ramos do Check Tree em paralelo.
- **Conformidade Híbrida de Templates**: O módulo `features/template_check/`
  combina verificações determinísticas via PyMuPDF (margens, fontes,
  entrelinhas, cabeçalhos) com visão computacional (comparação visual de
  páginas), executadas concorrentemente via `asyncio.gather`.

**Rationale**: IA sem rastreabilidade é uma caixa preta inauditável.
A combinação de structured output + coordenadas visuais + anonimização
transforma a IA em ferramenta confiável para auditoria normativa.

### IV. Testes Orientados a Risco (NON-NEGOTIABLE)

A suíte de testes DEVE ser orientada a risco e comportamento — não a
cobertura cega de linhas. A metodologia completa está definida na skill
`.agents/skills/fastapi-testing-methodology/SKILL.md`.

- **Pirâmide de Testes (5 camadas)**:
  1. `tests/unit/services/` — Regras de negócio com mocks completos de
     repositórios (`AsyncMock`, `pytest-mock`).
  2. `tests/integration/repositories/` — Queries SQL com banco real via
     `session` fixture (savepoints).
  3. `tests/api/routers/` — Fluxo ponta a ponta com `TestClient`.
  4. Testes de segurança transversais (401/403) integrados em `tests/api/`.
  5. Testes de regressão nos diretórios pertinentes.
- **Matriz de Risco**: A profundidade DEVE ser proporcional à criticidade:
  - Crítico (auth, segurança, regras centrais): Unit + Repo + API + Security.
  - Alto (transações, mutações complexas): Unit + Repo + API.
  - Médio (consultas, filtros): Unit + Repo (se query complexa).
  - Baixo (CRUDs simples, health): API Integration.
- **Isolamento de Banco**: Testcontainers PostgreSQL 16 com DDL único por
  sessão e rollback via savepoints a cada teste. NUNCA rodar
  `create_all`/`drop_all` por teste individual.
- **Factories Modulares**: Massas de dados via Factory Boy em
  `tests/factories/`. NUNCA usar `uuid4()` soltos para FKs — sempre
  instanciar entidades reais.
- **IA em Testes — Separação Categórica**:
  1. *AI Integration Tests*: `FakeListChatModel` para validar fluxo sem
     tokens. Roda em `task test`.
  2. *AI Contract Tests*: Validação de schemas contra JSON corrompido.
     Roda em `task test`.
  3. *AI Evaluation*: Chamadas reais a LLMs com golden datasets
     (`tests/ai/evaluation/datasets/`). Marcado com `@pytest.mark.ai`.
     Roda SOMENTE em `task test-ai`.
- **Guardrail de Cobertura**: Mínimo de 80% de cobertura geral.
  `models.py` e `schemas.py` só podem ser excluídos se forem estritamente
  declarativos.

**Rationale**: Testes que dependem de rede externa ou consomem tokens pagos
em CI/CD são instáveis e caros. A separação em 3 categorias de IA garante
que o CI seja rápido, determinístico e barato, enquanto a avaliação de
qualidade roda sob demanda.

### V. Simplicidade e Consistência de Código

Todo código DEVE seguir padrões de formatação e estilo consistentes,
verificáveis automaticamente.

- **Limite de 79 caracteres por linha** (PEP 8 / Ruff).
- **Aspas simples `'`** por padrão em todo o projeto.
- **Ruff** como linter e formatter únicos. Regras ativas:
  `['I', 'F', 'E', 'W', 'PL', 'PT']`.
- **Tipagem estática**: Todo parâmetro de função, retorno e variável
  relevante DEVE ser tipado. Schemas Pydantic para validação de entrada/saída
  nos routers.
- **Poetry**: Gerenciador exclusivo de dependências e ambiente virtual.
  NUNCA executar `python`, `pytest`, `alembic` ou `ruff` sem o prefixo
  `poetry run` ou sem ativar a virtualenv via `poetry shell`.
- **Migrações**: Geradas via `poetry run alembic revision --autogenerate`
  após qualquer alteração em `models.py`. Diretório `migrations/` excluído
  do linting.

**Rationale**: Consistência elimina debates de estilo nos PRs e permite
que ferramentas automatizadas garantam a qualidade sem intervenção humana.

### VI. Segurança e Privacidade por Padrão

- **Autenticação**: JWT (HS256) via `pyjwt` com hash de senhas Argon2
  (`pwdlib`). Tokens emitidos com expiração configurável.
- **Autorização**: Controle de acesso por documento via `AccessType` (owner,
  advisor, viewer). Validação em services antes de qualquer operação.
- **Soft Delete**: Todas as entidades com `AuditMixin` utilizam `deleted_at`
  em vez de exclusão física. Queries DEVEM filtrar `deleted_at.is_(None)`.
- **Audit Trail**: Operações críticas (CREATE, UPDATE, DELETE) DEVEM gerar
  registros em `audit_logs` via `audit_service`.
- **LGPD**: Dados pessoais NUNCA transitam para LLMs externas sem
  anonimização prévia via Presidio (Princípio III).

**Rationale**: Um sistema de auditoria normativa que não protege os dados
dos seus próprios usuários contradiz sua razão de existir.

### VII. Documentação Viva (MkDocs)

Toda especificação de feature elaborada pelo Spec Kit DEVE ser documentada
em linguagem acessível no diretório `docs/`, utilizando o MkDocs para
publicação.

- **Localização**: Arquivos Markdown em `docs/` na raiz do repositório.
- **Linguagem**: Próxima de um humano não-técnico. Evitar jargão de
  implementação; focar em "o que o sistema faz" e "por que". Utilizar
  diagramas Mermaid e exemplos concretos sempre que possível.
- **Sincronização**: Quando uma spec (`spec.md`) for criada ou atualizada
  via `/speckit-specify`, uma página correspondente DEVE ser criada ou
  atualizada em `docs/` com o resumo funcional da feature.
- **Estrutura sugerida por página**:
  1. Visão geral da feature (para que serve, qual problema resolve).
  2. Fluxo principal (passo a passo do usuário).
  3. Regras de negócio (em linguagem natural).
  4. Diagrama de fluxo ou arquitetura (Mermaid).
  5. Glossário de termos específicos (se necessário).
- **Publicação**: O MkDocs DEVE ser configurado para gerar a documentação
  acessível em `https://meirelesgc.github.io/lumina-back` (já configurado
  no `pyproject.toml`).

**Rationale**: Specs técnicas em `.specify/` são ótimas para agentes e
desenvolvedores, mas stakeholders e revisores precisam de uma visão
simplificada e navegável do sistema.

### VIII. Página HTML Funcional de Validação/Demo (NON-NEGOTIABLE)

Sempre que uma nova spec alterar ou adicionar comportamento observável no
backend, a implementação da spec DEVE incluir uma página HTML simples que
permita demonstrar e validar manualmente o comportamento implementado.

Esta página NÃO é um frontend de produto: trata-se de um artefato pragmático
de validação, documentação funcional e demonstração do backend.

- **Objetivos**:
  1. Permitir que o desenvolvedor valide manualmente se a spec funciona
     conforme esperado ponta a ponta.
  2. Servir como referência funcional para a equipe de frontend entender
     rapidamente quais endpoints, fluxos e retornos estão disponíveis.
  3. Permitir demonstrar a funcionalidade do backend em reuniões sem precisar
     de uma aplicação frontend completa.
- **Princípios de Implementação**:
  - **Funcionalidade sobre estética**: NUNCA investir tempo em design visual,
    responsividade avançada ou bibliotecas pesadas de componentes.
  - **Simplicidade**: HTML, CSS básico e JavaScript vanilla. Sem frameworks de
    frontend ou dependências externas pesadas.
  - **Autoexplicativa e Focada**: A página deve permitir entender
    imediatamente o que a spec faz, demonstrando estritamente o escopo da
    spec.
  - **Consumo Real**: A página consome diretamente os endpoints reais da API.
- **Serviço e Organização no Código**:
  - As páginas DEVEM ser servidas diretamente pelo FastAPI existente,
    aproveitando a montagem de estáticos em `lumina/demos/` (exposta em
    `/demos/<spec-name>/` ou `/spec/<spec-name>/`).
  - NUNCA criar um servidor ou serviço separado para servir as demos.
  - A demo atua como complemento funcional ao Swagger/ReDoc (Swagger define o
    contrato técnico; a demo exercita o fluxo interativo).
- **Autenticação**:
  - Reutilizar o mecanismo de autenticação existente do projeto (campos para
    informar credenciais/token na própria página de teste).
  - NUNCA implementar um sistema paralelo de autenticação e NUNCA persistir
    credenciais desnecessariamente.
- **Conteúdo Mínimo Esperado na Demo**:
  - Nome da spec e breve descrição funcional.
  - Entradas necessárias para os fluxos/casos de uso.
  - Botões/ações para disparar as requisições contra a API.
  - Exibição clara de respostas com sucesso e respostas com erro (payloads).
  - Estado antes/depois quando relevante para entender a operação.
  - Indicação explícita quando uma ação possui efeito real no banco de dados.
- **Isolamento Arquitetural e Lifecycle**:
  - Demos NÃO podem conter regras de negócio no HTML/JS — regras residem
    exclusivamente nos services/repositories do backend.
  - Nenhuma parte da aplicação de produção pode depender da existência da demo.
  - A demo DEVE poder ser removida no futuro sem nenhum impacto no sistema.
- **Segurança**:
  - NUNCA contornar validações, permissões, RBAC ou isolamento de dados para
    facilitar a demo.
  - NUNCA criar endpoints especiais que ignorem proteções reais apenas para a
    demonstração.
- **Definition of Done (DoD) para Novas Specs**:
  - [ ] Backend implementado e aderente à arquitetura em camadas.
  - [ ] Testes automatizados cobrindo a matriz de risco.
  - [ ] Página HTML de demo/validação criada em `lumina/demos/<spec-name>/`.
  - [ ] Página servida pelo próprio FastAPI existente.
  - [ ] Autenticação integrada ao mecanismo existente (se aplicável).
  - [ ] Critérios de aceitação da spec exercitáveis manualmente pela página.
  - [ ] Respostas e erros da API claramente visíveis na interface.
  - [ ] Sem regra de negócio duplicada no frontend da demo.
  - [ ] Demo restrita estritamente ao escopo da spec.
  - [ ] Demo pode ser removida sem afetar a aplicação principal.

**Rationale**: Swagger valida tipos e contratos, testes automatizados validam
invariantes lógicas, mas a página demo valida a experiência operacional
do backend e acelera a integração com equipes externas e stakeholders.

## Workflow de Desenvolvimento com Agentes

Regras que governam como agentes de IA (subagentes) DEVEM operar ao
desenvolver features complexas no Lumina Back.

- **Git Worktrees para Paralelização**: Ao iniciar uma tarefa complexa que
  pode ser decomposta em subtarefas independentes, o agente DEVE criar
  git worktrees separados (`git worktree add`) para permitir que subagentes
  trabalhem em paralelo sem conflitos de working tree.
  - Cada worktree DEVE partir de `develop` ou da branch de feature corrente.
  - O nome da branch do worktree DEVE seguir o padrão:
    `feature/<feature-name>/<subtask-name>`.
  - Ao finalizar, o agente DEVE informar o desenvolvedor para que ele
    faça o merge/attach manual da branch à `develop`. Agentes NUNCA
    fazem merge diretamente em `develop` ou `main`.
- **Subagentes para Tarefas Complexas**: Quando uma tarefa envolve múltiplos
  arquivos independentes ou camadas distintas (ex: repository + service +
  router + tests), o agente principal DEVE criar subagentes especializados
  para trabalhar em paralelo, cada um em seu worktree.
- **Atomicidade de Commits**: Cada subtarefa DEVE resultar em commits
  atômicos e auto-descritivos na branch do worktree. Mensagens de commit
  DEVEM seguir o padrão Conventional Commits (ex: `feat:`, `fix:`, `test:`,
  `docs:`).
- **Testes Antes de Entregar**: Nenhuma branch de worktree DEVE ser
  considerada pronta sem que `poetry run task test` passe com sucesso.
  Se a feature envolve IA, `poetry run task test-ai` DEVE ser executado
  separadamente e seu resultado relatado.
- **Cleanup**: Ao finalizar o trabalho, worktrees DEVEM ser removidos
  com `git worktree remove` para manter o repositório limpo.

## Stack Tecnológica e Infraestrutura

Definição canônica da stack. Qualquer adição ou substituição de tecnologia
DEVE ser proposta como emenda à constituição.

| Categoria | Tecnologia | Versão/Constraint |
|-----------|-----------|-------------------|
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
| Anonimização | Microsoft Presidio | ≥2.2.360 |
| Relatórios PDF | ReportLab | ≥4.4.4 |
| Storage | Local / S3 (aioboto3) | Configurável via `STORAGE_PROVIDER` |
| Notificações | Evolution API (WhatsApp) | v2.3.6 |
| Gerenciador | Poetry | ≥2.0.0 |
| Linter/Formatter | Ruff | ≥0.12.11 |
| Testes | Pytest + Testcontainers + Factory Boy | — |
| Tasks | Taskipy | ≥1.14.1 |
| CI/CD | GitHub Actions → AWS EC2 via SSH | — |
| Containerização | Docker + Docker Compose | — |

## Governance

Esta constituição é o documento normativo supremo do projeto Lumina Back.
Todas as práticas de desenvolvimento, revisão de código e decisões
arquiteturais DEVEM estar em conformidade com os princípios aqui
estabelecidos.

- **Supremacia**: Em caso de conflito entre esta constituição e qualquer
  outro documento (AGENTS.md, skills, READMEs), a constituição prevalece.
  O `AGENTS.md` DEVE ser mantido como guia operacional complementar,
  nunca contraditório.
- **Emendas**: Qualquer alteração a esta constituição DEVE ser:
  1. Proposta com justificativa técnica.
  2. Documentada no Sync Impact Report (comentário HTML no topo do arquivo).
  3. Versionada segundo SemVer:
     - MAJOR: Remoção ou redefinição incompatível de princípios.
     - MINOR: Adição de princípio ou expansão material de orientação.
     - PATCH: Clarificações, correções de texto, refinamentos não-semânticos.
- **Revisão de Compliance**: Todo PR DEVE ser verificado quanto à aderência
  aos princípios. Complexidade arquitetural que desvie dos princípios DEVE
  ser justificada explicitamente no PR.
- **Guia Operacional**: O `AGENTS.md` na raiz do repositório contém
  comandos essenciais e orientações de runtime para desenvolvedores e
  agentes. Ele complementa — mas não substitui — esta constituição.

**Version**: 1.1.0 | **Ratified**: 2026-08-31 | **Last Amended**: 2026-08-31
