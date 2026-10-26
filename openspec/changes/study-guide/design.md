# Design

## Context

O configurador já tem `DocumentGroup` (um tipo de trabalho, como "TCC") e `DocumentGroupItem` (os entregáveis, com nome e ícone). O `Project` escolhe um grupo por `document_group_id`. As rotas de grupos aceitam qualquer usuário autenticado e não registram auditoria. As listagens ordenam itens por `created_at` e o `selectinload(DocumentGroup.items)` em `document_group_repo.py` não filtra itens excluídos.

A check tree (`Typification` → `Taxonomy` → `Branch` → `Source`) descreve os critérios de avaliação. O acesso a projetos já está em `project_repo.has_project_access` (dono, orientador com vínculo ativo, admin).

Motivação e escopo: ver `proposal.md`. Requisitos: ver `specs/document-groups/spec.md` e `specs/study-guide/spec.md`.

## Goals / Non-Goals

**Goals:**
- Prender os anexos ao item do grupo, para que todo projeto do grupo veja o mesmo guia.
- Referenciar tipificações por chave estrangeira, sem copiar dados da check tree.
- Manter o cadastro de DOI funcionando quando o Crossref cair.

**Non-Goals:**
- Corrigir a falta de checagem de admin no configurador.
- Auditoria (`audit_service`) nas rotas de grupos e anexos. As rotas de grupos não auditam hoje, e os anexos seguem o mesmo padrão.
- Cache de respostas do Crossref.

## Decisions

### 1. Anexo como tabela nova, sem reaproveitar `Source`

`study_attachments` guarda os três tipos numa tabela só, com `kind` e colunas anuláveis por tipo:

| Coluna | Uso |
| :--- | :--- |
| `id`, campos do `AuditMixin` | todos |
| `document_group_item_id` (FK, `ondelete=CASCADE`) | todos |
| `position` (int) | todos |
| `kind` (`TYPIFICATION`, `DOI`, `LINK`) | todos |
| `description` (text, anulável) | todos |
| `title` (anulável) | `DOI` e `LINK` |
| `typification_id` (FK para `typifications`) | `TYPIFICATION` |
| `doi` | `DOI` |
| `authors` (JSONB, lista de nomes), `year`, `container_title`, `metadata_source` (`CROSSREF`, `MANUAL`) | `DOI` |
| `url` | `LINK` |

Um `CheckConstraint` por tipo garante as colunas obrigatórias: `typification_id` não nulo para `TYPIFICATION`, `doi` e `metadata_source` para `DOI`, `url` e `title` para `LINK`. Três índices únicos parciais (`deleted_at IS NULL`) impedem duplicatas no item: `(item, typification_id)`, `(item, doi)` e `(item, url)`.

Alternativas descartadas:
- **Guardar DOI e link em `Source`**: `Source` tem nome único global, entra no snapshot da release (`AppliedSource`) e embasa ramos avaliados pela IA. Um artigo de estudo ali apareceria na árvore de avaliação.
- **Uma tabela por tipo**: três CRUDs e três consultas para montar o guia em ordem. A ordem mistura os tipos dentro do item, então uma tabela só simplifica a posição.
- **Lista de ids em JSONB, como `ProjectDocument.typification_ids`**: sem chave estrangeira, a exclusão de uma tipificação deixa ids órfãos.

### 2. Posição inteira com renumeração na reordenação

`DocumentGroupItem.position` e `StudyAttachment.position` são inteiros. Criar põe `max(position) + 1` dos ativos. Excluir deixa um buraco, que não afeta a ordem. Reordenar recebe a lista completa e regrava 1, 2, 3... na mesma transação. Não há índice único em `position`: a regravação em lote violaria um índice único no meio da transação, e a lista completa já garante a consistência.

Alternativa descartada: posição fracionária (inserir entre dois itens sem renumerar). Os grupos têm poucos itens e a lista completa é mais simples de validar.

### 3. Progresso por projeto e anexo

`study_progress` tem `project_id` (FK, `CASCADE`), `study_attachment_id` (FK, `CASCADE`), `studied_at` e `studied_by`, com chave primária composta. Marcar é um insert que ignora conflito, o que mantém o `studied_at` original. Desmarcar apaga a linha. A tabela não usa `AuditMixin`: o registro é um fato do aluno, não um cadastro do configurador.

### 4. Cliente do Crossref isolado

`lumina/services/crossref_client.py` expõe uma função assíncrona `fetch_doi_metadata(doi) -> DoiMetadata | None`. Ela chama `GET {CROSSREF_URL}/works/{doi}` com `httpx.AsyncClient`, timeout `CROSSREF_TIMEOUT_SECONDS` (padrão 5) e `User-Agent` com `CROSSREF_MAILTO` quando configurado. Qualquer erro de rede, status diferente de 200 ou JSON inesperado devolve `None` e registra um aviso no log. O serviço de anexos decide o que gravar: título do usuário se houver, senão o do Crossref.

