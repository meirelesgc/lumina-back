## Why

O Kanban e os níveis `AUDITOR` e `ANALYST` estão obsoletos. O front não chama as rotas de status, `ANALYST` não tem efeito e `AUDITOR` só recebe notificação do Kanban. Sem o Kanban, `DocumentHistory` vira uma tabela de ligação entre documento e release, e removê-la agora evita manter esse legado nas próximas mudanças, incluindo a revisão de permissões.

## What Changes

- **BREAKING**: remover as rotas `PUT /doc/{doc_id}/status/*` e as notificações de WhatsApp por troca de status.
- **BREAKING**: remover `AUDITOR` e `ANALYST` do `AccessType`. Contas com esses níveis passam a `DEFAULT`, e a API recusa esses valores com `422`.
- **BREAKING**: remover `history` da resposta de documento. `DocumentRelease` passa a apontar direto para o documento, e `history_id` sai da resposta de release.
- **BREAKING**: remover `status` e `sent_to_kanban` de `ProjectDocument`.
- **BREAKING**: remover `pending_reviews` dos cartões de orientando. A métrica compara `processing_status` com `WAITING_FOR_REVIEW`, valor que esse campo nunca assume, e sempre devolve zero.
- Remover a tabela `document_histories`, com migração que preserva todos os releases.

## Capabilities

### New Capabilities

- `document-releases`: vínculo direto entre release e documento e contrato das respostas que deixam de carregar histórico e status de fluxo.

### Modified Capabilities

- `access-control`: passa a definir os níveis de acesso aceitos pela API.

## Impact

- **Rotas**: `/doc/{doc_id}/status/*` deixam de existir. `/doc`, `/doc/{doc_id}/release`, `/project-document`, `/user` e `/advisorship/my-advisees` mudam de contrato.
- **Banco**: migração em `document_releases`, `project_documents` e `users`, e remoção de `document_histories`.
- **Código**: `lumina/models.py`, schemas de documento, release, projeto, orientação e usuário, pipeline de IA, relatórios, stats, chat, mensagens, repositories de documento e release, `audit_service` e `notification_service`.
- **Frontend**: nenhuma alteração, porque esta mudança só toca o backend. O front continua compatível: o `status` enviado ao criar documento de projeto passa a ser ignorado, e a métrica "Pendências de revisão" segue mostrando zero, como hoje, pelo `?? 0`. Os tipos do front continuam citando `ANALYST`, `AUDITOR`, `sent_to_kanban` e `history`, sem efeito em tela.
- **Testes**: `test_release_pipeline.py`, `test_report_export.py`, a caracterização do Kanban e os testes de orientação.
- **Fora desta mudança**: a revisão de permissões e as issues #31, #32 e #33.
