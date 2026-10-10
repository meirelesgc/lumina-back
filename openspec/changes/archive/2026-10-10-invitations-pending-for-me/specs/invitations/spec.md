## Purpose

Permite o gerenciamento e a consulta de convites de orientação acadêmica no sistema Lumina, possibilitando que usuários autenticados visualizem seus convites pendentes e ajam sobre eles.

## ADDED Requirements

### Requirement: List pending invitations for authenticated user
O sistema SHALL fornecer um endpoint autenticado `GET /invitations/pending-for-me` que lista todos os convites pendentes de orientação acadêmica associados ao e-mail do usuário atualmente autenticado.

#### Scenario: User lists pending invitations successfully
- **WHEN** um usuário autenticado com e-mail cadastrado faz uma requisição `GET /invitations/pending-for-me`
- **THEN** o sistema retorna status HTTP 200 com a lista de todos os convites direcionados ao e-mail do usuário cujo status seja `PENDING`
- **THEN** cada convite retornado inclui detalhes de quem convidou (`inviter`), projeto vinculado (`project`), status, papel (`role_type`), tópico (`topic`), token de aceite e data de expiração (`expires_at`)
- **THEN** a lista é ordenada por data de criação de forma decrescente

#### Scenario: Unauthenticated request is rejected
- **WHEN** um cliente não autenticado faz uma requisição `GET /invitations/pending-for-me` sem credenciais válidas
- **THEN** o sistema retorna status HTTP 401 Unauthorized

### Requirement: Filter out invalid, expired, and non-pending invitations
O endpoint `GET /invitations/pending-for-me` SHALL retornar apenas convites ativos e válidos para resposta.

#### Scenario: Exclude expired, accepted, rejected, cancelled, and deleted invitations
- **WHEN** existem convites para o e-mail do usuário com status `ACCEPTED`, `REJECTED`, `CANCELLED`, ou com `expires_at` anterior ao momento atual, ou com `deleted_at` preenchido
- **THEN** esses convites NÃO são retornados na lista do endpoint `GET /invitations/pending-for-me`

#### Scenario: User has no pending invitations
- **WHEN** o usuário autenticado não possui convites pendentes válidos direcionados ao seu e-mail
- **THEN** o sistema retorna status HTTP 200 com uma lista vazia `{"invitations": []}`
