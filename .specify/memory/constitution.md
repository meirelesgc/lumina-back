<!-- Sync Impact Report
Version Change: 1.2.0 -> 1.3.0
Modified Principles:
- None renamed; content of existing IV principles preserved verbatim.
Added Sections/Principles:
- V. AI Pipeline Integrity & Data Sovereignty (new Core Principle, promoted from Additional Constraints + expanded)
- Additional Constraints: new "Observabilidade e Logging Estruturado" rule
- Additional Constraints: new "Gestão de Segredos" rule
- Development Workflow: new "Integração com Spec-Kit" rule (item 4 in Quality Gates + standalone)
- Governance: new "Cadência de Revisão de Conformidade" rule
Removed Sections: None
Follow-up TODOs: None — all placeholders resolved.
-->

# Lumina Back Constitution

## Core Principles

### I. Code Quality & Architecture Integrity
- **Separação de Responsabilidades**: A arquitetura do sistema MUST manter divisão clara
  entre camadas: `routers/` (validação de entrada/saída e camada HTTP), `services/` (regras
  de negócio e orquestração de domínio), `repositories/` (abstração de persistência e
  consultas) e `models.py` (modelos relacionais SQLAlchemy).
- **Tipagem Estática e Schemas Pydantic**: Todas as requisições e respostas de endpoints
  MUST ser estritamente tipadas e validadas com schemas Pydantic.
- **Estilo e Formatação Rigorosa**: O código-fonte MUST respeitar o limite de linha de
  **79 caracteres** e utilizar **aspas simples** (`'`) por padrão (estilo PEP 8 / Ruff).
  O linter e o formatador DEVEM ser validados com `poetry run ruff check --fix` e
  `poetry run ruff format`.
- **Uso Obrigatório do Poetry**: Todas as ferramentas do ecossistema (`python`, `pytest`,
  `alembic`, `ruff`, etc.) MUST ser executadas exclusivamente através do Poetry
  (`poetry run <comando>`). O uso de binários globais é estritamente proibido.
- **Higiene de Versionamento (Git)**: Novas implementações e correções MUST ser feitas em
  branches isoladas (ou *git worktrees*). Commits intermediários de rascunho (*WIP*) MUST
  passar por *squash/rebase* antes do merge para manter um histórico atômico e semântico.

### II. Testing Standards & Risk-Driven Verification
- **Foco em Comportamento e Matriz de Risco**: A suíte de testes automatizados MUST
  priorizar a validação de cenários de risco e comportamentos críticos de negócio em vez de
  perseguir cegamente percentuais brutos de cobertura de linhas, seguindo a metodologia
  `fastapi-testing-methodology`.
- **Isolamento de Banco de Dados com Savepoints**: Testes com persistência MUST utilizar
  `Testcontainers` com transações aninhadas (*Savepoints* / Nested Transactions). É
  terminantemente PROIBIDO executar `create_all` ou `drop_all` em cada teste individual.
- **Segregação Estrita de Testes de IA**:
  - Testes que realizam chamadas reais a APIs de LLMs externas (com consumo de tokens) MUST
    ser marcados obrigatoriamente com `@pytest.mark.ai` e executados apenas sob demanda
    (`poetry run task test-ai`).
  - Testes de rotina e CI/CD (`poetry run task test`) MUST executar apenas testes
    determinísticos, utilizando mocks (`unittest.mock.AsyncMock`, `FakeListChatModel`).
- **Refatoração Segura**: Qualquer grande refatoração estrutural MUST ser precedida por
  Testes de Caracterização (conforme `safe-refactoring-methodology`) para assegurar a
  preservação de comportamento regressivo.

### III. User Experience & API Design Consistency
- **Semântica e Constantes HTTP**: A API MUST retornar códigos de status HTTP semânticos
  utilizando as constantes do framework (ex.: `fastapi.status.HTTP_200_OK`,
  `HTTP_201_CREATED`, `HTTP_403_FORBIDDEN`), sendo proibido o uso de números literais soltos
  no código.
- **Tratamento de Erros Human-Friendly & Seguro**: Exceções de domínio e validações DEVEM
  retornar mensagens de erro claras, consistentes e orientadas à resolução (`detail`), NUNCA
  expondo *stack traces*, credenciais ou detalhes internos de infraestrutura em ambiente
  produtivo.
- **Consistência de Contratos e Visibilidade**: A listagem e manipulação de recursos MUST
  seguir regras previsíveis de escopo e permissão (ex.: autor `created_by`, colaboradores
  `editors`, orientadores via `scope='mine'|'advisees'|'all'`), mantendo documentação
  amigável e alinhada com as necessidades do frontend.
- **Evolução Não Disruptiva de APIs**: Mudanças estruturais em endpoints ou contratos de
  dados DEVEM manter retrocompatibilidade sempre que possível ou prover guias de migração
  claros antes de depreciações.

### IV. Performance & Asynchronous Efficiency
- **I/O Não Bloqueante (Async Native)**: Todas as operações de entrada e saída — incluindo
  consultas ao banco de dados via SQLAlchemy 2.0, requisições de rede, cache em Redis e
  mensageria RabbitMQ — MUST ser implementadas de forma assíncrona (`async`/`await`),
  impedindo bloqueios no *event loop* do FastAPI.
