# 04 - Evolução dos Testes e Limpeza Pós-Refatoração

## A Vida Útil dos Testes de Caracterização

Os testes de caracterização cumprem um papel transitório essencial: servir de **rede de proteção** enquanto a estrutura antiga está sendo desmontada.

Porém, eles não devem permanecer com acoplamentos ao passado após a refatoração.

```text
+─────────────────────────────────+
| Código sem testes               |
+─────────────────────────────────+
                 │
                 ▼
+─────────────────────────────────+
| Testes de Caracterização        |  <── Fotografia do comportamento inicial
+─────────────────────────────────+
                 │
                 ▼
+─────────────────────────────────+
| Refatoração Estrutural          |  <── Desacoplamento passo a passo
+─────────────────────────────────+
                 │
                 ▼
+─────────────────────────────────+
| Código mais Simples e Limpo     |
+─────────────────────────────────+
                 │
                 ▼
+─────────────────────────────────+
| Testes de Comportamento/Domínio |  <── Testes expressivos do novo modelo
+─────────────────────────────────+
                 │
                 ▼
+─────────────────────────────────+
| Limpeza de Legado e Fixtures    |  <── Remoção de fixtures obsoletas
+─────────────────────────────────+
```

---

## 1. O que Manter vs. O que Limpar

### 🗑️ O que Limpar:
* **Fixtures obsoletas em `tests/conftest.py`**:
  * Remover factories que apontavam para o modelo removido (ex: `UnitFactory`).
  * Remover fixtures de sessão/função do modelo removido (ex: `@pytest_asyncio.fixture async def unit(...)`).
* **Testes unitários/de repo específicos do conceito excluído**:
  * Deletar `tests/api/routers/test_<entidade_antiga>.py`.
  * Deletar `tests/integration/repositories/test_<entidade_antiga>_repo.py`.
  * Deletar `tests/unit/services/test_<entidade_antiga>_service.py`.

### 🛡️ O que Manter e Evoluir:
* **Testes dos fluxos afetados**:
  * Remover parâmetros de fixture legada dos testes de caracterização (ex: tirar injeção de `unit`).
  * Remover asserções de campos obsoletos (ex: checagem de `total_units` em `/stats/kpis`).
  * Promover esses testes para a suíte permanente de integração da API (ex: `tests/api/routers/` ou `tests/api/characterization/`).

---

## 2. Critérios de Aceite Finais (Definition of Done)

Uma grande refatoração só está 100% concluída quando:

1. **Zero Referências Mortas**: Varredura global no repositório confirma ausência de imports quebrados ou resquícios do conceito antigo.
2. **Suíte 100% Verde**: `poetry run task test` executa todos os testes com sucesso.
3. **Formatação e Lint Impecáveis**:
   ```bash
   poetry run ruff check --fix
   poetry run ruff format
   ```
4. **Histórico Git Limpo**: Commits atômicos documentando cada etapa da refatoração.
