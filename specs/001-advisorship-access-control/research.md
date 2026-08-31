# Research: Advisorship and Entity Access Control

## Context & Problem Statement

O Lumina Back implementou controle de acesso rigoroso para documentos (`/doc`) e orientações acadêmicas (`/advisorship`), permitindo isolamento de dados por usuário e compartilhamento supervisionado entre orientador e orientando. Contudo, os endpoints de projetos (`GET /project` e `GET /project-document/by-project/{id}`) permaneceram sem injeção de sessão (`CurrentUser`), expondo projetos globalmente.

Adicionalmente, a Constituição do Lumina Back (Princípio VIII) exige que toda spec possua uma página HTML funcional em `lumina/demos/<spec-name>/` servida diretamente pelo FastAPI para validação manual, demonstração e documentação funcional de contratos.

## Research Decisions

### Decision 1: Padrão de Isolamento e Scoping em Projetos

- **Decision**: Injetar `current_user: CurrentUser` em todos os endpoints de leitura e listagem de `lumina/routers/check_tree/projects.py` e `project_documents.py`.
- **Rationale**:
  1. Mantém simetria exata com o padrão arquitetural já estabelecido em `lumina/routers/docs/docs.py`.
  2. Garante que `project_service.get_projects` e `project_repo.list_all` filtrem por `Project.created_by == current_user.id` (ou por orientandos vinculados ativamente caso o usuário seja orientador).
  3. Impede que contas recém-criadas visualizem projetos ou documentos de terceiros.
- **Alternatives Considered**:
  - *Filtrar apenas no frontend*: Rejeitado categoricamente (falha de segurança grave; backend deve ser autoritativo).
  - *Tabela separada de permissões de projeto*: Rejeitado por complexidade desnecessária (o modelo `Project` já herda de `AuditMixin` e possui o campo `created_by`).

### Decision 2: Arquitetura da Página HTML de Demonstração (`/demos/advisorship/`)

- **Decision**: Criar a aplicação estática em `lumina/demos/advisorship/index.html` consumindo diretamente os endpoints REST da API via `fetch()` assíncrono com Vanilla JS e CSS moderno.
- **Rationale**:
  1. O FastAPI já possui o ponto de montagem `app.mount('/demos', StaticFiles(directory=DEMOS_DIR, html=True), name='demos')` configurado em `lumina/app.py`.
  2. Sem necessidade de build tools, frameworks pesados (React/Vue) ou servidores secundários (Princípio VIII).
  3. Permite autenticação rápida com inputs de login/senha ou geração automática de tokens para 3 personas de teste (Aluno, Orientador, Terceiro).
  4. Exibe em tempo real o status HTTP (200 OK vs 403 Forbidden), o JSON payload e o diagnóstico visual de isolamento.
- **Alternatives Considered**:
  - *Criar app React dentro de um subdiretório*: Rejeitado por violar o Princípio VIII da Constituição (proíbe complexidade de frontend e frameworks desnecessários para demos).
  - *Swagger UI*: Mantido para contratos técnicos, enquanto a demo atua como validação do fluxo interativo de múltiplas personas.

### Decision 3: Estratégia de Testes de Integração

- **Decision**: Expandir a suíte de testes em `tests/integration/` com `test_project_access_control.py` espelhando a matriz de testes de `test_doc_access_control.py`.
- **Rationale**:
  - Garante conformidade com o Princípio IV (Testes Orientados a Risco), validando:
    1. Conta nova lista 0 projetos.
    2. Usuário B recebe 403/404 ao tentar ler projeto de Usuário A.
    3. Orientador ativo consegue visualizar projetos de seus orientandos.
    4. Ex-orientador com vínculo cancelado tem acesso revogado.
