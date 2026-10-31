# document-releases Specification

## Purpose
Define como cada release se liga ao seu documento e quais dados de documento, release e documento de projeto a API expõe depois da remoção do Kanban.

## Requirements

### Requirement: Release pertence diretamente ao documento

O sistema SHALL ligar cada release a exatamente um documento, e SHALL listar em `GET /doc/{doc_id}/release` todos os releases não removidos desse documento.

#### Scenario: Usuário envia um release

- **WHEN** o autor envia um arquivo em `POST /doc/{doc_id}/release`
- **THEN** o release aparece em `GET /doc/{doc_id}/release`

#### Scenario: Release de outro documento

- **WHEN** um usuário lista os releases de um documento
- **THEN** a resposta não traz releases de outros documentos

### Requirement: Migração preserva os releases

A migração SHALL ligar cada release existente ao documento que o histórico dele apontava, e SHALL remover a tabela de histórico sem perder nenhum release.

#### Scenario: Documento com vários históricos

- **WHEN** a migração roda sobre um documento com releases em dois históricos diferentes
- **THEN** os dois releases ficam ligados a esse documento e a tabela `document_histories` deixa de existir

### Requirement: Fluxo de status removido

O sistema SHALL responder `404` às antigas rotas `PUT /doc/{doc_id}/status/*`, e SHALL omitir `history` da resposta de documento e `history_id` da resposta de release.

#### Scenario: Cliente chama uma rota de status

- **WHEN** um usuário autenticado envia `PUT /doc/{doc_id}/status/completed`
- **THEN** o sistema responde `404`

#### Scenario: Cliente lê um documento

- **WHEN** o autor envia `GET /doc/{doc_id}`
- **THEN** a resposta não traz o campo `history`

### Requirement: Listagem de documentos por data de criação

O sistema SHALL ordenar `GET /doc` pela data de criação do documento, do mais antigo para o mais recente, e SHALL incluir todos os documentos visíveis ao usuário.

#### Scenario: Usuário lista os documentos

- **WHEN** um usuário com dois documentos envia `GET /doc`
- **THEN** a resposta traz os dois documentos, com o mais antigo primeiro

### Requirement: Documento de projeto sem status de fluxo

O sistema SHALL omitir `status` e `sent_to_kanban` das respostas de documento de projeto, e SHALL ignorar esses campos quando vierem no corpo.

#### Scenario: Front cria documento de projeto com status

- **WHEN** um usuário envia `POST /project-document` com `status` igual a `PENDING`
- **THEN** o sistema cria o documento de projeto e a resposta não traz `status` nem `sent_to_kanban`

### Requirement: Cartão de orientando sem pendências de revisão

O sistema SHALL omitir `pending_reviews` da resposta de `GET /advisorship/my-advisees`, e SHALL manter `total_documents`.

#### Scenario: Orientador lista os orientandos

- **WHEN** um orientador com vínculo ativo envia `GET /advisorship/my-advisees`
- **THEN** cada cartão traz `total_documents` e não traz `pending_reviews`
