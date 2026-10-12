# Aplicação neste repositório (pi\*VMA)

Como a metodologia se traduz na suíte atual. Confira o código antes de usar:
nomes de fixtures e helpers podem mudar.

## Onde ficam os testes

| Camada | Diretório |
|---|---|
| Jornada | `tests/integration/journeys/etapa_<n>_<nome>/` |
| Contrato da interface | `tests/api/routers/` |
| Integração com banco | `tests/integration/database/` |
| Migrações | `tests/integration/migrations/` |
| Provisionamento | `tests/integration/bootstrap/` |
| Pré-avaliação por IA (fake) | `tests/integration/ai/` |
| Notificações | `tests/integration/notifications/` e `tests/unit/notifications/` |
| Unitário | `tests/unit/` |

As jornadas são agrupadas pela etapa do processo em que o usuário está, não
pela rota.

## Infraestrutura

- PostgreSQL com pgvector sobe uma vez por sessão via Testcontainers
  (`tests/conftest.py`). Cada teste roda em transação com savepoint e
  rollback.
- `client` é o `TestClient` com a sessão do teste injetada.
- A pré-avaliação em segundo plano fica desligada por fixture `autouse`. Para
  observar o resultado, chame a execução explicitamente
  (`pre_evaluation_service._execute`), como em
  `etapa_1_submissao_triagem/test_return_review_via_ai.py`.
- `fake_provider` injeta o provedor de IA determinístico.
- Factories ficam em `tests/factories/`.

## Helpers das jornadas

Em `tests/integration/journeys/conftest.py`:

| Helper | Ação do usuário |
|---|---|
| `bootstrap_fresh_deploy(session, monkeypatch)` | Ambiente novo: perfis, permissões, templates e administrador inicial |
| `journey_client` | Cliente com `Origin` confiável, como o navegador |
| `sign_up(client, username)` | Cadastro público |
| `log_in(client, identifier, password=PASSWORD)` | Login por cookie, limpando a sessão anterior |
| `log_out(client)` | Saída |
| `process_tasks(client, process_id)` | Tarefas visíveis ao usuário logado, por atividade |

Para conceder perfis globais, entre como administrador
(`ADMIN_EMAIL`, `ADMIN_PASSWORD`) e use a rota pública de RBAC, como faria
a pessoa responsável.

## Convenções

- A descrição da jornada vai na docstring do módulo, com a spec e a história
  de origem (ex.: "Spec 030, US4").
- Acompanhe pendências por `GET /tasks`, como o frontend: um ator só age
  quando aparece uma tarefa `READY` para ele.
- Rotas mutáveis exigem `Origin` confiável. Use `journey_client`.
- Erros seguem `{"detail": {"code", "message"}}`. Nos testes focados,
  verifique o `code`, não a mensagem.
- Listagens respondem em `data` com `pagination`.

## Comandos

```bash
poetry run pytest tests/integration/journeys
poetry run pytest tests/api/routers/test_<dominio>.py
```
