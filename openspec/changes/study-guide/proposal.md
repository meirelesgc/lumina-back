# Proposta: Guia de estudo por entregável

## Por que

Um orientando que começa um TCC sabe o que precisa entregar (anteprojeto, TCC, um terceiro documento) porque o projeto usa um grupo de documentos, mas não sabe o que estudar para cada entrega nem em que ordem trabalhar. O orientador hoje passa essas referências fora do Lumina, e o aluno não vê a ligação entre o material e os critérios em que o trabalho dele vai ser avaliado.

## O que muda

- Os itens de um grupo de documentos (`DocumentGroupItem`) ganham posição. O configurador define a ordem de trabalho: anteprojeto, depois TCC, depois o terceiro documento.
- Cada item recebe uma lista ordenada de anexos de estudo. Um anexo tem um tipo e uma descrição livre:
  - `TYPIFICATION`: aponta para uma tipificação da check tree.
  - `DOI`: guarda o DOI normalizado e o link `https://doi.org/...`. No cadastro, o Lumina consulta o Crossref e preenche título, autores, ano e veículo. Se a consulta falhar, o anexo é salvo com o título digitado.
  - `LINK`: guarda uma URL `http` ou `https` e um título.
- O projeto passa a expor o guia de estudo do grupo dele: itens e anexos em ordem, com o progresso do projeto.
- O dono do projeto marca e desmarca anexos como estudados. Orientador com vínculo ativo e admin leem o guia e o progresso, mas não marcam.
- Anexos de tipificação excluída somem do guia e da contagem de progresso.

Exemplo do resultado prático, num grupo "TCC":

| Ordem | Entregável | Anexos |
| :--- | :--- | :--- |
| 1 | Anteprojeto | Tipificação X |
| 2 | TCC | Tipificação X, artigo Z (DOI) |
| 3 | Outro documento | Tipificação Y, livro XPTO (link) |

## Capacidades

### Novas Capacidades

- `document-groups`: ordem dos itens de um grupo de documentos.
- `study-guide`: anexos de estudo por item de grupo (tipificação, DOI, link), consulta ao Crossref, guia de estudo do projeto e progresso por projeto.

### Capacidades Modificadas

Nenhuma.

## Fora do escopo

- Guia personalizado pelo orientador para um orientando específico. O guia vale para todos os projetos que usam o grupo. Fica para a issue "Guia de estudo personalizado por vínculo de orientação" (a abrir).
- Exigir admin no configurador. Os anexos seguem a regra atual dos grupos de documentos, que aceita qualquer usuário autenticado. A decisão fica para a issue "Configurador aceita alterações de qualquer usuário autenticado" (a abrir).
- Outros tipos de anexo, como fonte normativa (`Source`), arquivo enviado ou vídeo.

## Impacto

- **Banco**: coluna `position` em `document_group_items`, com preenchimento pela data de criação; tabelas novas `study_attachments` e `study_progress`.
- **Rotas**: novas rotas em `/document-group` para ordenar itens e gerenciar anexos; `GET /project/{project_id}/study-guide` e rotas para marcar anexos como estudados.
- **Código**: `lumina/models.py`, `lumina/routers/check_tree/document_groups.py`, `lumina/routers/check_tree/projects.py`, `lumina/services/document_group_service.py`, serviço e repositório novos para o guia, cliente do Crossref.
- **Dependências**: nenhuma nova. O cliente do Crossref usa o `httpx`, que já está no ambiente e é usado em `notification_service.py`.
- **Configuração**: `CROSSREF_URL`, `CROSSREF_TIMEOUT_SECONDS` e `CROSSREF_MAILTO` (opcional, identifica o Lumina no pool educado do Crossref).
