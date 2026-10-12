# Aplicação neste repositório (Lumina)

Como a metodologia se traduz na suíte atual. Confira o código antes de usar:
nomes de fixtures e helpers podem mudar.

## Onde ficam os testes

| Camada | Diretório |
|---|---|
| Contrato das rotas | `tests/api/routers/`, `tests/api/check_tree/` e `tests/routers/` (mais antigo) |
| Caracterização de fluxos | `tests/api/characterization/` |
| Integração com banco | `tests/integration/repositories/`, `tests/integration/check_tree/` |
| Unitário, incluindo os estágios do pipeline de IA | `tests/unit/`, `tests/unit/services/` |
| Avaliação de qualidade da IA (chamadas reais) | `tests/ai/evaluation/` |
| Acervo de PDFs com gabarito de seções | `tests/fixtures/documents/` |
| Factories | `tests/factories/` |

O Lumina ainda não tem testes de jornada. Combine o diretório com o time na
primeira mudança que criar um.

## Infraestrutura

Em `tests/conftest.py`:

- PostgreSQL 16 sobe uma vez por sessão via Testcontainers. Cada teste roda
  em transação com savepoint e rollback (`session`).
- `client` é o `TestClient` com a sessão do teste injetada.
- `user` e `other_user` criam usuários com a senha em `clean_password`.
  `token` faz login por `POST /auth/token`. As rotas autenticadas recebem
  `headers={'Authorization': f'Bearer {token}'}`.
- `mock_fast_model_for_tests` (`autouse`) troca o modelo rápido por um mock
  com resposta fixa, a menos que a suíte rode com `--run-ai`.
- `isolate_background_task_db_writes` (`autouse`) dá uma sessão nula às
  tarefas em segundo plano de `branch_analyzer`, `query_expansion_service` e
  `tree_suggestion_service`. Para observar o efeito delas, chame a função
  diretamente no teste.
- `mock_db_time` fixa `created_at` e `updated_at` de um modelo.

## Convenções

- Testes que chamam modelos reais levam `@pytest.mark.ai`. A suíte padrão os
  pula.
- Testes de ingestão leem os PDFs de `tests/fixtures/documents/` pelo
  caminho relativo a essa pasta e não copiam os arquivos. O gabarito
  `<nome>.sections.yaml` fica ao lado do PDF. Siga a seção "Extração
  determinística" de [05-ia.md](05-ia.md) para as tolerâncias.
- Erros das rotas seguem o formato do FastAPI, `{"detail": ...}`.
- Mudanças de comportamento passam pelo OpenSpec. Os testes previstos vão em
  `tasks.md` da mudança, com o caminho do arquivo de teste.

## Comandos

```bash
poetry run task test
```

```bash
poetry run task test-ai
```

```bash
poetry run pytest tests/unit/services/test_chunking.py
```
