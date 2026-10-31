# document-groups Specification

## Purpose

Organiza os grupos de documentos do configurador, que listam os entregáveis de um tipo de trabalho, e define a ordem em que o pesquisador produz esses entregáveis.

## Requirements

### Requirement: Itens de grupo têm posição
Cada item ativo de um grupo de documentos SHALL ter uma posição inteira, única dentro do grupo, começando em 1. O sistema SHALL devolver os itens de um grupo ordenados pela posição em `GET /document-group/{group_id}`, `GET /document-group` e `GET /document-group/{group_id}/items`.

#### Scenario: Item novo entra no fim da lista
- **WHEN** um usuário autenticado cria um item em um grupo que já tem dois itens ativos
- **THEN** o item novo recebe a posição 3
- **THEN** a listagem do grupo devolve o item novo por último

#### Scenario: Itens existentes recebem posição pela data de criação
- **WHEN** a migração roda em uma base com grupos que já têm itens
- **THEN** cada item ativo recebe a posição pela ordem de criação dentro do grupo, começando em 1

#### Scenario: Item excluído não aparece na listagem
- **WHEN** um item do grupo foi excluído
- **THEN** as listagens do grupo não devolvem esse item

### Requirement: Reordenar itens de um grupo
O sistema SHALL oferecer `PUT /document-group/{group_id}/items/order`, que recebe a lista completa de ids dos itens ativos do grupo na ordem desejada e grava as posições 1, 2, 3... nessa ordem. A rota segue a mesma regra de acesso das demais rotas do configurador.

#### Scenario: Reordenação bem-sucedida
- **WHEN** um usuário autenticado envia `{"item_ids": [tcc, anteprojeto, outro]}` para um grupo com esses três itens ativos
- **THEN** o sistema retorna 200 com o grupo e os itens na ordem enviada

#### Scenario: Lista incompleta ou com id estranho
- **WHEN** a lista enviada omite um item ativo, repete um id ou traz um id que não é item ativo do grupo
- **THEN** o sistema retorna 422 e não altera nenhuma posição

#### Scenario: Grupo inexistente
- **WHEN** o grupo não existe ou foi excluído
- **THEN** o sistema retorna 404
