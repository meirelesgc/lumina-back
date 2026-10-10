## Purpose

Permite que um usuário envie um documento normativo em PDF e receba sugestões revisáveis (dry-run) para criar ou enriquecer a árvore de verificação (Source, Typification, Taxonomy e Branch). Nenhuma alteração chega à árvore real sem confirmação explícita, item a item.

## ADDED Requirements

### Requirement: Create suggestion session from a normative PDF
O sistema SHALL fornecer o endpoint autenticado `POST /tree-suggestion`, que recebe um arquivo PDF (multipart) e, opcionalmente, `typification_id`. Ele cria uma sessão de sugestão com status `processing` e responde HTTP 202 com os dados da sessão. A geração das sugestões MUST ocorrer de forma assíncrona, sem bloquear a resposta. Sem `typification_id`, a sessão fica no modo `create`; com ele, no modo `enrich`.

#### Scenario: Session created in create mode
- **WHEN** um usuário autenticado envia um PDF válido sem `typification_id`
- **THEN** o sistema responde HTTP 202 com a sessão no modo `create`, status `processing`, nome do arquivo original e criador
- **THEN** o arquivo enviado fica armazenado e associado à sessão

#### Scenario: Session created in enrich mode
- **WHEN** um usuário autenticado envia um PDF válido com o `typification_id` de uma tipificação ativa
- **THEN** o sistema responde HTTP 202 com a sessão no modo `enrich`, referenciando a tipificação alvo

#### Scenario: Target typification does not exist
- **WHEN** o `typification_id` informado não existe ou foi excluído logicamente
- **THEN** o sistema responde HTTP 404 e nenhuma sessão é criada

#### Scenario: Non-PDF file is rejected
- **WHEN** o arquivo enviado não é um PDF (pelo tipo declarado ou pelo conteúdo)
- **THEN** o sistema responde HTTP 415 e nenhuma sessão é criada

#### Scenario: File exceeds configured limits
- **WHEN** o arquivo excede o tamanho máximo ou o número máximo de páginas configurados
- **THEN** o sistema responde HTTP 413 e nenhuma sessão é criada

#### Scenario: Unauthenticated request is rejected
- **WHEN** um cliente sem credenciais válidas chama qualquer endpoint `/tree-suggestion`
- **THEN** o sistema responde HTTP 401

### Requirement: Session processing lifecycle
O processamento SHALL levar a sessão de `processing` para `ready` quando as sugestões forem geradas, ou para `failed`, com uma mensagem de erro legível, quando a geração falhar. A sessão SHALL passar a `completed` quando não restar nenhum item `pending`. Uma sessão que permanecer em `processing` além do timeout configurado MUST ser reportada como `failed` na leitura seguinte.

#### Scenario: Generation succeeds
- **WHEN** o processamento termina sem erros
- **THEN** a sessão passa a `ready` e seus itens sugeridos ficam disponíveis com status `pending`

#### Scenario: Generation finds nothing applicable
- **WHEN** o processamento termina sem nenhuma sugestão válida além do Source
- **THEN** a sessão passa a `ready` contendo apenas o item de Source

#### Scenario: Generation fails
- **WHEN** ocorre um erro irrecuperável na extração do PDF ou na geração
- **THEN** a sessão passa a `failed` com `error_message` preenchida e sem itens sugeridos

#### Scenario: Processing exceeds timeout
- **WHEN** uma sessão é consultada e está em `processing` há mais tempo que o timeout configurado
- **THEN** a sessão é marcada e retornada como `failed`, com mensagem indicando timeout

### Requirement: Read and list suggestion sessions
O sistema SHALL fornecer `GET /tree-suggestion`, para listar sessões com paginação e filtro opcional por status, e `GET /tree-suggestion/{session_id}`, que retorna a sessão com todos os seus itens sugeridos. Qualquer usuário autenticado SHALL poder ler qualquer sessão.

#### Scenario: Read session with items
- **WHEN** um usuário autenticado consulta uma sessão existente
- **THEN** o sistema retorna HTTP 200 com modo, status, tipificação alvo (se houver), arquivo, criador, datas e a lista de itens
- **THEN** a sessão traz o nome atual da tipificação alvo (`target_typification_name`), e cada item com pai existente traz o título atual desse pai (`parent_entity_title`), sem exigir chamadas adicionais

#### Scenario: Session not found
- **WHEN** o `session_id` não existe
- **THEN** o sistema responde HTTP 404

#### Scenario: List filtered by status
- **WHEN** um usuário lista sessões com `status=ready`
- **THEN** apenas sessões com status `ready` são retornadas, ordenadas pela data de criação, da mais recente para a mais antiga

### Requirement: Suggested item content
Cada item sugerido SHALL conter: `kind` (`source`, `typification`, `taxonomy` ou `branch`), `operation` (`create` ou `update`), campos propostos (`name` ou `title` e `description`), status (`pending`, `confirmed` ou `discarded`) e a referência ao seu pai. O pai pode ser outro item sugerido da mesma sessão ou uma entidade existente da árvore. Itens que não sejam `source` MUST trazer ao menos uma evidência com trecho literal e página(s) do documento, além de uma justificativa.

#### Scenario: Source item is always proposed
- **WHEN** uma sessão chega a `ready`
- **THEN** ela contém exatamente um item `kind=source`, `operation=create`, com nome e descrição sugeridos a partir do documento

#### Scenario: Item hierarchy in create mode
- **WHEN** uma sessão no modo `create` chega a `ready`
- **THEN** cada item `taxonomy` referencia um item `typification` da sessão como pai, e cada item `branch` referencia um item `taxonomy` da sessão como pai

