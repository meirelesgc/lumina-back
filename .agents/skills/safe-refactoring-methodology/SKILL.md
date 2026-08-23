---
name: safe-refactoring-methodology
description: Diretrizes, padrões e fluxos de execução para grandes refatorações e mudanças estruturais seguras no Lumina Back utilizando Testes de Caracterização (Characterization Testing), passos atômicos incrementais e preservação estrita de comportamento.
---

# Safe Refactoring Methodology — Lumina Back

Esta skill documenta a metodologia oficial para **grandes refatorações**, mudanças de arquitetura e remoção/substituição de conceitos estruturais legados no **Lumina Back**.

O objetivo primordial é permitir transformações profundas no código sem interromper o funcionamento da aplicação, sem quebras inesperadas no banco de dados e sem "apagar metade do projeto para torcer para funcionar".

---

## 🧭 Princípio Fundamental

> **Separar com rigor duas coisas:**
> 1. Mudar a **arquitetura/organização** interna;
> 2. Mudar o **comportamento** do sistema.
>
> A refatoração consiste em realizar transformações estruturais que **preservam estritamente o comportamento observável**, em passos pequenos, contínuos e verificáveis.

---

## 🔄 O Ciclo de 4 Etapas da Refatoração Segura

```
+-------------------------------------------------------------+
| Etapa 1: Diagnóstico e Mapeamento de Impacto                |
| Mapear todas as camadas (DB, Repos, Serviços, Routers, DTOs)|
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Etapa 2: Rede de Proteção (Characterization Tests)          |
| Fotografar o comportamento atual dos fluxos afetados        |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Etapa 3: Passos Atômicos Incrementais (Verde -> Verde)      |
| Mudança pequena -> Suíte passa -> Próxima micro-mudança     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Etapa 4: Pós-Refatoração e Evolução dos Testes              |
| Promover testes a domínio permanente e limpar legado        |
+-------------------------------------------------------------+
```

---

## 🛠️ Detalhamento das Etapas

### 1. Diagnóstico e Mapeamento de Impacto
Não comece alterando código. Faça uma varredura completa identificando o acoplamento do conceito a ser refatorado nas 6 camadas:
* **Banco de Dados & Modelos**: Tabelas, colunas (atenção a `NOT NULL`), FKs, índices parciais e TSV.
* **Repositórios**: Queries, joins, filtros opcionais e buscas textuais.
* **Serviços**: Regras de negócio, instanciações diretas de entidades e disparos de eventos/filas.
* **API & Schemas**: DTOs de entrada (`Create`, `Update`), filtros (`FilterPage`) e responses (`Public`).
* **Endpoints & Routers**: Prefixos de rotas, dependências injetadas e métricas/KPIs.
* **Testes & Fixtures**: Fixtures globais (`conftest.py`), factories e mocks existentes.

---

### 2. Rede de Proteção (Testes de Caracterização)
* **Regra**: Não tente testar o sistema inteiro antes de começar; foque **exclusivamente nos fluxos que serão afetados** pela refatoração.
* **Conceito**: *Characterization Tests* capturam **o que o sistema atualmente faz** (fotografia do comportamento real: entradas $A, B, C \rightarrow$ saídas $X, Y, Z$).
* **Foco no Comportamento**: O teste valida o contrato da API e o fluxo de negócio, não o local dos arquivos ou a estrutura interna de classes.
* **Critério de Saída**: Os testes de caracterização devem estar **100% verdes** antes de qualquer linha de código de produção ser modificada.

---

### 3. Passos Atômicos Incrementais (Ciclo Verde $\rightarrow$ Verde)
A refatoração nunca deve ser feita em um único bloco monolítico. Divida a mudança em micro-passos independentes:

1. **Desacoplar Banco e Modelos Primeiro**:
   * Tornar colunas obrigatórias em opcionais (`nullable=True`) no modelo e migration intermediária antes de remover dependências de código.
2. **Desacoplar Regras de Negócio e Serviços**:
   * Remover atribuições obrigatórias no `create_*` e desvincular notificações ou regras do conceito antigo.
   * *Executar testes $\rightarrow$ Garantir Verde*.
3. **Limpeza de Schemas de Entrada e Filtros**:
   * Remover campos dos DTOs e dos repositórios.
   * *Executar testes $\rightarrow$ Garantir Verde*.
4. **Remoção Física Final**:
   * Gerar migration Alembic para dropar tabelas, FKs, índices e colunas.
   * Deletar routers, repositórios, schemas e serviços obsoletos.
   * *Executar testes $\rightarrow$ Garantir Verde*.

---

### 4. Pós-Refatoração e Evolução dos Testes
* **Eliminar Acoplamento com o Passado**: Testes de caracterização podem conter fixtures ou dados de setup do modelo antigo; ajuste-os para a nova realidade.
* **Promover para Testes de Comportamento**: Transforme a suíte temporária em testes expressivos do novo domínio.
* **Exclusão de Fixtures Mortas**: Remova factories e fixtures de `conftest.py` que não têm mais utilidade.
* **Auditoria de Qualidade**: Rodar `poetry run task test`, `poetry run ruff check` e `poetry run ruff format`.

---

## 📚 Documentos de Referência

Para aprofundar em cada aspecto técnico, consulte os guias na pasta `references/`:

1. [Testes de Caracterização (Characterization Testing)](./references/01-characterization-testing.md)
2. [Passos Atômicos e Fatiamento de Mudanças](./references/02-atomic-refactoring-steps.md)
3. [Segurança em Banco de Dados e Migrations Alembic](./references/03-database-and-migrations-safety.md)
4. [Evolução dos Testes e Limpeza Pós-Refatoração](./references/04-post-refactoring-test-evolution.md)

---

## 📋 Templates Práticos

* [Template de Teste de Caracterização](./templates/characterization_test_template.py)
* [Template de Plano de Refatoração (Markdown)](./templates/refactoring_plan_template.md)
