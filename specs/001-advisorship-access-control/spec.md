# Feature Specification: Advisorship and Entity Access Control

**Feature Branch**: `001-advisorship-access-control`

**Created**: 2026-08-31

**Status**: Draft

**Input**: User description: "Retroativamente, gere a demonstração para a funcionalidade de orientações, e as regras de como o sistema bloqueia e mostra os documentos projetos e entidades no geral na plataforma. Teoricamente um orientador deveria conseguir ver os seus orientandos e aquilo em que esta envolvido. Isso também vale para o orientando."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Isolamento de Dados por Usuário Padrão (Priority: P1)

Como um pesquisador ou aluno cadastrado na plataforma, desejo que meus documentos, projetos e entidades criadas sejam visíveis apenas por mim por padrão, para que nenhuma outra conta não autorizada tenha acesso aos meus dados acadêmicos ou de pesquisa.

**Why this priority**: A privacidade e o isolamento de dados entre contas (tenants/usuários) é o requisito fundamental de segurança da plataforma. Qualquer vazamento de projetos ou documentos entre contas independentes quebra a integridade do sistema.

**Independent Test**: Criar duas contas independentes (`Usuário A` e `Usuário B`). `Usuário A` cria projetos e documentos. `Usuário B` autentica-se e lista seus projetos e documentos. `Usuário B` não deve ver nenhum item criado por `Usuário A`.

**Acceptance Scenarios**:

1. **Given** que `Usuário A` criou um projeto "Projeto Alfa" e um documento "Doc 1", **When** `Usuário B` (sem nenhum vínculo com `Usuário A`) autentica-se e lista seus projetos (`GET /project`) ou documentos (`GET /doc`), **Then** a resposta deve retornar apenas os itens de `Usuário B` (lista vazia para conta recém-criada).
2. **Given** que `Usuário A` possui um documento com identificador específico, **When** `Usuário B` tenta consultar diretamente os detalhes do documento por ID (`GET /doc/{id}`), **Then** o sistema deve recusar o acesso com código de erro `403 Forbidden`.
3. **Given** que `Usuário A` possui um projeto com ID específico, **When** `Usuário B` tenta consultar ou listar documentos desse projeto (`GET /project-document/by-project/{id}`), **Then** o sistema deve recusar o acesso com código `403 Forbidden` ou `404 Not Found`.

---

### User Story 2 - Visibilidade Compartilhada por Vínculo Ativo de Orientação (Priority: P1)

Como um orientador acadêmico com vínculo ativo, desejo visualizar a lista de meus orientandos, bem como consultar os projetos e documentos submetidos por eles, para que eu possa acompanhar, revisar e emitir relatórios sobre o progresso dos trabalhos. Do mesmo modo, o orientando deve visualizar seus orientadores vinculados.

**Why this priority**: É a regra de negócio central do módulo acadêmico: permitir a colaboração supervisionada sem abrir mão da privacidade perante terceiros.

**Independent Test**: Criar um orientador `Prof. Silva` e um orientando `Aluno João` com vínculo ativo (`status = ACTIVE`). O orientador deve conseguir listar o orientando, alternar o filtro de escopo de documentos/projetos (`scope = advisees` ou `scope = all`) e acessar o conteúdo dos documentos de `Aluno João`.

**Acceptance Scenarios**:

1. **Given** um vínculo de orientação ativo entre `Orientador` e `Orientando`, **When** o `Orientador` consulta a lista de orientandos (`GET /advisorship/my-advisees`), **Then** o sistema deve retornar os dados de `Orientando` com status ativo.
2. **Given** que o `Orientando` criou um documento ou projeto, **When** o `Orientador` lista documentos com escopo `scope=advisees` ou consulta diretamente o documento do orientando por ID, **Then** o sistema deve permitir a visualização completa do documento e seus detalhes acadêmicos (`GET /advisorship/documents/{doc_id}/academic-context`).
3. **Given** um vínculo de orientação ativo, **When** o `Orientando` consulta seus orientadores (`GET /advisorship/my-advisors`), **Then** o sistema deve listar o `Orientador` e o papel desempenhado (ex: `MAIN_ADVISOR` ou `CO_ADVISOR`).

---

### User Story 3 - Bloqueio Automático em Vínculos Inativos ou Cancelados (Priority: P2)

