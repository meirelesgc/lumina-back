## Why

Três rotas expõem o Lumina a qualquer visitante ou usuário comum. `POST /user` é pública e grava o `access_level` do corpo, então um anônimo se cadastra como `ADMIN`. `DELETE /user/{id}` aceita qualquer usuário autenticado. `GET /audit-log` não exige autenticação e entrega e-mail, telefone e ids de registros. Esta mudança fecha as três agora, antes da revisão completa de permissões.

## What Changes

- **BREAKING**: `POST /user` ignora `access_level` e cria a conta como `DEFAULT`. O cadastro continua público.
- **BREAKING**: `DELETE /user/{id}` passa a aceitar só o próprio usuário ou um `ADMIN`. Os demais recebem `403`.
- **BREAKING**: `GET /audit-log` passa a exigir `ADMIN`. Anônimo recebe `401` e usuário comum recebe `403`.
- `PUT /user` continua como a única forma de um `ADMIN` alterar o nível de acesso.

## Capabilities

### New Capabilities

- `access-control`: regras de autorização da API, começando pela criação de contas, pela remoção de usuários e pela leitura da trilha de auditoria.

### Modified Capabilities

Nenhuma.

## Impact

- **Rotas**: `POST /user`, `DELETE /user/{id}`, `GET /audit-log`.
- **Código**: `lumina/schemas/user.py`, `lumina/services/user_service.py`, `lumina/services/invitation_service.py`, `lumina/routers/users.py`, `lumina/routers/audit/audit_logs.py`.
- **Frontend**: nenhuma alteração. O campo `access_level` enviado no cadastro passa a ser ignorado, e o front não chama `/audit-log`.
- **Operação**: quem administra a produção precisa conferir as contas `ADMIN` atuais, porque o cadastro aberto pode ter criado contas indevidas.
- **Fora desta mudança**: as demais rotas sem autenticação, incluindo releases e `/uploads`, ficam para a revisão de permissões, que também absorve as issues #31 e #33. A issue #32 segue em trabalho próprio.
