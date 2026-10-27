# study-guide Specification

## Purpose

Indica ao pesquisador o que estudar para produzir cada entregável de um grupo de documentos e em que ordem, com anexos (tipificações, artigos por DOI e links) descritos pelo configurador e progresso acompanhado por projeto.

## Requirements

### Requirement: Cadastrar anexo de estudo em um item de grupo
O sistema SHALL oferecer `POST /document-group/item/{item_id}/attachment` para criar um anexo de estudo em um item ativo de grupo. Todo anexo tem `kind` (`TYPIFICATION`, `DOI` ou `LINK`) e `description` opcional em texto livre. O anexo novo entra no fim da lista do item. A rota segue a regra de acesso das demais rotas do configurador.

#### Scenario: Item inexistente
- **WHEN** o item não existe ou foi excluído
- **THEN** o sistema retorna 404

#### Scenario: Descrição gravada
- **WHEN** o usuário cria um anexo com `description` "Leia os critérios da seção de metodologia antes de escrever o anteprojeto"
- **THEN** a resposta e as listagens devolvem essa descrição sem alteração

### Requirement: Anexo do tipo tipificação
Um anexo `TYPIFICATION` SHALL apontar para uma tipificação ativa por `typification_id`. A resposta SHALL trazer o id e o nome da tipificação. O mesmo item não SHALL ter dois anexos ativos para a mesma tipificação.

#### Scenario: Tipificação válida
- **WHEN** o usuário cria um anexo `TYPIFICATION` com o id da tipificação X
- **THEN** o sistema retorna 201 com `typification` contendo o id e o nome de X

#### Scenario: Tipificação inexistente
- **WHEN** `typification_id` não existe, foi excluído ou não foi enviado
- **THEN** o sistema retorna 422

#### Scenario: Tipificação repetida no item
- **WHEN** o item já tem um anexo ativo para a tipificação X e o usuário cria outro para X
- **THEN** o sistema retorna 409

### Requirement: Anexo do tipo DOI
Um anexo `DOI` SHALL aceitar o DOI puro (`10.1234/abc`) ou com os prefixos `doi:`, `https://doi.org/` e `https://dx.doi.org/`. O sistema SHALL gravar o DOI sem prefixo e em minúsculas e devolver `doi_url` no formato `https://doi.org/<doi>`. O mesmo item não SHALL ter dois anexos ativos com o mesmo DOI.

#### Scenario: DOI com prefixo de URL
- **WHEN** o usuário envia `https://doi.org/10.1590/S0102-311X2023000100001`
- **THEN** o anexo grava `doi` como `10.1590/s0102-311x2023000100001`
- **THEN** a resposta traz `doi_url` igual a `https://doi.org/10.1590/s0102-311x2023000100001`

#### Scenario: DOI inválido
- **WHEN** o valor enviado não começa por `10.`, seguido de quatro a nove dígitos, uma barra e um sufixo
- **THEN** o sistema retorna 422

#### Scenario: DOI repetido no item
- **WHEN** o item já tem um anexo ativo com o mesmo DOI, escrito com outra caixa ou outro prefixo
- **THEN** o sistema retorna 409

### Requirement: Metadados do DOI pelo Crossref
Ao criar um anexo `DOI`, ou ao trocar o DOI de um anexo existente, o sistema SHALL consultar o Crossref e gravar título, autores, ano e veículo de publicação. O título enviado pelo usuário SHALL prevalecer sobre o do Crossref. Se o Crossref falhar, demorar além do limite configurado ou não conhecer o DOI, o sistema SHALL gravar o anexo assim mesmo.

#### Scenario: Crossref encontra o DOI
- **WHEN** o usuário cria um anexo `DOI` sem título e o Crossref responde com os metadados do artigo
- **THEN** o anexo grava título, autores, ano e veículo vindos do Crossref
- **THEN** a resposta traz `metadata_source` igual a `CROSSREF`

#### Scenario: Título digitado prevalece
- **WHEN** o usuário cria um anexo `DOI` com título "Artigo Z" e o Crossref devolve outro título
- **THEN** o anexo grava o título "Artigo Z" e os autores, o ano e o veículo do Crossref

#### Scenario: Crossref indisponível
- **WHEN** o Crossref responde com erro, não conhece o DOI ou passa do tempo limite
- **THEN** o sistema retorna 201 com o anexo, o título digitado (ou nulo), autores, ano e veículo vazios
- **THEN** a resposta traz `metadata_source` igual a `MANUAL`

#### Scenario: Edição sem troca de DOI
- **WHEN** o usuário edita só a descrição de um anexo `DOI`
- **THEN** o sistema não consulta o Crossref e mantém os metadados gravados

### Requirement: Anexo do tipo link
Um anexo `LINK` SHALL exigir `url` com esquema `http` ou `https` e `title` não vazio. O mesmo item não SHALL ter dois anexos ativos com a mesma URL.

#### Scenario: Link válido
- **WHEN** o usuário cria um anexo `LINK` com título "Livro XPTO" e uma URL `https`
- **THEN** o sistema retorna 201 com o título e a URL

#### Scenario: Link sem título ou com esquema inválido
- **WHEN** o título está vazio ou a URL usa outro esquema, como `ftp` ou `javascript`
- **THEN** o sistema retorna 422

