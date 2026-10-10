## Why

Atualmente, o endpoint de listagem `GET /invitations` restringe usuários não-administradores a visualizarem apenas os convites que eles próprios emitiram (`inviter_id == current_user.id`). Quando um estudante ou orientando recebe múltiplos convites de diferentes professores ou para diferentes projetos em seu e-mail, não há nenhuma rota autenticada que permita consultar quais convites estão pendentes de resposta para ele. O usuário fica dependente exclusivamente de links com tokens recebidos por e-mail, sem visibilidade no dashboard da aplicação.

## What Changes

- Adicionar novo endpoint autenticado `GET /invitations/pending-for-me` que lista todos os convites com status `PENDING` direcionados ao e-mail do usuário autenticado (`current_user.email`), que ainda não expiraram e não foram excluídos logicamente (`deleted_at IS NULL`).
- Carregar relacionamentos necessários na consulta (dados de quem convidou `inviter` e dados do projeto `project`, se houver) para exibição rica no frontend.
- Ordenar os convites pendentes por data de criação decrescente (`created_at DESC`).
- Adicionar testes de integração cobrindo a listagem de múltiplos convites pendentes para o usuário logado, isolamento entre contas e exclusão de convites expirados/recusados/cancelados.

## Capabilities

### New Capabilities
- `invitations`: Gerenciamento e consulta de convites de orientação acadêmica, incluindo listagem de pendências recebidas pelo usuário autenticado.

### Modified Capabilities
<!-- Nenhuma capability existente está sendo modificada -->

## Impact

- **APIs**: Novo endpoint `GET /invitations/pending-for-me` no router [`lumina/routers/invitations.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/routers/invitations.py).
- **Services & Repositories**: Novos métodos em [`lumina/services/invitation_service.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/services/invitation_service.py) e [`lumina/repositories/invitation_repo.py`](file:///home/jaspion/Fiocruz/Lumina/lumina-back/lumina/repositories/invitation_repo.py).
- **Frontend**: O frontend passa a ter um endpoint para alimentar centros de notificação, dashboards de pendências e telas de aceite direto de múltiplos convites sem depender exclusivamente dos links de e-mail.
- **Breaking Changes**: Nenhuma quebra de contrato existente; puramente aditivo.
