## Context

`AdminUser` é usado só em `/audit-log`. As checagens de `ADMIN` estão repetidas em services e repositories, e `has_document_access` e `has_project_access` ficam em repositories. `docs/governanca.md` proíbe `HTTPException` em repositories, e os services já levantam esse erro.

`ADMIN` significa orientador por decisão registrada na mudança arquivada `restrict-advisor-candidates-to-admins` do front. Assim, orientadores leem todos os documentos, e o isolamento protege usuários `DEFAULT` entre si.

`ix_uq_advisorship_active` é único para vínculos não removidos, sem olhar `status`. `get_active_pair` também ignora `status`, o que causa a #32 e o aceite de convite sem efeito.

O `WebSocket /doc/message/{doc_id}/ws` já exige o cookie, mas não confere acesso ao documento. `/ws/{subscriber_id}`, `/stats`, `/system-settings`, `/export`, `/doc/{id}/assistant/chat` e `/chat` não têm chamada no front. Veja `proposal.md` para a motivação.

## Goals / Non-Goals

**Goals:**

- Fazer uma rota nova falhar nos testes quando não declarar sua regra.
- Reunir as regras em um único módulo.

**Non-Goals:**

- Separar `ADMIN` de orientador.
- Tabela de permissões ou biblioteca de autorização.
- Remover rotas sem uso no front.
- Mudar o banco.

## Decisions

**Criar `lumina/services/access_service.py`.** O módulo reúne `is_admin`, as consultas `can_read_document`, `can_edit_document`, `can_delete_document`, `can_read_project` e os `ensure_*`, que levantam `403`. `doc_repo.has_document_access` e `project_repo.has_project_access` viram consultas puras chamadas por ele, e os `if`s espalhados são trocados por essas funções. As listagens em `doc_repo.list_all` e `project_repo.list_all` continuam com o filtro em SQL.

**Declarar a regra no router.** Routers só com rotas protegidas recebem `dependencies=[Depends(get_current_user)]`. Rotas do configurador usam `AdminUser`. Os routers mistos (`auth`, `users`, `invitations`) declaram rota a rota. Alternativa rejeitada: middleware global, que perde a resposta `401` do `Security` e esconde a regra do OpenAPI.

**Teste percorre `app.routes`.** `tests/api/routers/test_route_protection.py` tem a lista `PUBLIC_ROUTES` e confere, na árvore de dependências de cada rota, que `get_current_user` aparece. Uma rota nova sem regra quebra esse teste.

**Separar `get_pair` de `get_active_pair`.** `get_pair` mantém a busca sem `status`, necessária para respeitar o índice único. `get_active_pair` passa a filtrar `ACTIVE`. `create_advisorship` e `accept_invitation` usam `get_pair`: vínculo ativo responde `409` ou reaproveita, vínculo encerrado volta a `ACTIVE`. Alternativa rejeitada: alterar o índice, que exigiria migração sem ganho.

**Trocar `StaticFiles` por rota em `/uploads`.** A rota mantém a URL, resolve o caminho dentro de `UPLOAD_DIRECTORY` e procura o dono: `DocumentRelease`, `ProjectDocument`, `UserImage`, `Source`. Arquivo sem dono conhecido, como upload de sugestão de árvore, exige `ADMIN`. O front baixa PDFs com `withCredentials`, e `<img>` envia o cookie pelo proxy na mesma origem.

**`GET /advisorship/advisors` traz o e-mail.** A tela de onboarding mostra o e-mail do orientador, então a troca no front se limita à URL e ao fim do filtro.

**Filtrar resultados de conformidade por `created_by`.** `doc_id` é texto sem chave estrangeira, e `created_by` é gravado em todo resultado. Um editor deixa de ver o resultado criado pelo autor.

**WebSockets.** `get_current_user` recebe `Request`, que não existe em WebSocket. Uma nova `get_current_ws_user` lê o mesmo cookie e fecha a conexão com código `1008` sem token válido ou sem acesso ao documento.

**Comando `lumina/scripts/promote_admin.py`.** Segue o formato de `seed_demo.py` e recebe o e-mail como argumento.

## Risks / Trade-offs

- [Onboarding quebra até o front trocar a rota] → Aceito. O documento para o time do front registra a troca e a ordem de publicação.
- [Vínculos com orientador `DEFAULT` já existentes] → Continuam valendo, mas o orientador deixa de reativá-los. A consulta abaixo lista esses casos.
- [Editor perde resultados de conformidade do autor] → Aceito, porque o dono do resultado é o único campo confiável hoje.
- [Rota de `/uploads` mais lenta que `StaticFiles`] → A consulta usa `file_path`, e o volume é baixo. Sem índice nesta mudança.

## Migration Plan

1. Avisar o time do front com o documento.
2. Publicar o back. Não há migração.
3. Revisar os vínculos com `SELECT a.id, u.email FROM advisorships a JOIN users u ON u.id = a.advisor_id WHERE a.status = 'ACTIVE' AND a.deleted_at IS NULL AND u.access_level <> 'ADMIN'`.
4. Reverter significa reverter o commit, porque nenhum dado muda.
