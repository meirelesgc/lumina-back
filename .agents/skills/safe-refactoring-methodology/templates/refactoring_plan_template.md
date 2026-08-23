# Template: Plano de Refatoração Segura em Grandes Mudanças

## 1. Visão Geral e Contexto
* **Conceito/Estrutura a ser Refatorada**: [Descrição]
* **Motivação e Novo Modelo de Domínio**: [Descrição]
* **Objetivo de Comportamento**: [Preservar comportamento existente sem quebras]

---

## 2. Mapa de Impacto no Código
Identificação dos pontos de acoplamento em cada camada:
* **Banco de Dados & Modelos**: [Tabelas, FKs, colunas nullable/not null, índices]
* **Repositórios & Queries**: [Filtros, joins, buscas full-text]
* **Serviços & Regras de Negócio**: [Instanciações, validações, notificações]
* **API, Routers & Schemas**: [Endpoints, DTOs de entrada/saída, parâmetros de paginação]
* **Testes & Fixtures**: [Fixtures em `conftest.py`, factories e mocks]

---

## 3. Fases de Execução

### Fase 1: Rede de Proteção (Characterization Tests)
* Criar arquivo de testes fotografando os fluxos reais afetados:
  * Fluxo 1: [Entrada -> Saída]
  * Fluxo 2: [Entrada -> Saída]
* **Critério de Saída**: `poetry run task test` 100% verde antes de qualquer alteração de produção.

### Fase 2: Passos Atômicos Incrementais (Verde -> Verde)
* **Passo 2.1**: Desacoplamento da persistência (tornar colunas opcionais nos modelos).
* **Passo 2.2**: Desacoplamento de regras de serviço e notificações.
* **Passo 2.3**: Limpeza de schemas (DTOs) e repositórios.
* **Passo 2.4**: Remoção física (migration Alembic, deleção de arquivos obsoletos).

### Fase 3: Pós-Refatoração e Limpeza
* Remover factories e fixtures obsoletas de `conftest.py`.
* Promover testes de caracterização a testes permanentes de domínio.
* Executar `poetry run task test`, `poetry run ruff check` e `poetry run ruff format`.
