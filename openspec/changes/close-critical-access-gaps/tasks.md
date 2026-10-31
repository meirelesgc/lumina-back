# Tasks

## 1. Cadastro sem privilégio

- [x] 1.1 Em `tests/routers/test_users.py`, escrever `test_visitante_nao_se_cadastra_como_admin` e ver o teste falhar antes da mudança: o `POST /user` anônimo com `access_level: ADMIN` hoje devolve `ADMIN`.
- [x] 1.2 No mesmo arquivo, escrever `test_visitante_se_cadastra_como_default` como guarda: passa desde o início.
- [x] 1.3 No mesmo arquivo, escrever `test_admin_promove_outra_conta` como guarda: passa desde o início e prova que `PUT /user` continua promovendo.
- [x] 1.4 Tirar `access_level` de `UserSchema`, declará-lo em `UserPublic` e `UserUpdate`, e remover o uso em `user_service.create_user` e `invitation_service`. Verificar que 1.1 a 1.3 passam e que `tests/integration/test_invitations.py` continua passando.

## 2. Remoção de usuário

- [x] 2.1 Em `tests/routers/test_users.py`, escrever `test_usuario_comum_nao_remove_outra_conta` e ver o teste falhar antes da mudança: hoje a rota responde `204`.
- [x] 2.2 No mesmo arquivo, escrever `test_admin_remove_outra_conta` como guarda: passa desde o início. `test_delete_user` já cobre o titular.
- [x] 2.3 Trocar o parâmetro de `user_service.delete_user` para `current_user`, conferir dono ou `ADMIN` e ajustar `lumina/routers/users.py`. Verificar que 2.1 e 2.2 passam.

## 3. Trilha de auditoria

- [x] 3.1 Criar `tests/api/routers/test_audit_logs_router.py` com os testes de visitante (`401`) e de usuário comum (`403`) e ver os dois falharem antes da mudança: hoje a rota responde `200`.
- [x] 3.2 No mesmo arquivo, escrever o teste do `ADMIN` como guarda: passa desde o início.
- [x] 3.3 Exigir `AdminUser` em `read_audit_logs`. Verificar que os testes do arquivo passam.

## 4. Fechamento

- [x] 4.1 Registrar em `docs/governanca.md` as três regras e corrigir, ali e em `docs/arquitetura-engenharia.md`, a linha que descreve `AccessType` como `owner, advisor, viewer`. Verificar com `grep` que a descrição antiga saiu.
- [x] 4.2 Rodar a suíte completa e registrar aqui o resultado que de fato rodou. Resultado em 2026-10-31, com o `pytest` da `.venv` e o Docker Desktop: 582 passaram, 13 foram pulados, nenhum falhou.

## Workflow follow-up

- Revisar as contas `ADMIN` de produção com a consulta do `design.md`.
- Commitar os artefatos em `docs(openspec): ...` e o código e os testes em `fix(...)`, em commits separados.
- Sincronizar a spec e arquivar a mudança depois da revisão.