A normalização do DOI fica numa função pura no mesmo módulo, testada sem rede. O DOI é gravado em minúsculas porque o DOI não diferencia caixa, e isso torna o índice único simples.

Alternativa descartada: rota de pré-visualização chamada pelo front. Você escolheu o preenchimento no cadastro. A rota pode entrar depois sem mudar o modelo.

### 5. Rotas

Os anexos ficam no router de grupos (`/document-group/item/{item_id}/attachment...`, `/document-group/attachment...`), seguindo os caminhos de item que já existem (`PUT /document-group/item` com o id no corpo). O guia e o progresso ficam no router de projetos, porque dependem do acesso ao projeto. Um `study_guide_service.py` monta o guia e reutiliza `project_repo.has_project_access`. A marcação compara `project.created_by` com o usuário atual.

### 6. Tipificação excluída

As consultas de anexos fazem `outerjoin` com `typifications` e descartam linhas `TYPIFICATION` cuja tipificação tem `deleted_at`. `delete_typification` não muda.

### 7. Testes

Duas jornadas ficam em `tests/api/journeys/`, diretório novo (o Lumina ainda não tem testes de jornada). Em prosa:

> **A trilha da Helena** (`test_trilha_da_helena.py`). A configuradora Helena cria o grupo "TCC" com os itens outro documento, TCC e anteprojeto, reordena para anteprojeto, TCC e outro documento e confere a ordem. No anteprojeto, ela anexa a tipificação "Artigo científico". Cola um DOI com `https://doi.org/` e letras maiúsculas e vê o DOI limpo, com título, autores e ano do Crossref. Cola um segundo DOI com o Crossref fora do ar e vê o anexo salvo com o título que digitou e `metadata_source` `MANUAL`. Anexa um livro por link. Escreve uma descrição em cada anexo, sem que o Crossref seja consultado de novo, e reordena para o artigo introdutório vir primeiro. Exclui um anexo e confere que a lista ficou exatamente na ordem pedida, sem ele.

> **O semestre do Pedro** (`test_semestre_do_pedro.py`). O grupo "TCC" tem seis anexos nos três itens. Pedro cria dois projetos do grupo. No primeiro, abre o guia e vê anteprojeto, TCC e outro documento em ordem, 0 de 6. Marca o primeiro artigo e vê 1 de 6 com a data. Marca de novo e a data não muda. Marca outro anexo e desmarca, e o placar volta a 1. No segundo projeto, vê 0 de 6 e o artigo como não estudado. A orientadora Marina, com vínculo ativo, entra, abre o guia do primeiro projeto e vê 1 de 6; ao tentar marcar um anexo, recebe 403.

As recusas do cadastro (tipificação repetida, link sem título ou com `ftp`, DOI repetido com outra escrita) e as situações de acesso e exclusão (terceiro sem acesso, projeto sem grupo, tipificação excluída, marcação de anexo oculto, exclusão de anexo já marcado, admin que lê e não marca, projeto excluído) viram testes focados em `tests/api/check_tree/test_study_attachments_api.py` e `tests/api/check_tree/test_study_guide_api.py`. Cada uma prova um comportamento sozinha e não cabe no caminho de um ator.

O Crossref é substituído por um stub determinístico (monkeypatch de `fetch_doi_metadata`) nas jornadas e nos testes de rota. O stub conta as chamadas, para provar que editar a descrição não consulta o Crossref. O cliente em si é testado com `httpx.MockTransport`.

## Risks / Trade-offs

- [Crossref lento trava o cadastro] → timeout de 5 s configurável; na falha o anexo é salvo como `MANUAL`.
- [Metadados do Crossref mudam depois do cadastro] → o anexo guarda o que veio no cadastro. Trocar o DOI refaz a consulta. Não há atualização periódica.
- [Qualquer usuário autenticado edita o guia, como no resto do configurador] → registrado como fora do escopo, com issue própria.
- [Excluir um item deixa os anexos dele inacessíveis, mas ativos no banco] → os anexos somem junto com o item nas consultas, que filtram o item. O `CASCADE` só age na exclusão física.
- [`selectinload(DocumentGroup.items)` devolve itens excluídos hoje] → a mudança passa a filtrar e ordenar os itens no repositório, o que pode tirar itens excluídos de telas que hoje os mostram. Isso corrige um defeito, e o requisito "Item excluído não aparece na listagem" registra o comportamento.

## Migration Plan

1. Migração Alembic adiciona `document_group_items.position` como anulável, preenche com `row_number() over (partition by group_id order by created_at)` nos itens ativos (os excluídos recebem 0) e torna a coluna `NOT NULL`.
2. A mesma migração cria `study_attachments` e `study_progress` com as restrições da decisão 1 e 3.
3. Reversão: `downgrade` apaga as duas tabelas e a coluna. Nenhum dado existente depende delas.
