# 02 - Passos Atômicos e Fatiamento de Mudanças

## O Anti-padrão do "Big Bang"
O erro mais frequente em grandes refatorações é tentar fazer tudo em uma única tacada:
```text
[Anti-padrão]
Apagar modelos ──> Deletar arquivos ──> Mudar serviços ──> Descobrir 40 quebras ──> Desespero
```

Esse padrão torna o Git inutilizável, dificulta identificar a causa de regressões e frequentemente leva ao abandono da refatoração.

---

## O Padrão de Passos Atômicos (Ciclo Verde $\rightarrow$ Verde)

Cada transformação deve ser uma transição pequena, independente e imediatamente testável:

```text
Testes Verdes
     │
     ▼
[Passo 1: Desacoplamento da Criação de Entidades]
     │
     ▼
Testes Verdes (poetry run task test)
     │
     ▼
[Passo 2: Desacoplamento de Notificações / Regras de Negócio]
     │
     ▼
Testes Verdes (poetry run task test)
     │
     ▼
[Passo 3: Remoção de Campos em Filtros e Schemas DTO]
     │
     ▼
Testes Verdes (poetry run task test)
     │
     ▼
[Passo 4: Remoção Física de Tabelas, Routers e Arquivos Obsoletos]
     │
     ▼
Testes Verdes (poetry run task test)
```

---

## Estratégia de Fatiamento Recomendada

### 1. Camada de Persistência / Modelos
* **Tornar campos opcionais primeiro**: Antes de remover colunas, altere colunas `NOT NULL` para `nullable=True` nos modelos SQLAlchemy.
* Isso garante que novas criações funcionem sem a dependência antes de remover o campo completamente.

### 2. Camada de Serviços e Regras de Negócio
* Desvincule a entidade antiga das operações de escrita (ex: remoção de `unit_id=current_user.unit_id`).
* Se houver notificações vinculadas (ex: notificar auditores da mesma unidade), altere a regra para um escopo independente (ex: notificar auditores globais ou do projeto).
* **Validação**: Execute os testes de caracterização para garantir que os fluxos continuam respondendo com sucesso.

### 3. Camada de Schemas (Pydantic) e Filtros
* Remova os campos obsoletos de `FilterPage`, `CreateSchema`, `UpdateSchema` e `PublicSchema`.
* Remova as cláusulas `.where(Model.col == filters.col)` dos repositórios.
* **Validação**: Testes de caracterização continuam passando sem enviar ou filtrar pelo campo obsoleto.

### 4. Remoção Física e Limpeza
* Remova os arquivos de rota (`routers/`), serviços (`services/`), repositórios (`repositories/`) e schemas (`schemas/`).
* Desregistre o roteador em `app.py`.
* Crie a migration Alembic de remoção de tabelas e FKs.
* **Validação**: Executar suíte completa (`poetry run task test`).
