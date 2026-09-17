# Lumina Back

API e motor de Inteligência Artificial para elaboração, revisão e auditoria normativa de documentos técnicos, editais de compras públicas e chamadas acadêmicas.

---

## 🛠️ Stack Tecnológica

* **Linguagem**: Python 3.13
* **Framework Web**: FastAPI
* **Gerenciador de Dependências**: [Poetry](https://python-poetry.org/)
* **Banco de Dados & ORM**: PostgreSQL, PGVector, SQLAlchemy 2.0 (Async), Alembic
* **Cache & Mensageria**: Redis, RabbitMQ
* **IA & LLMs**: LangChain, OpenAI (`gpt-5-mini`, `gpt-4o-mini`)
* **Testes & Qualidade**: Pytest, Testcontainers, Factory-Boy, Taskipy, Ruff

---

## 🚀 Comandos Essenciais

```bash
# Servidor de Desenvolvimento
poetry run task run

# Testes Automatizados (Padrão - Sem consumo de tokens)
poetry run task test

# Testes de IA Real (Consumo de tokens)
poetry run task test-ai

# Verificação e Formatação de Código
poetry run ruff check
poetry run ruff format
```

---

## 🧰 Scripts Úteis

O repositório disponibiliza scripts CLI auxiliares para manutenção, testes e carga da base de dados:

### 1. Análise Retroativa de Seções de Branches (`analyze-branches`)

Analisa as regras (`Branch`) já persistidas na base de dados utilizando o modelo rápido de IA (`get_fast_model()`) para inferir se o cumprimento da regra exige:
- `SPECIFIC_SECTION`: Busca direcionada em uma seção específica do documento (ex: 'Habilitação Jurídica', 'Qualificação Técnica').
- `ENTIRE_DOCUMENT`: Leitura transversal do documento inteiro (ex: formatação ABNT, clareza, ausência de rasuras).
- `UNKNOWN`: Regra com contexto insuficiente ou vago.

```bash
# Inspecionar as branches cadastradas sem chamar a LLM (Dry-Run)
poetry run task analyze-branches --dry-run

# Analisar apenas uma amostra (ex: primeiras 5 branches)
poetry run task analyze-branches --limit 5

# Executar a análise com controle de concorrência e salvar relatório consolidado em JSON
poetry run task analyze-branches --concurrency 5 -o lumina/storage/reports/branches_section_analysis.json

# Visualizar todas as opções disponíveis
poetry run task analyze-branches --help
```

### 2. Povoamento de Demonstração (`seed`)

Popula o banco de dados com perfis de usuários (orientadores, alunos), orientações acadêmicas, projetos e documentos de teste:

```bash
poetry run task seed
```

---

## 📚 Documentação

A documentação arquitetural e funcional completa está disponível no diretório `docs/` e pode ser visualizada via MkDocs:

```bash
poetry run task docs
```
