## Context

`DocumentRelease.history_id` aponta para `document_histories`, e o documento só é alcançado por essa tabela. Pipeline de IA, relatórios, stats, chat, mensagens e `tree_repository` fazem esse caminho. `doc_repo.list_all` faz join obrigatório com o último histórico e ordena por status. Só `doc_service.create_doc` e `kanban_service` criam linhas de histórico. Veja `proposal.md` para a motivação.

O front não lê o conteúdo de `history`, não usa `history_id`, não lê `ProjectDocument.status` e trata `pending_reviews` com `?? 0`. Ele envia `status: "PENDING"` em `POST /project-document`.

## Goals / Non-Goals

**Goals:**

- Remover Kanban, `AUDITOR`, `ANALYST`, `DocumentHistory`, `DocumentStatus` e `ProjectDocument.status` sem perder releases.

**Non-Goals:**

- Alterar `Project.status` e `processing_status`, que têm outro significado.
- Reescrever `audit_logs` antigos. O JSON gravado com `history` continua como está.
- Criar outro fluxo de revisão ou outra notificação no lugar do Kanban.
- Corrigir regras de autorização, que pertencem à revisão de permissões.

## Decisions

**`DocumentRelease.document_id` substitui `history_id`.** A coluna é uma FK obrigatória e indexada para `documents`. `Document.releases` substitui a relação que passava pelo histórico, com `lazy='noload'` e `delete-orphan`, como em `DocumentHistory.releases`. Chamadas como `release.history.document` viram `release.document`, e os joins perdem um nível. A alternativa de manter a tabela sem o campo `status` preservaria uma ligação sem função.

**Migração em etapas numa só revisão.** A revisão adiciona `document_id` como anulável, preenche com `UPDATE ... FROM document_histories`, torna a coluna obrigatória, remove `history_id`, remove `document_histories`, remove `status` e `sent_to_kanban` de `project_documents` e converte `AUDITOR` e `ANALYST` para `DEFAULT`.

**`downgrade` recria a estrutura, sem recuperar dados.** Ele cria uma linha `PENDING` em `document_histories` por documento e religa os releases a ela. A sequência de status antiga e os níveis `AUDITOR` e `ANALYST` não voltam. Por isso o deploy exige backup.

**Ordenar `GET /doc` por `Document.created_at` crescente.** Hoje a ordem é status e data do último histórico. Sem transições, a data do histórico coincide com a criação do documento, então a ordem nova mantém o comportamento dos documentos que nunca passaram pelo Kanban. O join obrigatório sai, e nenhum documento fica de fora.

**`access_level` valida contra o enum reduzido.** `UserPublic` também usa o enum, então a migração precisa rodar antes de o código novo servir tráfego. O `entrypoint.sh` aplica as migrações antes de subir a API.

**Remover os ramos de `history` do `audit_service`.** `STATUS_TRANSLATION` e o tratamento da chave `history` só servem a diffs de status, e `update_document_status` era o único chamador que gerava esse diff.

**Ignorar `status` no `POST /project-document`.** O Pydantic ignora o campo extra, e o back sai primeiro sem quebrar o front. A limpeza do front vem em PR próprio no `lumina-front`.

## Risks / Trade-offs

- [Falha na migração com dados reais] → O teste de migração cobre documento com vários históricos, e o plano abaixo roda a contagem antes e depois.
- [`downgrade` perde dados] → Fazer backup antes do deploy. Reverter de verdade significa restaurar esse backup.
- [Ordem de `GET /doc` muda para documentos que passaram pelo Kanban] → Aceito, porque o status deixa de existir.
- [Conflito com a #32] → Esta mudança toca `advisorship_repo.get_advisee_document_metrics` e o schema de cartão, e a #32 toca `get_active_pair` e `get_advisee_documents`. São funções diferentes, mas quem mergear depois precisa atualizar a branch.

## Migration Plan

1. Fazer backup do banco.
2. Registrar `SELECT count(*) FROM document_releases`.
3. Publicar o back, que aplica a migração.
4. Conferir que a contagem não mudou e que `SELECT count(*) FROM document_releases WHERE document_id IS NULL` devolve zero.
5. Publicar a limpeza do `lumina-front`.
