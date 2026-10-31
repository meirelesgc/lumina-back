# Tasks

## 1. Migração

- [x] 1.1 Criar `tests/integration/test_remove_kanban_migration.py`, no padrão de `test_branch_section_scope_migration.py`, com documento de dois históricos e dois releases, e contas `AUDITOR`, `ANALYST` e `ADMIN`. Ver o teste falhar antes da mudança, porque a revisão ainda não existe. O teste precisa provar: releases ligados ao documento, `document_histories` removida, colunas de `project_documents` removidas, níveis convertidos e `downgrade` recriando a estrutura.
- [x] 1.2 Criar a revisão Alembic descrita no `design.md`, a partir da cabeça atual da `main` (`c4d1e7a92b36`). Verificar que 1.1 passa e que `alembic heads` mostra uma só cabeça.

## 2. Release ligado ao documento

- [x] 2.1 Em `tests/integration/test_release_pipeline.py` e `tests/integration/test_report_export.py`, trocar a montagem por `DocumentRelease(document_id=...)`. Ver os testes falharem antes da mudança.
- [x] 2.2 Em `tests/api/routers/test_document_contract_router.py`, escrever os testes de `GET /doc/{id}` sem `history`, de release sem `history_id` e de dois documentos com o mais antigo primeiro em `GET /doc`. Ver falharem antes da mudança os dois primeiros. O terceiro é guarda e passa desde o início.
- [x] 2.3 Remover `DocumentHistory` e `DocumentStatus` de `lumina/models.py` e dos schemas, criar `document_id` e `Document.releases`, e ajustar `routers/docs/releases.py`, `routers/docs/chat.py`, `routers/stats.py`, `services/ai/pipeline.py`, `services/report_service.py`, `services/notification_service.py`, `services/doc_service.py`, `repositories/doc_repo.py`, `repositories/message_repo.py`, `repositories/release_repo.py` e `repositories/tree_repository.py`, e apagar `repositories/releases_repository.py`, que nenhum módulo importava. Verificar que 2.1 e 2.2 passam e que `grep -rn "DocumentHistory\|DocumentStatus\|history_id" lumina` não devolve nada.

## 3. Kanban

- [x] 3.1 No arquivo de 2.2, escrever o teste de `PUT /doc/{id}/status/completed` com `404` e ver o teste falhar antes da mudança. Remover `test_characterization_kanban_flow` e o `history` de `test_affected_flows_characterization.py`.
- [x] 3.2 Apagar `routers/docs/kanban.py`, `services/kanban_service.py` e `repositories/kanban_repo.py`, tirar o router de `lumina/app.py`, e remover de `audit_service` o `STATUS_TRANSLATION` e os ramos de `history`. Verificar que 3.1 passa.

## 4. Documento de projeto e métrica

- [x] 4.1 Em `tests/api/routers/test_document_contract_router.py`, escrever o teste de `POST /project-document` com `status` e resposta sem `status` e `sent_to_kanban`. Ver o teste falhar antes da mudança.
- [x] 4.2 Remover `status` e `sent_to_kanban` do modelo, dos schemas de `ProjectDocument` e de `doc_service` e `project_document_service`. Verificar que 4.1 passa.
- [x] 4.3 Em `tests/api/routers/test_advisorship_router.py`, escrever o teste do cartão com `total_documents` e sem `pending_reviews`, e ajustar `tests/unit/services/test_advisorship_service.py`. Ver o teste falhar antes da mudança.
- [x] 4.4 Remover `pending_reviews` do schema e do service, e reduzir `get_advisee_document_metrics` à contagem total. Verificar que 4.3 passa.

## 5. Níveis de acesso

- [x] 5.1 Em `tests/routers/test_users.py`, escrever o teste de `PUT /user` com `AUDITOR` e `422`, e ver o teste falhar antes da mudança. `test_admin_promove_outra_conta` continua como guarda.
- [x] 5.2 Remover `ANALYST` e `AUDITOR` de `AccessType`. Verificar que 5.1 passa, que `grep -rn "AUDITOR\|ANALYST" lumina` não devolve nada e que `entrypoint.sh` aplica as migrações antes de subir a API.

## 6. Documentação

- [x] 6.1 Atualizar `docs/governanca.md` com os dois níveis. Verificar com `grep` que `ANALYST` saiu de `docs/`.
- [x] 6.2 Confirmar a compatibilidade do `lumina-front` sem alterá-lo. Numa cópia local descartada, tirar `history`, `sent_to_kanban` e o `status` de documento de projeto dos tipos não gerou erro no `next build`, o que mostra que nenhuma tela lê esses campos. `pending_reviews` usa `?? 0`.

## 7. Fechamento

- [x] 7.1 Rodar a suíte completa e registrar aqui o resultado que de fato rodou. Resultado em 2026-10-31, depois do merge da `main` atual, com o `pytest` da `.venv` e o Docker Desktop: 561 passaram, 9 foram pulados, nenhum falhou.

## Workflow follow-up

- Fazer o backup e seguir o plano de migração do `design.md` no deploy.
- Commitar os artefatos em `docs(openspec): ...` e o código e os testes em `refactor(...)`, em commits separados.
- Sincronizar as specs e arquivar a mudança depois da revisão.
