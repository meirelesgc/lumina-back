# Otimizações de Performance na Execução de Testes

Quando a suíte de testes atinge centenas ou milhares de casos, a velocidade de execução se torna crítica para a experiência de desenvolvimento.

## 1. Reuso do Schema de Banco de Dados (Transações)
- **O Problema:** Rodar `metadata.create_all` e `metadata.drop_all` antes e depois de cada teste adiciona muito atraso de I/O de rede/disco.
- **A Solução:** O banco e as tabelas devem ser criados *apenas uma vez* no início da sessão (fixture `scope="session"`).
- **Isolamento de Testes:** A cada teste, inicia-se uma nova transação. Ao final do teste, executa-se um `rollback()`, mantendo o banco limpo para o próximo teste de forma muito mais rápida que dropar as tabelas.

## 2. Isolamento e Organização de Factories
- **O Problema:** O `conftest.py` na raiz do projeto tende a virar um arquivo gigantesco e insustentável.
- **A Solução:** Extrair a criação de massas de dados (Factory Boy) para arquivos dedicados na pasta `tests/factories/` (ex: `user_factory.py`). As fixtures devem ser declaradas em arquivos específicos e carregadas no `conftest.py` base via `pytest_plugins = ["tests.fixtures.db", "tests.fixtures.users"]`.

## 3. Mock de Serviços de Rede Externos
- **O Problema:** Chamadas a APIs de LLM, serviços em nuvem ou provedores externos deixam o teste lento, encarecem a conta e causam falsos negativos (flaky tests).
- **A Solução:** Usar injeção de dependências ou ferramentas como `respx` para mockar as chamadas HTTP ou instâncias de serviços (`ai_service`, `storage_service`) em cenários unitários e de integração local.

## 4. Otimização de Criação de Token JWT
- **O Problema:** O hash de senha padrão (Bcrypt) leva intencionalmente cerca de 300ms a 500ms para dificultar ataques. Quando dezenas de testes de API chamam a rota real de login, isso custa minutos.
- **A Solução:** Criar uma fixture `auth_token` que pula o hashing do banco e apenas gera e assina um JWT válido usando a `SECRET_KEY` do projeto em memória.