#### Scenario: URL repetida no item
- **WHEN** o item já tem um anexo ativo com a mesma URL
- **THEN** o sistema retorna 409

### Requirement: Listar, editar, reordenar e excluir anexos
O sistema SHALL oferecer `GET /document-group/item/{item_id}/attachments`, que devolve os anexos ativos do item ordenados pela posição, `PUT /document-group/attachment` para editar, `DELETE /document-group/attachment/{attachment_id}` para excluir e `PUT /document-group/item/{item_id}/attachments/order` para reordenar com a lista completa de ids. O tipo de um anexo não muda depois de criado.

#### Scenario: Reordenar anexos
- **WHEN** o usuário envia a lista completa de ids dos anexos ativos do item em outra ordem
- **THEN** o sistema retorna 200 com os anexos na ordem enviada

#### Scenario: Reordenação inválida
- **WHEN** a lista omite um anexo ativo, repete um id ou traz um id de outro item
- **THEN** o sistema retorna 422 e não altera nenhuma posição

#### Scenario: Troca de tipo
- **WHEN** o usuário envia um `kind` diferente do tipo gravado
- **THEN** o sistema retorna 422

#### Scenario: Exclusão
- **WHEN** o usuário exclui um anexo
- **THEN** o anexo some da listagem do item e do guia de estudo dos projetos
- **THEN** o total de anexos e o de anexos estudados dos projetos que o marcaram deixam de contar esse anexo

### Requirement: Anexo de tipificação excluída fica oculto
Quando a tipificação de um anexo `TYPIFICATION` for excluída, o sistema SHALL omitir o anexo da listagem do item, do guia de estudo e da contagem de progresso. A exclusão da tipificação SHALL continuar funcionando como hoje.

#### Scenario: Tipificação excluída depois do cadastro
- **WHEN** o item tem um anexo para a tipificação X e alguém exclui X
- **THEN** a listagem do item e o guia de estudo não trazem esse anexo
- **THEN** o total de anexos e o de anexos estudados do progresso deixam de contar esse anexo

### Requirement: Guia de estudo do projeto
O sistema SHALL oferecer `GET /project/{project_id}/study-guide`, que devolve o grupo do projeto, os itens ativos em ordem e, em cada item, os anexos ativos em ordem com `studied` e `studied_at` daquele projeto, além do total de anexos e de anexos estudados. Podem ler o guia o dono do projeto, orientador com vínculo ativo com o dono e admin.

#### Scenario: Orientando abre o guia do TCC
- **WHEN** o dono de um projeto do grupo "TCC" abre o guia
- **THEN** o sistema retorna 200 com os itens anteprojeto, TCC e outro documento nessa ordem
- **THEN** cada item traz os anexos em ordem, com tipo, descrição e os dados do tipo (tipificação, DOI e metadados, ou link)

#### Scenario: Projeto sem grupo
- **WHEN** o projeto não tem grupo de documentos
- **THEN** o sistema retorna 200 com `document_group` nulo, `items` vazio e progresso 0 de 0

#### Scenario: Orientador e admin leem o guia
- **WHEN** um orientador com vínculo ativo com o dono, ou um admin, abre o guia do projeto
- **THEN** o sistema retorna 200 com os mesmos itens, anexos e progresso que o dono vê

#### Scenario: Terceiro sem acesso
- **WHEN** um usuário que não é dono, orientador ativo do dono nem admin pede o guia
- **THEN** o sistema retorna 403

#### Scenario: Projeto inexistente
- **WHEN** o projeto não existe ou foi excluído
- **THEN** o sistema retorna 404

### Requirement: Marcar anexo como estudado
O sistema SHALL oferecer `PUT /project/{project_id}/study-guide/attachment/{attachment_id}/studied` para marcar e `DELETE` na mesma rota para desmarcar. Só o dono do projeto marca e desmarca. O progresso pertence ao par projeto e anexo. As duas operações SHALL ser idempotentes.

#### Scenario: Orientando marca um anexo
- **WHEN** o dono do projeto marca o artigo Z como estudado
- **THEN** o sistema retorna 200 e o guia passa a trazer `studied` verdadeiro e `studied_at` para o artigo Z
- **THEN** o total de anexos estudados aumenta em 1

#### Scenario: Marcar duas vezes
- **WHEN** o dono marca um anexo que já está marcado
- **THEN** o sistema retorna 200 e mantém o `studied_at` original

#### Scenario: Desmarcar
- **WHEN** o dono desmarca um anexo marcado
- **THEN** o guia volta a trazer `studied` falso para esse anexo

#### Scenario: Orientador tenta marcar
- **WHEN** um orientador com vínculo ativo, ou um admin que não é dono, tenta marcar um anexo
- **THEN** o sistema retorna 403

#### Scenario: Anexo fora do grupo do projeto
- **WHEN** o anexo pertence a um item de outro grupo, foi excluído ou está oculto por tipificação excluída
- **THEN** o sistema retorna 404

#### Scenario: Progresso separado por projeto
- **WHEN** o mesmo orientando tem dois projetos do grupo "TCC" e marca o artigo Z só no primeiro
- **THEN** o guia do segundo projeto traz `studied` falso para o artigo Z