Como um pesquisador cujo vínculo de orientação foi encerrado ou cancelado, desejo que o ex-orientador deixe de ter acesso imediato aos meus novos projetos e documentos, preservando a autonomia da minha produção.

**Why this priority**: Evita vazamento de propriedade intelectual após encerramento de relações acadêmicas.

**Independent Test**: Cancelar um vínculo existente (`status = CANCELLED`). O ex-orientador não deve mais enxergar documentos do aluno em `scope=advisees` e qualquer tentativa de acesso por ID deve retornar `403 Forbidden`.

**Acceptance Scenarios**:

1. **Given** um vínculo de orientação com status `CANCELLED` ou `COMPLETED`, **When** o orientador busca documentos com `scope=advisees`, **Then** os documentos do ex-orientando não devem ser retornados na listagem.
2. **Given** um vínculo cancelado, **When** o orientador tenta obter os detalhes de um documento por ID (`GET /doc/{id}`), **Then** o sistema deve responder com `403 Forbidden`.

---

### User Story 4 - Demonstração Visual e Validação Manual (Priority: P2)

Como desenvolvedor, tech lead ou revisor de produto, desejo acessar uma página HTML interativa de demonstração servida pelo backend (`/demos/advisorship/`), para que eu possa validar manualmente a matriz de permissões (login com Conta A vs. Conta B vs. Orientador vs. Orientando) e demonstrar o funcionamento do controle de acesso em reuniões sem precisar do frontend de produção.

**Why this priority**: Atende ao Princípio VIII da Constituição do Lumina Back (Página HTML Funcional de Validação/Demo), fornecendo comprovação palpável e transparente do isolamento e das orientações.

**Independent Test**: Acessar `/demos/advisorship/` pelo navegador, efetuar login como diferentes personas e validar os fluxos de isolamento e compartilhamento diretamente na tela.

**Acceptance Scenarios**:

1. **Given** a aplicação FastAPI em execução, **When** o usuário acessa a rota `/demos/advisorship/`, **Then** o sistema deve carregar uma página HTML autoexplicativa com painéis de autenticação, listagem de orientandos, projetos e documentos por escopo.
2. **Given** credenciais válidas informadas na página de demo, **When** o usuário clica em "Verificar Meus Projetos" ou "Verificar Orientandos", **Then** a página deve exibir os payloads JSON reais retornados pela API e indicar visualmente se o isolamento está respeitado.

---

### Edge Cases

- **Orientador sem orientandos cadastrados**: Ao solicitar `scope=advisees`, a API deve retornar lista vazia de documentos sem gerar erros 500.
- **Usuário tenta orientar a si mesmo**: Tentativa de criar `Advisorship` onde `advisor_id == advisee_id` deve ser rejeitada com `400 Bad Request`.
- **Vínculos duplicados**: Tentativa de cadastrar o mesmo par de orientador/orientando ativo duas vezes deve resultar em conflito (`409 Conflict`).
- **Usuário Administrador**: Usuários com `access_level = ADMIN` podem visualizar qualquer documento ou projeto utilizando `scope=all`.
- **Documento com múltiplos orientadores (coorientação)**: Se o autor possuir orientador principal e coorientador ativos, ambos devem ter acesso de leitura aos documentos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE exigir autenticação (token JWT válido) em todos os endpoints de listagem e leitura de entidades de usuário (`/doc`, `/advisorship`, `/project`, `/project-document`).
- **FR-002**: A listagem de projetos (`GET /project`) DEVE filtrar estritamente os projetos pertencentes ao usuário autenticado (`created_by`), além de projetos pertencentes aos seus orientandos ativos quando aplicável.
- **FR-003**: A consulta de documentos de um projeto (`GET /project-document/by-project/{id}`) DEVE verificar se o usuário autenticado é o proprietário do projeto ou orientador ativo do proprietário antes de retornar a lista de documentos.
- **FR-004**: O sistema DEVE permitir a criação de vínculos de orientação (`POST /advisorship`) entre um usuário orientador e um usuário orientando, com definição de papel (`MAIN_ADVISOR`, `CO_ADVISOR`), tópico e status (`ACTIVE`, `COMPLETED`, `CANCELLED`).
- **FR-005**: O sistema DEVE fornecer o endpoint `GET /advisorship/my-advisees` para que orientadores consultem seus orientandos ativos.
- **FR-006**: O sistema DEVE fornecer o endpoint `GET /advisorship/my-advisors` para que orientandos consultem seus orientadores ativos.
- **FR-007**: A listagem de documentos (`GET /doc`) DEVE suportar os seguintes parâmetros de escopo de visibilidade:
  - `scope=mine` (padrão): Retorna apenas os documentos criados pelo usuário logado ou onde ele é editor explícito.
  - `scope=advisees`: Retorna exclusivamente documentos criados por orientandos vinculados ativamente ao usuário logado.
  - `scope=all`: Retorna a união dos documentos próprios e dos orientandos (ou todos do sistema para administradores).
  - `advisee_id=<UUID>`: Filtra documentos de um orientando específico sob supervisão do orientador.
