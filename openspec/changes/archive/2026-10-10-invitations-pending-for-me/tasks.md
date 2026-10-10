## 1. Repositório e Camada de Dados

- [x] 1.1 Implementar método `list_pending_by_email` em [`lumina/repositories/invitation_repo.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/repositories/invitation_repo.py) filtrando por e-mail (case-insensitive), status `PENDING`, `expires_at > func.now()`, `deleted_at IS NULL`, com `selectinload` para `inviter` e `project`, ordenando por `created_at.desc()`

## 2. Camada de Serviço e Roteador FastAPI

- [x] 2.1 Implementar função `list_pending_for_user` em [`lumina/services/invitation_service.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/services/invitation_service.py) invocando o repositório a partir do e-mail do `current_user`
- [x] 2.2 Declarar o endpoint `@router.get('/pending-for-me')` em [`lumina/routers/invitations.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/routers/invitations.py) posicionado **antes** de `@router.get('/{token}')`, protegido por `CurrentUser` e retornando `InvitationList`

## 3. Testes Automatizados e Validação

- [x] 3.1 Adicionar testes de integração em [`tests/integration/test_invitations.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/tests/integration/test_invitations.py) cobrindo:
  - Listagem bem-sucedida de múltiplos convites pendentes de professores/projetos distintos
  - Lista vazia quando não há convites pendentes
  - Não retorno de convites expirados, rejeitados, aceitos ou de outros usuários
  - Bloqueio com HTTP 401 para requisições não autenticadas
- [x] 3.2 Executar os testes automatizados com `poetry run task test` e validar conformidade de linting/estilo com `poetry run ruff check`
