## Context

Ver `proposal.md` para motivação e `specs/invitations/spec.md` para os requisitos de comportamento.

Atualmente, o roteador [`lumina/routers/invitations.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/routers/invitations.py) expõe endpoints para criação, listagem de enviados, consulta por token, aceite, rejeição e cancelamento. O modelo [`Invitation`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/models.py#L1521) já persiste `email`, `inviter_id`, `project_id`, `role_type`, `topic`, `status`, `expires_at` e campos de auditoria/soft delete. Não são necessárias alterações de schema ou migrações de banco.

## Goals / Non-Goals

**Goals:**
- Prover um endpoint `GET /invitations/pending-for-me` seguro, performático e tipado.
- Permitir que o estudante/orientando autenticado consulte em um único local todos os convites pendentes válidos direcionados ao seu e-mail.
- Retornar relacionamentos `inviter` e `project` carregados via `selectinload` para enriquecer a experiência do frontend.

**Non-Goals:**
- Não alterar as regras de negócio ou permissões de `GET /invitations` (que continuará focado nos convites enviados pelo usuário ou na visão global de admin).
- Não criar novas tabelas ou migrações no banco de dados.

## Decisions

### Decisão 1: Rota dedicada `GET /invitations/pending-for-me` vs Parâmetro em `GET /invitations`
- **Escolha**: Rota dedicada `GET /invitations/pending-for-me`.
- **Racional**: Separa claramente as responsabilidades de negócio: `GET /invitations` atende ao orientador monitorando os convites que ele emitiu (ou admin monitorando o sistema), enquanto `GET /invitations/pending-for-me` atende ao destinatário (geralmente aluno/orientando) verificando convites recebidos.
- **Alternativa descartada**: Adicionar um filtro `scope=received` no endpoint existente, o que aumentaria a complexidade de condicionais de autorização no service e causaria ambiguidade na documentação OpenAPI.

### Decisão 2: Ordem das rotas no FastAPI para evitar shadowing
- **Escolha**: Declarar `@router.get('/pending-for-me')` **antes** de `@router.get('/{token}')` em `lumina/routers/invitations.py`.
- **Racional**: No FastAPI, se uma rota parametrizada `/{token}` for registrada antes de `/pending-for-me`, o roteador interpretará a string `"pending-for-me"` como um token e encaminhará a requisição para a rota de consulta por token.

### Decisão 3: Schema de resposta
- **Escolha**: Reutilizar o schema existente `InvitationList` (`{"invitations": list[InvitationPublic]}`).
- **Racional**: Mantém total consistência com os demais contratos da API e permite ao frontend reaproveitar os mesmos tipos TypeScript gerados.

### Decisão 4: Filtragem de validade e expiração
- **Escolha**: Filtrar na query SQL no repositório `Invitation.status == 'PENDING'`, `Invitation.expires_at > func.now()`, `Invitation.deleted_at.is_(None)` e `func.lower(Invitation.email) == func.lower(current_user.email)`.
- **Racional**: Não transfere dados desnecessários (convites já expirados ou rejeitados) para a memória da aplicação.

## Risks / Trade-offs

- **[Roteamento / Shadowing]**: Se a rota for declarada abaixo de `/{token}`, o endpoint `/pending-for-me` nunca seria alcançado.
  - *Mitigação*: Posicionar a nova rota imediatamente antes de `/{token}` e adicionar testes de integração garantindo que `GET /invitations/pending-for-me` não caia na checagem de token.
