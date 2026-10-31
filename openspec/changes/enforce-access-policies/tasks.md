# Tasks

## 1. Base da política

- [ ] 1.1 Criar `tests/api/routers/test_route_protection.py` com `PUBLIC_ROUTES`, conferindo `get_current_user` na árvore de dependências de cada rota, e o teste de `401` em rota protegida. Ver o teste falhar antes da mudança, listando as rotas abertas.
- [ ] 1.2 Em `tests/routers/test_users.py`, escrever os testes de token de usuário removido, `GET /user`, `GET /user/{id}` e `PUT /user` sem `access_level`. Ver os testes falharem antes da mudança. O cenário de `ADMIN` listando usuários é guarda.
- [ ] 1.3 Criar `lumina/services/access_service.py`, barrar usuário removido em `get_current_user`, aplicar `dependencies` nos routers protegidos e ajustar `users.py` e `UserUpdate`. Verificar que 1.1 e 1.2 passam, com a suíte ajustada para autenticar as rotas de leitura.
- [ ] 1.4 Trocar os `if`s de `ADMIN` e dono em services por `access_service`. Verificar que `grep -rn "AccessType.ADMIN" lumina/services lumina/repositories` só devolve `access_service.py` e as listagens em SQL.

## 2. Orientação e convites

- [ ] 2.1 Em `tests/api/journeys/test_vinculo_de_orientacao.py`, escrever a jornada do orientando que escolhe orientador pela lista nova, encerra o vínculo e perde a ligação, e a do convite aceito após vínculo cancelado. Ver falhar antes da mudança.
- [ ] 2.2 Em `tests/api/routers/test_advisorship_router.py`, escrever os testes de criação direta, projeto de terceiro, reativação e ex-orientador, cobrindo vínculo ativo em outro projeto. Ver falharem antes da mudança os cenários de bloqueio. Os de sucesso são guardas.
- [ ] 2.3 Em `tests/integration/test_invitations.py`, escrever o teste de usuário comum enviando convite e ver falhar antes da mudança. Ajustar os testes atuais para convidar como `ADMIN`.
- [ ] 2.4 Criar `get_pair`, filtrar `ACTIVE` em `get_active_pair` e no caminho alternativo de `get_advisee_documents`, aplicar as regras em `advisorship_service` e `invitation_service`, e criar `GET /advisorship/advisors`. Verificar que 2.1 a 2.3 passam.

## 3. Documentos, mensagens e arquivos

- [ ] 3.1 Criar `tests/api/routers/test_document_access_router.py` com autor, editor, orientador ativo e estranho para releases, mensagens, conversas, assistente, PDFs, contexto acadêmico e `POST /doc` com documento de projeto alheio. Ver falharem antes da mudança os bloqueios. Os de sucesso são guardas.
- [ ] 3.2 Aplicar `access_service` em `routers/docs/releases.py`, `messages.py`, `chat.py`, `assistant.py`, `reports.py`, `message_service`, `report_service`, `doc_service` e `advisorship_service`. Verificar que 3.1 passa.
- [ ] 3.3 Criar `tests/api/routers/test_uploads_router.py` para release, ícone, projeto, arquivo sem dono e caminho com `..`. Ver falharem antes da mudança os bloqueios.
- [ ] 3.4 Trocar `StaticFiles` pela rota protegida em `/uploads`. Verificar que 3.3 passa.
- [ ] 3.5 Criar `tests/api/routers/test_websocket_access.py` e ver falhar antes da mudança o cenário sem acesso. Criar `get_current_ws_user` e aplicá-lo nos dois WebSockets. Verificar que o teste passa.

## 4. Configurador e sistema

- [ ] 4.1 Criar `tests/api/routers/test_admin_routes.py`, parametrizado com cada rota de escrita do configurador, sugestões, templates, `/stats` e `/system-settings`, esperando `403` para `DEFAULT` e nada gravado. Ver falhar antes da mudança. Incluir leitura de `DEFAULT` em `/document-group` como guarda.
- [ ] 4.2 Trocar `CurrentUser` por `AdminUser` nessas rotas e ajustar os testes atuais para autenticar como `ADMIN`. Verificar que 4.1 passa.
- [ ] 4.3 Em `tests/api/routers/test_conformity_access.py`, escrever os testes de leitura, listagem e remoção por dono e por outro usuário. Ver falhar antes da mudança.
- [ ] 4.4 Filtrar por `created_by` em `abnt_conformity_service` e `template_conformity_service` e seus repositories. Verificar que 4.3 passa.

## 5. Provisionamento e documentação

- [ ] 5.1 Criar `tests/unit/scripts/test_promote_admin.py` com conta existente e e-mail inexistente, e ver falhar antes da mudança. Criar `lumina/scripts/promote_admin.py`. Verificar que o teste passa.
- [ ] 5.2 Atualizar `docs/orientacao-academica.md` com as regras de vínculo e a leitura de `ADMIN`, e `docs/governanca.md` com a política. Verificar com `grep` que `POST /advisorship` descreve a regra nova.

## 6. Fechamento

- [ ] 6.1 Rodar a suíte completa e registrar aqui o resultado que de fato rodou.

## Workflow follow-up

- Enviar o documento ao time do front antes do deploy.
- Rodar a consulta de vínculos do `design.md` depois do deploy.
- Commitar os artefatos em `docs(openspec): ...` e o código e os testes em `feat(access): ...`, em commits separados.
- Citar `Closes #31`, `Closes #32` e `Closes #33` no PR.
- Sincronizar a spec e arquivar a mudança depois da revisão.
