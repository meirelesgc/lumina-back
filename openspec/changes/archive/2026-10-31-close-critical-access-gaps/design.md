## Context

`UserCreate` herda `access_level` de `UserSchema`, e `user_service.create_user` grava esse valor. `UserPublic` e `UserUpdate` herdam o mesmo campo e precisam dele. O `delete_user` recebe só o id de quem chama, sem conferir papel. `AdminUser` existe em `lumina/core/dependencies.py`, mas nenhuma rota o usa. Veja `proposal.md` para a motivação.

## Goals / Non-Goals

**Goals:**

- Fechar as três rotas com a menor alteração possível, sem esperar a revisão de permissões.

**Non-Goals:**

- Criar o módulo central de políticas, que pertence à revisão de permissões.
- Proteger as demais rotas sem autenticação, incluindo releases e `/uploads`.
- Barrar token de usuário removido em `get_current_user`.
- Corrigir `UserUpdate.access_level`, cujo valor padrão `DEFAULT` rebaixa um `ADMIN` que omite o campo.
- Criar um comando que provisione o primeiro `ADMIN`.

## Decisions

**Tirar `access_level` do `UserCreate`.** O campo sai de `UserSchema` e entra em `UserPublic` e `UserUpdate`. O modelo `User` já tem `DEFAULT` como padrão, então `create_user` deixa de passar o valor e `invitation_service` deixa de enviá-lo. O Pydantic ignora campos extras, e o `POST /user` do front continua funcionando. A alternativa era manter o campo e sobrescrever no service, o que deixaria no contrato da API um campo sem efeito.

**Ignorar o campo em vez de rejeitar com `422`.** O design arquivado do cadastro no front envia `access_level: "DEFAULT"` fixo. Rejeitar quebraria esse cliente sem ganho de segurança.

**Autorizar o `DELETE` no service.** `delete_user` passa a receber `current_user`, como `update_user` e `change_password`, e repete a mesma comparação de dono e admin. O módulo de políticas da revisão substitui esses `if`s juntos.

**Usar `AdminUser` em `/audit-log`.** A dependência já responde `401` e `403`, e a rota não tem service. É o primeiro uso dela.

## Risks / Trade-offs

- [Contas `ADMIN` indevidas já existem em produção] → A mudança não as remove. O passo de operação abaixo lista essas contas para revisão humana.
- [Ambiente novo fica sem caminho HTTP para criar o primeiro `ADMIN`] → Quem opera o ambiente promove a conta por SQL. O comando de provisionamento fica fora desta mudança.
- [Um cliente externo cria admins por `POST /user`] → Não encontramos esse uso no front. Esse cliente passaria a receber contas `DEFAULT` e precisaria de um `PUT /user` feito por admin.

## Migration Plan

1. Publicar a mudança. Ela não altera o banco.
2. Listar as contas com `SELECT id, username, email, created_at FROM users WHERE access_level = 'ADMIN' AND deleted_at IS NULL` e revisar cada uma.
3. Para reverter, reverter o commit. Nenhum dado muda.
