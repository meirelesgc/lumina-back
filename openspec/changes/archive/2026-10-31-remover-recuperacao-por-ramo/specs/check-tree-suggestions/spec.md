# Spec Delta

## MODIFIED Requirements

### Requirement: Confirm a suggested item
O sistema SHALL fornecer `POST /tree-suggestion/{session_id}/items/{item_id}/confirm`, com corpo opcional para sobrescrever os campos propostos. A confirmação MUST aplicar o item imediatamente na árvore real, com as mesmas validações e efeitos colaterais da criação ou atualização manual (unicidade e registro de auditoria). Ao final, o item fica `confirmed`, com referência à entidade aplicada, ao revisor e à data da revisão.

#### Scenario: Confirm create item with edits
- **WHEN** o usuário confirma um item `create` pendente, informando novo título
- **THEN** a entidade é criada na árvore real com o título informado, o item fica `confirmed`, com `applied_entity_id`, e os valores finais aplicados ficam registrados no item

#### Scenario: Child requires parent in the real tree
- **WHEN** o usuário confirma um item cujo pai é um item sugerido ainda não confirmado
- **THEN** o sistema responde HTTP 409, informando que o pai deve ser confirmado antes, e nada é aplicado

#### Scenario: Child of confirmed parent
- **WHEN** o usuário confirma um item cujo pai sugerido já foi confirmado
- **THEN** a entidade é criada sob a entidade aplicada pelo pai

#### Scenario: Confirm update item
- **WHEN** o usuário confirma um item `update` pendente, e a entidade alvo não mudou desde a geração da sugestão
- **THEN** título e descrição da entidade existente são atualizados para os valores finais

#### Scenario: Stale update is rejected
- **WHEN** o usuário confirma um item `update` cuja entidade alvo foi alterada ou excluída depois da geração da sugestão
- **THEN** o sistema responde HTTP 409 e a entidade não é alterada

#### Scenario: Item is not pending
- **WHEN** o usuário tenta confirmar ou descartar um item já `confirmed` ou `discarded`
- **THEN** o sistema responde HTTP 409

#### Scenario: Session not ready for review
- **WHEN** o usuário tenta confirmar ou descartar um item de uma sessão em `processing` ou `failed`
- **THEN** o sistema responde HTTP 409

#### Scenario: Confirmação de ramo sem chamada de modelo
- **WHEN** o usuário confirma um item de ramo
- **THEN** o ramo é aplicado sem nenhuma chamada a modelo de linguagem
