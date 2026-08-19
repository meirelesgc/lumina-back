# Changelog — Lumina Back

Todas as principais modificações, melhorias, correções de segurança e refatorações realizadas no repositório.

---

## [Não Lançado / Semana Atual] — 19/08/2026

### 🎓 Nova Camada Organizacional & Relações de Orientação (N-N)
* **Modelo Relacional Contextual (`Advisorship`)**:
  * Substituição de cargos globais estáticos (`ANALYST`/`AUDITOR`) por relacionamentos contextuais N-N entre `User` (Orientador) $\leftrightarrow$ `User` (Orientando).
  * Suporte a papéis bidirecionais: um usuário pode atuar simultaneamente como orientador em certos projetos e orientando em outros.
  * Suporte a tipos de vínculo (`MAIN_ADVISOR`, `CO_ADVISOR`, `EVALUATOR`) e temas de pesquisa.
  * Integração direta com [`Project`](lumina/models.py#L1182-L1197) e [`DocumentGroup`](lumina/models.py#L1228-L1250) (sem amarras a semestres/períodos fixos).
* **Novos Endpoints para o Frontend (`/advisorship`)**:
  * `GET /advisorship/my-advisees`: **Visão do Orientador** com contagem de produções submetidas e revisões pendentes.
  * `GET /advisorship/advisees/{advisee_id}/documents`: Listagem das monografias e documentos do orientando.
  * `GET /advisorship/my-advisors`: **Visão do Orientando** listando todos os seus orientadores e projetos.
  * `GET /advisorship/documents/{doc_id}/academic-context`: Detalhes de autoria, orientadores e projeto associado.
  * `POST /advisorship`, `GET /advisorship`, `PUT /advisorship/{id}`, `DELETE /advisorship/{id}`: Gestão completa de vínculos com auditoria.
* **Migração de Banco (Alembic)**:
  * Criada a migration `0007_create_advisorships_table.py` com índices únicos parciais para registros ativos e FK em `documents.advisorship_id`.

### 🔒 Segurança & Controle de Acesso
* **Blindagem de Rotas de Usuário**:
  * Adicionada obrigatoriedade de autenticação (`current_user: CurrentUser`) nos endpoints de listagem e leitura de usuários (`GET /user` e `GET /user/{id}`), protegendo dados cadastrais contra acessos anônimos.

### 🧹 Remoção de Entidades Legadas (`Units`)
* **Eliminação de Unidades Físicas**:
  * Remoção completa da tabela `units` e das referências de coluna `unit_id` em `users` e `documents`.
  * Atualização da migration `0006_remove_units_and_unit_id_references.py`.

### 🧪 Testes & Metodologia (`fastapi-testing-methodology`)
* **Implementação da Pirâmide de Testes para Orientação**:
  * `AdvisorshipFactory` (`factory_boy`) para geração de dados em testes.
  * Testes Unitários de Serviço (`tests/unit/services/test_advisorship_service.py`) com isolamento via mocks.
  * Testes de Integração de Repositório (`tests/integration/test_advisorship_repo.py`) com persistência real em Savepoints.
  * Testes de Integração de API (`tests/api/routers/test_advisorship_router.py`) validando fluxos de autenticação, 201, 200, 401 e 403.
* **Total de Testes**: **100 testes automatizados passando** com 100% de sucesso.

---

## [Versão 3.0 / Rebranding & Infraestrutura]

### 🚀 Infraestrutura & CI/CD
* **Docker Compose & Deployment**: Correções no `docker-compose.yml` e automação de deploy via GitHub Actions.
* **Guia de Desenvolvimento**: Criação do `AGENTS.md` com padrões de ambiente Poetry, regras para testes de IA e lint com Ruff.
* **Otimização de Telemetria**: Remoção do OpenTelemetry para simplificação de stack.

### 📄 Documentos & IA
* **Versionamento de Documentos**: Suporte a histórico de versões via `DocumentRelease`.
* **Rastreamento de Contexto**: Rastreamento de posição de contexto e citações em documentos.
* **Rebranding do Projeto**: Transição do ecossistema de *IaEditais* para *Lumina*.