- **FR-008**: O endpoint `GET /doc/{id}` DEVE permitir acesso de leitura apenas se o usuário for o criador (`created_by`), editor autorizado, orientador ativo do criador, ou administrador do sistema. Qualquer outro usuário DEVE receber `403 Forbidden`.
- **FR-009**: Operações de mutação em documentos (`PUT /doc`, `DELETE /doc/{id}`) e projetos (`PUT /project`, `DELETE /project/{id}`) DEVEM ser restritas ao proprietário do recurso ou editores com permissão de escrita explícita, impedindo que orientadores excluam trabalhos sem autorização.
- **FR-010**: O sistema DEVE fornecer o endpoint `GET /advisorship/documents/{doc_id}/academic-context` para expor o contexto acadêmico consolidado de um documento (autor/orientando, orientadores vinculados e projeto associado).
- **FR-011**: O sistema DEVE disponibilizar uma página HTML funcional de demonstração em `lumina/demos/advisorship/index.html` servida via FastAPI (`/demos/advisorship/`) que permita exercitar e comprovar a matriz de controle de acesso entre diferentes personas.
- **FR-012**: A página de demonstração NÃO DEVE conter regras de negócio próprias nem contornar restrições de segurança, consumindo diretamente as rotas oficiais da API com tokens JWT reais.

### Key Entities

- **User**: Usuário cadastrado na plataforma (pesquisador, orientador, orientando ou administrador) com identificador UUID, credenciais e nível de acesso (`access_level`).
- **Advisorship**: Vínculo de supervisão acadêmica relacionando um `advisor_id` (User) a um `advisee_id` (User), com atributos `role_type` (orientador principal ou coorientador), `topic`, `status` (`ACTIVE`, `COMPLETED`, `CANCELLED`) e timestamps de auditoria.
- **Project**: Agrupador temático de documentos de pesquisa, associado ao seu criador (`created_by`) e a um grupo de documentos.
- **ProjectDocument**: Vínculo entre um documento físico/digital e um projeto estruturado.
- **Document**: Entidade documental principal (artigo, monografia, edital) contendo metadados, versões de release e histórico de acessos/permissões (`AccessType`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das requisições de listagem de projetos e documentos para contas recém-criadas retornam apenas dados próprios (zero vazamento de entidades de terceiros).
- **SC-002**: 100% das tentativas de leitura ou modificação de documentos por usuários sem vínculo de propriedade ou orientação ativa são rejeitadas com código `403 Forbidden`.
- **SC-003**: Orientadores ativos conseguem listar e acessar 100% dos documentos e projetos de seus orientandos através dos filtros de escopo (`scope=advisees` e `scope=all`).
- **SC-004**: Desenvolvedores e revisores conseguem demonstrar e validar a matriz de acesso em menos de 2 minutos utilizando a página HTML de demo em `/demos/advisorship/`.

## Assumptions

- **Mecanismo de Autenticação**: O sistema utiliza o fluxo de autenticação JWT padrão da API (`POST /auth/token`) para autenticação de todas as requisições.
- **Soft Delete**: Entidades excluídas utilizam soft-delete via `AuditMixin.deleted_at` e são automaticamente ignoradas pelas consultas de visibilidade e orientação.
- **Permissão de Leitura vs. Edição**: Por padrão, o vínculo de orientação concede permissão de leitura sobre a produção do orientando; permissões de edição requerem inclusão como editor ou coautoria.
- **Existência Prévia**: A lógica de controle de acesso para `/doc` e `/advisorship` já se encontra implementada e testada na suíte de testes de integração (`test_doc_access_control.py`), necessitando de alinhamento análogo para `/project` e da respectiva página de demo.