- **Eficiência de Consultas (Anti-N+1)**: Consultas a relacionamentos no banco de dados
  DEVEM utilizar carregamento explícito otimizado (`selectinload` ou `joinedload`), evitando
  overhead de consultas em cascata.
- **Processamento Otimizado de IA e Documentos**: Pipelines de extração de texto (PDFs,
  DOCX) e anonimização de dados com Presidio DEVEM gerenciar streams e memória
  eficientemente, delegando tarefas pesadas para filas de processamento em background quando
  a latência síncrona inviabilizar a resposta rápida do endpoint.
- **Performance da Suíte de Testes**: A suíte de testes deve ser mantida ágil e
  paralelizável, recomendando o uso de `pytest-xdist` com a estratégia `--dist loadscope`
  para execução distribuída sem concorrência destrutiva de fixtures.

### V. AI Pipeline Integrity & Data Sovereignty
- **Anonimização Obrigatória Antes de LLMs**: Todo dado sensível processado por módulos de
  inteligência artificial MUST passar por pipelines de análise e anonimização via Presidio
  Analyzer/Anonymizer **antes** de qualquer transmissão a provedores externos de LLM
  (OpenAI, etc.). A omissão desta etapa constitui violação crítica.
- **Determinismo e Rastreabilidade de Pipelines**: Cadeias LangChain e pipelines de IA MUST
  ser projetados de forma que cada etapa seja rastreável e auditável. Parâmetros de
  temperatura, modelos e versões DEVEM ser explicitamente configuráveis via variáveis de
  ambiente — nunca *hardcoded*.
- **Fallback e Resiliência**: Integrações com APIs de LLM externas DEVEM implementar
  estratégias de fallback (ex.: retry com *exponential backoff*, circuit breaker) para
  garantir degradação graciosa em caso de indisponibilidade do provedor.
- **Segregação de Dados de Treinamento**: Dados de usuários finais MUST NOT ser utilizados
  para fine-tuning ou retreinamento de modelos sem consentimento explícito documentado e
  rastreável. Este princípio prevalece sobre qualquer otimização de desempenho.

## Additional Constraints & AI Guidelines

- **Versionamento de Banco com Alembic**: Qualquer alteração em modelos ORM
  (`lumina/models.py`) MUST ser acompanhada por uma migração gerada e versionada no Alembic
  (`poetry run alembic revision --autogenerate -m "descricao"`). Migrations sem
  `downgrade` implementado DEVEM ser explicitamente justificadas.
- **Observabilidade e Logging Estruturado**: Todos os serviços e handlers de exceção MUST
  emitir logs estruturados (JSON ou formato parseável) contendo: timestamp, nível
  (`INFO`/`WARNING`/`ERROR`), `request_id` (quando aplicável), módulo de origem e mensagem
  descritiva. Logs em produção NUNCA devem conter dados pessoais identificáveis (PII) ou
  segredos de autenticação.
- **Gestão de Segredos**: Credenciais, chaves de API e *connection strings* MUST ser
  carregadas exclusivamente via variáveis de ambiente (`.env` local, secrets manager em
  produção). É estritamente PROIBIDO *commitar* segredos no repositório Git.

## Development Workflow & Quality Gates

- **Quality Gates de PR**: Nenhum código deve ser integrado à branch principal sem:
  1. Sucesso na execução completa dos testes rápidos (`poetry run task test`).
  2. Conformidade total no linting e formatação com Ruff
     (`poetry run ruff check` e `poetry run ruff format --check`).
  3. Validação dos schemas de entrada e saída e status codes HTTP.
  4. Ausência de segredos ou PII detectáveis no diff do PR.
- **Análise de Cobertura**: Relatórios de cobertura em HTML (`poetry run task cov`) devem
  ser consultados para garantir que fluxos críticos e regras de autorização não possuam
  lacunas de teste.
- **Integração com Spec-Kit**: Novas funcionalidades MUST seguir o fluxo do Spec-Kit:
  `speckit-specify` → `speckit-plan` → `speckit-tasks` → `speckit-implement`. Desvios do
  fluxo requerem justificativa documentada no PR. A validação de conformidade com esta
  Constituição (`speckit-analyze`) SHOULD ser executada antes de qualquer merge.

## Governance

- **Supremacia da Constituição**: Esta Constituição sobrepõe todas as práticas não
  documentadas e acordos informais do repositório.
- **Procedimento de Emenda**: Qualquer alteração ou inclusão de novos princípios requer
  justificativa técnica documentada, revisão em PR e aprovação explícita dos mantenedores.
- **Versionamento Semântico da Governança**:
  - **MAJOR**: Remoção ou reformulação incompatível de princípios fundamentais.
  - **MINOR**: Inclusão de novos princípios, seções ou expansão significativa de diretrizes.
  - **PATCH**: Correções textuais, ajustes de formatação ou refinamentos de redação sem
    alteração semântica.
- **Cadência de Revisão de Conformidade**: A conformidade com esta Constituição DEVE ser
  verificada ativamente a cada ciclo de release. Recomenda-se a execução de
  `speckit-analyze` ao final de cada sprint para identificar desvios estruturais acumulados.
  Violações identificadas MUST ser registradas como issues e priorizadas no próximo ciclo.
- **Revisão de Conformidade de Tarefas**: Todas as tarefas de especificação, planejamento e
  Pull Requests no Spec-Kit devem ser validadas contra estes princípios antes da integração.

**Version**: 1.3.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-22