#### Scenario: Multiple typifications from one document
- **WHEN** o documento regula mais de um tipo documental (ex.: TCC, dissertação e tese)
- **THEN** a sessão no modo `create` contém um item `typification` para cada tipo identificado, cada um com sua própria subárvore

#### Scenario: Evidence is present and verifiable
- **WHEN** um item `typification`, `taxonomy` ou `branch` é retornado
- **THEN** cada evidência traz um trecho que pode ser localizado no texto extraído do documento e as páginas correspondentes (base 1)

#### Scenario: Unverifiable suggestions are dropped
- **WHEN** o gerador produz uma sugestão cuja evidência não pode ser localizada no texto extraído
- **THEN** a sugestão não é persistida como item da sessão

### Requirement: Enrich mode proposals
No modo `enrich`, o sistema SHALL propor apenas: novas taxonomias sob a tipificação alvo; novos ramos sob taxonomias existentes ou sob taxonomias sugeridas; e alterações (`operation=update`) de título e/ou descrição em taxonomias e ramos existentes da tipificação alvo. O sistema MUST NOT propor remoções nem itens fora da subárvore da tipificação alvo.

#### Scenario: New items under existing tree
- **WHEN** o documento contém regras não cobertas pela tipificação alvo
- **THEN** a sessão contém itens `create` cujo pai é a tipificação alvo, uma taxonomia existente dela ou um item `taxonomy` sugerido

#### Scenario: Update proposal for existing item
- **WHEN** o documento detalha ou corrige uma taxonomia ou ramo existente
- **THEN** a sessão contém um item `operation=update` que referencia a entidade existente, com os valores atuais e os valores propostos para comparação

#### Scenario: No removals proposed
- **WHEN** a tipificação alvo contém itens não mencionados pelo documento
- **THEN** nenhum item da sessão representa a remoção desses itens

### Requirement: Duplicate signaling
Para itens `create`, o sistema SHALL sinalizar quando houver entidade ativa semelhante no mesmo escopo: tipificações em escopo global, taxonomias dentro da mesma tipificação e ramos dentro da mesma taxonomia. Para isso, preenche a referência à entidade semelhante e o motivo. A sinalização é informativa e MUST NOT impedir a confirmação.

#### Scenario: Similar existing item is flagged
- **WHEN** um item sugerido tem título equivalente (após normalização) ou semanticamente equivalente a uma entidade ativa do mesmo escopo
- **THEN** o item traz `similar_to_id` apontando a entidade existente e uma nota explicando a semelhança

#### Scenario: Confirming an exact title collision
- **WHEN** o usuário confirma um item `create` cujo título final é idêntico ao de uma entidade ativa do mesmo escopo
- **THEN** o sistema responde HTTP 409, o item permanece `pending` e a árvore não é alterada

### Requirement: Confirm a suggested item
O sistema SHALL fornecer `POST /tree-suggestion/{session_id}/items/{item_id}/confirm`, com corpo opcional para sobrescrever os campos propostos. A confirmação MUST aplicar o item imediatamente na árvore real, com as mesmas validações e efeitos colaterais da criação ou atualização manual (unicidade, registro de auditoria e, para ramos, análise de seção e expansão de consultas). Ao final, o item fica `confirmed`, com referência à entidade aplicada, ao revisor e à data da revisão.

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

### Requirement: Source linkage
O item `source` SHALL ser independente da cascata: confirmá-lo não é pré-requisito de nenhum outro item. Quando confirmado, o Source criado recebe o arquivo da sessão e MUST ser vinculado às tipificações e taxonomias que a sessão já aplicou (criadas ou atualizadas) e às que aplicar depois. No modo `enrich`, ele é vinculado também à tipificação alvo. Se o item `source` for descartado, nenhum vínculo é criado.

#### Scenario: Source confirmed after tree items
- **WHEN** a sessão já tem itens `typification` e `taxonomy` confirmados e o usuário confirma o item `source`
- **THEN** o Source é criado com o arquivo da sessão e vinculado a essas tipificações e taxonomias

#### Scenario: Tree item confirmed after source
- **WHEN** o item `source` já foi confirmado e o usuário confirma um item `typification` ou `taxonomy`
- **THEN** a entidade aplicada é vinculada ao Source da sessão

#### Scenario: Source discarded
- **WHEN** o item `source` é descartado e outros itens são confirmados
- **THEN** as entidades aplicadas não recebem vínculo com nenhum Source da sessão

### Requirement: Discard suggested items
O sistema SHALL fornecer `POST /tree-suggestion/{session_id}/items/{item_id}/discard` e `POST /tree-suggestion/{session_id}/discard`. O primeiro descarta um item pendente e, em cascata, todos os seus descendentes pendentes. O segundo descarta todos os itens pendentes da sessão. O descarte MUST NOT alterar a árvore real.

#### Scenario: Discard parent cascades to children
- **WHEN** o usuário descarta um item `typification` pendente que tem taxonomias e ramos sugeridos pendentes
- **THEN** o item e todos os seus descendentes pendentes ficam `discarded`

#### Scenario: Discard whole session
- **WHEN** o usuário descarta a sessão
- **THEN** todos os itens pendentes ficam `discarded`, os já confirmados permanecem inalterados e a sessão passa a `completed`

#### Scenario: Session completes after last review
- **WHEN** o último item pendente de uma sessão é confirmado ou descartado
- **THEN** a sessão passa a `completed`
