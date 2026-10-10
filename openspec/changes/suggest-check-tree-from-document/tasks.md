## 1. Modelo de dados e configuração

- [x] 1.1 Adicionar em `lumina/core/settings.py` as configurações `TREE_SUGGESTION_*` (tamanho máximo, páginas máximas, timeout, orçamento de lote, concorrência, score mínimo de evidência) e verificar a leitura com `poetry run python -c "from lumina.core.settings import Settings; print(Settings().TREE_SUGGESTION_MAX_PAGES)"`
- [x] 1.2 Criar os enums (`TreeSuggestionMode`, `TreeSuggestionStatus`, `TreeSuggestionItemKind`, `TreeSuggestionItemOperation`, `TreeSuggestionItemStatus`) e os modelos `TreeSuggestionSession` e `TreeSuggestionItem` em `lumina/models.py`, conforme o design §1; verificar que a importação de `lumina.models` não falha
- [x] 1.3 Gerar a migração Alembic das duas tabelas com os índices do Migration Plan e verificar com `alembic upgrade head` seguido de `alembic downgrade -1` e `alembic upgrade head`
- [x] 1.4 Adicionar a dependência `rapidfuzz` via Poetry e verificar `poetry run python -c "import rapidfuzz"`

## 2. Services existentes: modo sem commit

- [x] 2.1 Adicionar `commit: bool = True` em `source_service.create_source`, `typification_service.create_typification`, `taxonomy_service.create_taxonomy/update_taxonomy` e `branch_service.create_branch/update_branch` (com `commit=False` apenas fazem flush e, no Branch, não disparam o background); verificar que a suíte atual dos CRUDs continua passando
- [x] 2.2 Extrair `branch_service.dispatch_branch_enrichment` a partir do disparo atual de análise de seção e expansão de consultas, e cobrir com teste unitário que `commit=False` não dispara nada e que o helper dispara as duas tarefas

## 3. Repositório e schemas

- [x] 3.1 Criar `lumina/repositories/tree_suggestion_repo.py` com: criar sessão, obter sessão com itens, listar com filtro e paginação, obter item com `FOR UPDATE`, coletar descendentes pendentes (CTE recursiva), contar pendentes e inserir itens em lote; verificar com testes de integração em `tests/integration/repositories/`
- [x] 3.2 Criar `lumina/schemas/tree_suggestion.py` (`TreeSuggestionSessionPublic`, `TreeSuggestionSessionDetail`, `TreeSuggestionSessionList`, `TreeSuggestionItemPublic`, `TreeSuggestionItemConfirm`, `TreeSuggestionFilter`, `Evidence`) e exportá-los em `lumina/schemas/__init__.py`; verificar serialização com teste unitário de `model_validate` a partir dos modelos ORM

## 4. Motor de geração (IA)

- [x] 4.1 Criar `lumina/services/ai/tree_suggestion/` com os modelos Pydantic de saída estruturada (escopo, candidatos de regra, árvore consolidada) e os prompts em português; verificar que a importação do pacote funciona
- [x] 4.2 Implementar a etapa de extração reutilizando `extract_raw_markdown_and_pages`, `build_sections_tree_from_markdown` e o agrupamento de seções em lotes por `TREE_SUGGESTION_BATCH_CHARS`; verificar com teste unitário que nenhum lote excede o orçamento (salvo seção única maior que ele) e que a ordem é preservada
- [x] 4.3 Implementar a validação determinística de evidência (normalização, busca exata, fallback `rapidfuzz.partial_ratio` e mapeamento offset→páginas base 1 via `page_map`); verificar com testes unitários de trecho exato, trecho com quebra de linha/hífen, trecho inexistente (rejeitado) e páginas corretas
- [x] 4.4 Implementar a deduplicação determinística por título normalizado no escopo correto (global para tipificação, por tipificação para taxonomia, por taxonomia para ramo); verificar com testes unitários
- [x] 4.5 Implementar `generate_tree_suggestions` orquestrando escopo → regras (map com semáforo) → evidência → consolidação → duplicatas, validando IDs devolvidos pelo LLM contra a subárvore existente e registrando etapas no `run_logger`; verificar com testes unitários usando modelo fake (override) nos modos `create` (múltiplas tipificações) e `enrich` (itens `create` e `update`, nenhum de remoção)

## 5. Service de sessões de sugestão

