# Tasks

## 1. Modelo e migração

- [ ] 1.1 Adicionar `position` a `DocumentGroupItem` e criar `StudyAttachment` e `StudyProgress` em `lumina/models.py`, com as restrições e índices da decisão 1 do `design.md`. Gerar a migração Alembic com o preenchimento de `position` descrito no plano de migração e verificar com `poetry run alembic upgrade head` seguido de `poetry run alembic downgrade -1` e `upgrade head` numa base com grupos e itens existentes

## 2. Ordem dos itens do grupo (`document-groups`)

- [ ] 2.1 Escrever testes em `tests/api/check_tree/test_document_groups_api.py`: item novo entra no fim, listagens ordenadas por posição sem itens excluídos, reordenação bem-sucedida, lista incompleta ou com id estranho (422), grupo inexistente (404). Confirmar que falham antes da mudança
- [ ] 2.2 Escrever teste em `tests/integration/check_tree/test_document_groups_repo.py` para o preenchimento de `position` pela data de criação. Confirmar que falha antes da migração
- [ ] 2.3 Implementar a posição no `create_item`, o filtro e a ordem nas consultas de `document_group_repo.py` e a rota `PUT /document-group/{group_id}/items/order`. Verificar que os testes de 2.1 e 2.2 passam

## 3. Cliente do Crossref e normalização do DOI

- [ ] 3.1 Escrever testes unitários em `tests/unit/services/test_crossref_client.py`: normalização com e sem prefixos (`doi:`, `https://doi.org/`, `https://dx.doi.org/`), caixa, DOIs inválidos; leitura de título, autores, ano e veículo de uma resposta do Crossref; `None` para 404, 500, timeout e JSON inesperado, usando `httpx.MockTransport`. Confirmar que falham antes da mudança
- [ ] 3.2 Adicionar `CROSSREF_URL`, `CROSSREF_TIMEOUT_SECONDS` e `CROSSREF_MAILTO` em `lumina/core/settings.py` e implementar `lumina/services/crossref_client.py`. Verificar que os testes de 3.1 passam

## 4. Anexos de estudo (`study-guide`)

- [ ] 4.1 Escrever testes em `tests/api/check_tree/test_study_attachments_api.py` cobrindo os cenários dos requisitos de cadastro, tipificação, DOI, metadados do Crossref (com `fetch_doi_metadata` substituído por stub), link, listar, editar, reordenar, excluir e tipificação excluída. Incluir as recusas da jornada da Helena: tipificação repetida (409), link sem título e link `ftp` (422), DOI repetido com outro prefixo e outra caixa (409) e edição de descrição sem nova consulta ao Crossref. Confirmar que falham antes da mudança
- [ ] 4.2 Criar os schemas em `lumina/schemas/study_attachment.py`, o repositório `lumina/repositories/study_attachment_repo.py`, o serviço `lumina/services/study_attachment_service.py` e as rotas em `lumina/routers/check_tree/document_groups.py`. Verificar que os testes de 4.1 passam

## 5. Guia de estudo e progresso do projeto

- [ ] 5.1 Escrever testes em `tests/api/check_tree/test_study_guide_api.py` cobrindo os cenários dos requisitos "Guia de estudo do projeto" e "Marcar anexo como estudado": guia do dono, orientador e admin lendo o guia (200), projeto sem grupo, terceiro sem acesso (403), projeto inexistente ou excluído (404), marcar, marcar duas vezes, desmarcar, orientador e admin não dono tentando marcar (403), anexo fora do grupo ou oculto por tipificação excluída (404), tipificação excluída e anexo marcado excluído saindo do total e dos estudados, progresso separado por projeto. Confirmar que falham antes da mudança
- [ ] 5.2 Implementar `lumina/services/study_guide_service.py` e as rotas `GET /project/{project_id}/study-guide` e `PUT`/`DELETE /project/{project_id}/study-guide/attachment/{attachment_id}/studied` em `lumina/routers/check_tree/projects.py`. Verificar que os testes de 5.1 passam

## 6. Jornadas e documentação

- [ ] 6.1 Escrever `tests/api/journeys/test_trilha_da_helena.py` com a jornada "A trilha da Helena" da decisão 7 do `design.md`, passos numerados nos comentários e Crossref substituído por stub que conta as chamadas. Verificar que passa
- [ ] 6.2 Escrever `tests/api/journeys/test_semestre_do_pedro.py` com a jornada "O semestre do Pedro" da decisão 7 do `design.md`, com troca explícita de ator entre Pedro e Marina. Verificar que passa
- [ ] 6.3 Criar `docs/guia-de-estudo.md` com o exemplo do grupo TCC, os tipos de anexo, a consulta ao Crossref e as regras de acesso, e incluir a página na navegação de `mkdocs.yml`. Verificar com `poetry run task docs-build`

## 7. Verificação final

- [ ] 7.1 Rodar `poetry run task test` e registrar aqui o resultado que de fato rodou

## Workflow follow-up

- Commitar os artefatos (`docs(openspec): ...`) separados do código e dos testes (`feat(...)`).
- Arquivar a mudança depois da revisão.
