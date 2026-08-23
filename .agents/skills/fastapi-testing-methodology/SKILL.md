---
name: fastapi-testing-methodology
description: Diretrizes e padrões para arquitetura de testes, otimização de execução, matriz de risco e critérios de aceite em projetos FastAPI com pytest, testcontainers e factory_boy.
---

# FastAPI Testing Methodology

Esta skill documenta a metodologia padrão de testes para este projeto (FastAPI). 
O objetivo principal é garantir que a suíte de testes seja focada em **risco e comportamento**, não apenas em cobertura de linhas cega, além de escalar com boa performance (otimizações de banco de dados e mocks).

Quando você estiver implementando novos testes ou refatorando os existentes, consulte as referências e templates abaixo para garantir que está seguindo o padrão.

## Referências da Metodologia
Para entender as regras teóricas, leia os arquivos abaixo na pasta `references/`:

1. [Arquitetura e Camadas de Testes](./references/01-architecture-layers.md)
2. [Otimizações de Performance](./references/02-performance-optimizations.md)
3. [Cobertura e Matriz de Risco](./references/03-risk-and-coverage.md)
4. [Definition of Done (Critérios de Parada)](./references/04-definition-of-done.md)
5. [Armadilhas Comuns e Pitfalls](./references/05-common-pitfalls.md)
6. [Padrões de Testes para IA (AI Testing Standards)](./references/06-ai-testing-standards.md)


## Templates e Exemplos Práticos
Ao criar novos arquivos, você pode usar os templates abaixo da pasta `templates/` como base:

* [conftest_base.py](./templates/conftest_base.py): Exemplo de setup de DB rápido com transações.
* [test_service_example.py](./templates/test_service_example.py): Exemplo de Teste de Unidade mockando o repository.
* [test_repository_example.py](./templates/test_repository_example.py): Exemplo de Teste de Integração validando dados reais.
* [test_api_example.py](./templates/test_api_example.py): Exemplo de Teste de Integração de API (Roteador).

## Regras de Execução e Performance (Pytest)
Ao escalar a suíte de testes (especialmente testes de banco de dados via `testcontainers`), certifique-se de respeitar as seguintes diretrizes para evitar deadlocks e lentidão extrema:

1. **Testes Paralelos com Xdist (`--dist loadscope`)**: Se utilizar o `pytest-xdist` para execução paralela, **sempre** utilize a flag `--dist loadscope`. Isso agrupa os testes por módulo/classe e garante que os workers não disputem ou causem concorrência não tratada nas fixtures de mesma sessão.
2. **Isolamento de Conexão com Nested Transactions (Savepoints)**: Nunca execute `drop_all` e `create_all` para cada teste isoladamente. O teardown agressivo exauste as conexões e derruba o container. A arquitetura correta (`tests/conftest.py`) cria as tabelas uma única vez na sessão (via `autouse=True`) e injeta o `session` abrindo e dando `rollback` em _Savepoints_ (Nested Transactions) para resetar o estado de forma ultra-rápida.