- [x] 5.1 Implementar em `lumina/services/tree_suggestion_service.py` a criação da sessão (validação de content-type e magic bytes, tamanho, páginas, tipificação alvo ativa), o salvamento do arquivo via `Storage` e o agendamento do background; verificar com testes os erros 415, 413 e 404 e o caso de sucesso em `processing`
- [x] 5.2 Implementar `run_tree_suggestion_background` (sessão de banco própria, carga da subárvore, persistência transacional dos itens com `position`, `target_snapshot` e exatamente um item `source`, transição para `ready` ou `failed` com mensagem sanitizada); verificar com testes de sucesso, de geração sem regras (apenas o Source) e de falha
- [x] 5.3 Implementar leitura e listagem com timeout preguiçoso de `processing`; verificar com teste que uma sessão antiga em `processing` é retornada como `failed`
- [x] 5.4 Implementar `confirm_item` conforme o design §4 (lock, checagem de status da sessão, resolução de pai, checagem de snapshot em `update`, aplicação via services com `commit=False`, vínculo com o Source, `completed` automático, commit único e disparo do enriquecimento de Branch); verificar com testes de: criação com edição, pai pendente (409), filho de pai confirmado, update válido, update obsoleto (409), item não pendente (409), sessão não pronta (409) e colisão de título (409, item continua `pending`)
- [x] 5.5 Implementar a confirmação do item `source` (cria o Source com o arquivo da sessão e vincula às tipificações e taxonomias já aplicadas e à tipificação alvo no modo `enrich`) e o vínculo das confirmações posteriores; verificar com testes as duas ordens de confirmação e o caso de Source descartado
- [x] 5.6 Implementar `discard_item` (cascata nos descendentes pendentes) e `discard_session`; verificar com testes a cascata, a preservação dos itens confirmados e a transição para `completed`

## 6. API

- [x] 6.1 Criar `lumina/routers/check_tree/tree_suggestions.py` com os seis endpoints do design §6, protegidos por `CurrentUser`, e registrar o router em `lumina/app.py`; verificar que as rotas aparecem em `/openapi.json`
- [x] 6.2 Resolver `target_typification_name` e `parent_entity_title` na leitura da sessão e verificar nos testes de serviço e de API que os rótulos refletem os nomes atuais
- [x] 6.3 Adicionar testes de API em `tests/api/check_tree/test_tree_suggestions_api.py` cobrindo o fluxo ponta a ponta (upload → background com modelo fake → leitura → confirmações → descarte → `completed`) e 401 sem autenticação; verificar com `poetry run pytest tests/api/check_tree/test_tree_suggestions_api.py`

## 7. Documentação e verificação final

- [x] 7.1 Documentar o fluxo de sugestões em `docs/base-de-conhecimento.md` (seção da árvore de verificação) e verificar com `poetry run task docs-build`
- [x] 7.2 Executar `poetry run task test` sem falhas, `ruff check` e `ruff format --check` sem erros novos nos arquivos alterados (o projeto já tem pendências de lint anteriores a esta mudança), e `openspec validate suggest-check-tree-from-document --strict` sem erros

## 8. Somente regras de conteúdo

- [ ] 8.1 Adicionar a coluna JSONB `excluded_rules` (padrão lista vazia) em `TreeSuggestionSession`, com nova migração Alembic, e o campo `excluded_rules: list[ExcludedRule]` nos schemas de sessão; verificar com `alembic upgrade head`/`downgrade -1`/`upgrade head` e com o teste de serialização dos schemas
- [ ] 8.2 Adicionar `rule_type` (`content` | `formatting`) ao `RuleCandidate`, com a definição de formatação × conteúdo no prompt de extração, e separar no gerador as regras `formatting` verificadas em `excluded_rules` (deduplicadas, fora da consolidação); verificar com testes unitários do gerador: regra de formatação não vira item, aparece em `excluded_rules` com páginas, regra sem evidência não aparece e taxonomia só de formatação não é criada
- [ ] 8.3 Persistir `excluded_rules` na sessão ao concluir a geração e expô-las na leitura; ajustar as fixtures e os testes de serviço e de API para usar regras de conteúdo e cobrir as excluídas; verificar com `poetry run pytest tests/integration/test_tree_suggestion_service.py tests/api/check_tree/test_tree_suggestions_api.py`
- [ ] 8.4 Exibir na demo `/demos/tree_suggestions/` uma seção somente leitura "Fora do escopo da árvore (formatação)" e trocar o modo exemplo para regras de conteúdo; verificar exercitando o modo exemplo
- [ ] 8.5 Atualizar `docs/base-de-conhecimento.md`, rodar a suíte completa e o lint dos arquivos alterados, e `openspec validate suggest-check-tree-from-document --strict` sem erros
