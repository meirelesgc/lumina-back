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
- `tests/unit/services/test_ingestion_sections.py` encontra os gabaritos
  sozinho. Documento novo no acervo não pede teste novo: rode o arquivo e
  decida pelo resultado, como descreve `tests/fixtures/documents/README.md`.
  O piso `MIN_SECTION_IDENTIFICATION_RATE` fica no próprio teste.
- Para comparar com o comportamento anterior a uma correção, rode o mesmo
  teste num `git worktree` do commit anterior. O teste de hoje mede o código
  de ontem sem que ninguém precise ter escrito o teste antes.
- Com `DEBUG_INGESTION_AUDIT=True` no `.env`, os testes de ingestão gravam a
  auditoria em `lumina/storage/ingestion_audit/` (fora do git). Para medir
  tempo, rode com `DEBUG_INGESTION_AUDIT=False`.
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
poetry run pytest tests/unit/services/test_ingestion_sections.py -s
```
