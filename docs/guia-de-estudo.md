# Guia de Estudo

O guia de estudo diz ao orientando o que estudar para cada entregável do projeto e em que ordem. O configurador monta o guia uma vez no grupo de documentos, e todo projeto que usa o grupo vê o mesmo guia. O progresso fica guardado por projeto.

O código está em:

* Rotas do configurador: `lumina/routers/check_tree/document_groups.py`
* Rotas do projeto: `lumina/routers/check_tree/projects.py`
* Serviços: `lumina/services/study_attachment_service.py` e `lumina/services/study_guide_service.py`
* Cliente do Crossref: `lumina/services/crossref_client.py`

---

## 1. Exemplo: o grupo TCC

Num grupo "TCC", o configurador põe os entregáveis na ordem de trabalho e anexa a cada um o material de estudo:

| Ordem | Entregável | Anexos |
| :--- | :--- | :--- |
| 1 | Anteprojeto | Tipificação "Artigo científico" |
| 2 | TCC | Tipificação "Artigo científico", artigo Z (DOI) |
| 3 | Outro documento | Tipificação "Revisão sistemática", livro XPTO (link) |

O orientando abre `GET /project/{project_id}/study-guide` e recebe os três entregáveis nessa ordem, cada um com os anexos em ordem, e o placar do projeto (`studied_attachments` de `total_attachments`).

---

## 2. Ordem dos entregáveis

Cada item do grupo tem uma posição. Um item novo entra no fim. Para mudar a ordem, o configurador envia a lista completa dos itens ativos:

```http
PUT /document-group/{group_id}/items/order
{"item_ids": ["<anteprojeto>", "<tcc>", "<outro>"]}
```

Se a lista omitir um item, repetir um id ou trouxer um item de outro grupo, a API responde `422` e não muda nada. As listagens do grupo não mostram itens excluídos.

---

## 3. Tipos de anexo

Todo anexo tem um tipo (`kind`) e uma descrição livre, como "Leia a seção de metodologia antes de escrever". O tipo não muda depois do cadastro.

| Tipo | Campos | Regras |
| :--- | :--- | :--- |
| `TYPIFICATION` | `typification_id` | A tipificação precisa existir. A resposta traz o id e o nome dela. |
| `DOI` | `doi`, `title` opcional | Aceita o DOI puro ou com `doi:`, `https://doi.org/` e `https://dx.doi.org/`. O Lumina grava o DOI sem prefixo, em minúsculas, e devolve `doi_url`. |
| `LINK` | `url`, `title` | A URL usa `http` ou `https`, e o título é obrigatório. |

O mesmo item não aceita dois anexos ativos para a mesma tipificação, o mesmo DOI ou a mesma URL: a API responde `409`. Um DOI escrito com outro prefixo ou outra caixa conta como o mesmo.

Rotas:

* `POST /document-group/item/{item_id}/attachment`: cria o anexo no fim da lista do item.
* `GET /document-group/item/{item_id}/attachments`: lista os anexos em ordem.
* `PUT /document-group/attachment`: edita um anexo.
* `PUT /document-group/item/{item_id}/attachments/order`: reordena com a lista completa de ids.
* `DELETE /document-group/attachment/{attachment_id}`: exclui o anexo.

Quando alguém exclui uma tipificação, os anexos que apontam para ela somem da lista do item, do guia e do placar. A exclusão da tipificação funciona como antes.

---

## 4. Consulta ao Crossref

Ao criar um anexo `DOI`, ou ao trocar o DOI de um anexo, o Lumina consulta `GET {CROSSREF_URL}/works/{doi}` e grava título, autores, ano e veículo. O título digitado pelo configurador prevalece sobre o do Crossref. Editar só a descrição não consulta o Crossref de novo.

Se o Crossref falhar, demorar além do limite ou não conhecer o DOI, o anexo é salvo assim mesmo, com o título digitado e `metadata_source` igual a `MANUAL`. Quando os metadados vêm do Crossref, `metadata_source` é `CROSSREF`.

| Variável | Padrão | Uso |
| :--- | :--- | :--- |
| `CROSSREF_URL` | `https://api.crossref.org` | Endereço da API |
| `CROSSREF_TIMEOUT_SECONDS` | `5` | Tempo limite da consulta |
| `CROSSREF_MAILTO` | vazio | E-mail enviado no `User-Agent`, que põe o Lumina no pool educado do Crossref |

---

## 5. Acesso e progresso

| Quem | Lê o guia | Marca e desmarca |
| :--- | :--- | :--- |
| Dono do projeto | Sim | Sim |
| Orientador com vínculo ativo com o dono | Sim | Não (`403`) |
| Admin | Sim | Não (`403`), a menos que seja o dono |
| Outro usuário | Não (`403`) | Não (`403`) |

O dono marca um anexo com `PUT /project/{project_id}/study-guide/attachment/{attachment_id}/studied` e desmarca com `DELETE` na mesma rota. As duas operações são idempotentes: marcar de novo mantém a data da primeira marcação. Um anexo de outro grupo, excluído ou oculto por tipificação excluída responde `404`.

O progresso pertence ao par projeto e anexo. Um orientando com dois projetos do mesmo grupo tem um placar em cada um. Um projeto sem grupo de documentos recebe o guia vazio, com placar 0 de 0.

As rotas do configurador seguem a regra atual dos grupos de documentos e aceitam qualquer usuário autenticado. A issue [#33](https://github.com/meirelesgc/lumina-back/issues/33) trata dessa regra.
