# Diretrizes e Guia de Desenvolvimento para Agentes e Desenvolvedores — Lumina Back

Este documento reúne os padrões, comandos essenciais e boas práticas para o desenvolvimento e manutenção do repositório **Lumina Back**.

---

## 🛠️ Stack Tecnológica

* **Linguagem**: Python 3.13
* **Framework Web**: FastAPI
* **Gerenciador de Dependências & Ambiente**: [Poetry](https://python-poetry.org/)
* **Banco de Dados & ORM**: PostgreSQL, SQLAlchemy 2.0 (Async), Alembic
* **Cache & Mensageria**: Redis, RabbitMQ (Pika)
* **IA & LLMs**: LangChain, LangChain Community, OpenAI
* **Testes & Qualidade**: Pytest, Pytest-Asyncio, Testcontainers, Factory-Boy, Taskipy, Ruff

---

## 📌 Regra de Ouro: Uso do Poetry

> **IMPORTANTE**: Nunca execute ferramentas globais do sistema (`python`, `pytest`, `alembic`, `ruff`) diretamente sem o ambiente do Poetry.  
> **Sempre** utilize o prefixo `poetry run <comando>` ou ative a virtualenv via `poetry shell`.

---

## 🚀 Comandos Essenciais

O repositório utiliza o **Taskipy** para centralizar os comandos mais frequentes definidos no `pyproject.toml`.

### 1. Servidor de Desenvolvimento
```bash
# Inicia a API FastAPI em modo de desenvolvimento (com auto-reload)
poetry run task run
# Ou diretamente:
poetry run fastapi dev lumina/app.py
```

### 2. Testes Automatizados

* **Testes Padrão (CI/CD e Local - Sem Gasto de Tokens)**:
  Executa todos os testes unitários e de integração com cobertura. Os testes que chamam LLMs reais são **automaticamente ignorados**.
  ```bash
  poetry run task test
  ```

* **Testes de IA Real (Avaliação com consumo de tokens - Ambiente Local)**:
  Executa especificamente os testes marcados com `@pytest.mark.ai` que invocam chamadas reais a modelos de LLM.
  ```bash
  poetry run task test-ai
  ```

* **Todos os Testes (Incluindo IA Real)**:
  ```bash
  poetry run task test-all
  ```

* **Relatório HTML de Cobertura**:
  ```bash
  poetry run task cov
  # O relatório estará disponível em htmlcov/index.html
  ```

### 3. Linting e Formatação de Código (Ruff)
```bash
# Verificar problemas de lint
poetry run ruff check

# Corrigir problemas automaticamente
poetry run ruff check --fix

# Formatar o código
poetry run ruff format
```

### 4. Migrações de Banco de Dados (Alembic)
```bash
# Gerar nova migration após alterar modelos em lumina/models.py
poetry run alembic revision --autogenerate -m "descricao_da_mudanca"

# Aplicar migrações no banco de dados
poetry run alembic upgrade head

# Reverter a última migração aplicada
poetry run alembic downgrade -1
```

---

## 🧠 Boas Práticas para Testes com Inteligência Artificial

1. **Evite consumo desnecessário de tokens em testes rotineiros**:
   * Sempre que possível, utilize mocks (`unittest.mock.AsyncMock`, `MagicMock`) ou o `FakeListChatModel` do LangChain (ver fixtures em `tests/ai/fixtures/ai_fixtures.py`).
2. **Marcação de Testes de IA Real**:
   * Qualquer teste que precise fazer chamadas reais a APIs de LLMs externas **deve** ser decorado com `@pytest.mark.ai`:
     ```python
     @pytest.mark.ai
     @pytest.mark.asyncio
     async def test_minha_avaliacao_llm_real():
         ...
     ```
   * Isso garante que o teste seja pulado no CI/CD e na execução do `task test`, rodando somente quando a flag `--run-ai` (ou `task test-ai`) for fornecida.

---

## 🏛️ Padrões de Arquitetura e Código

* **Limite de Linha**: 79 caracteres (estilo PEP 8 / Ruff).
* **Aspas**: Aspas simples `'` por padrão.
* **Isolamento de Banco nos Testes**:
  * O `conftest.py` utiliza `Testcontainers` com transações aninhadas (*Savepoints*).
  * Nunca chame `create_all` ou `drop_all` em cada teste individual.
* **Typing e Modelos**:
  * Utilize tipagem estática e schemas Pydantic para validação de entrada/saída nos routers.
  * Mantenha a separação clara de responsabilidades entre `routers/`, `services/`, `repositories/` e `models.py`.
