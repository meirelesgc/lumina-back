# Armadilhas Comuns e Lições Aprendidas (Pitfalls)

Durante a aplicação contínua de testes ou orquestração via agentes, certas falhas comuns costumam aparecer. Use as lições abaixo para se antecipar a esses erros de implementação:

## 1. Conflito de Namespaces (Import Collisions)
Quando criar testes usando subagentes em paralelo, evite ao máximo usar nomes de arquivos genéricos como `_api.py`, `_repo.py` ou `_service.py`. O Pytest pode encontrar colisões de namespace de importação ao juntar todas as branches.
**Solução:** Sempre utilize o contexto de domínio nos nomes dos arquivos (ex: `test_project_repo.py`, `test_taxonomy_service.py`).

## 2. Violação de Chave Estrangeira (ForeignKeyViolation)
Em testes de repositório de integração, é tentador utilizar falsos identificadores (`uuid4()`) para chaves estrangeiras como `created_by` ou `project_id`. Isso fará o banco de dados falhar miseravelmente com exceções de integridade relacional.
**Solução:** Sempre ancore relações em objetos previamente criados por Factories e persistidos no DB. Para trilhas de auditoria, utilize sempre o `user.id` vindo de uma fixture de sessão ativa ou instancie a respectiva `UserFactory`.

## 3. Erros 422 (Unprocessable Entity) Assumindo Pydantic
Não adivinhe o formato de payloads baseando-se no senso comum (ex: usar apenas `title` e `description`). Endpoints podem falhar silenciosamente ou retornar `422` se chaves obrigatórias como arrays vazios (`source_ids: []`) ou relacionamentos forem omitidos.
**Solução:** Sempre leia as especificações do `BaseModel` / Pydantic (como `BranchCreate`, `TaxonomyCreate`) antes de codificar o envio do `.post()` ou `.put()` nos testes de API. 

## 4. Congelamentos de Execução por Isolamento Lazy (Coroutines)
Ao usar fixtures que invocam ou interagem com sessões assíncronas de banco de dados (`async def fixture_name`), esquecer de decorá-las com `@pytest_asyncio.fixture` causará o erro: `AttributeError: 'coroutine' object has no attribute`.
Além de quebrar o teste individualmente, isso propaga objetos assíncronos que não foram aguardados, corrompendo a transação na conexão e causando deadlocks nos testes subsequentes.
**Solução:** Revise estritamente toda declaração de fixture. Se for assíncrona, não utilize apenas `@pytest.fixture`.
