# 03 - Segurança em Banco de Dados e Migrations Alembic

## Cuidados Críticos com Banco de Dados em Refatorações

Modificações no esquema do PostgreSQL via Alembic exigem disciplina para evitar deadlocks, violações de integridade referencial ou perda involuntária de dados em produção.

---

## 1. Ordem Correta para Remoção de Tabelas e Chaves Estrangeiras

Ao remover uma tabela pai (ex: `units`) que é referenciada por múltiplas tabelas filhas (ex: `users`, `documents`):

1. **Primeiro: Dropar as Foreign Keys filhas**:
   ```sql
   ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_user_unit_id CASCADE;
   ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_unit_id_fkey CASCADE;
   ```
2. **Segundo: Dropar as Colunas filhas**:
   ```sql
   ALTER TABLE users DROP COLUMN IF EXISTS unit_id CASCADE;
   ALTER TABLE documents DROP COLUMN IF EXISTS unit_id CASCADE;
   ```
3. **Terceiro: Dropar Índices específicos da tabela pai**:
   ```sql
   DROP INDEX IF EXISTS ix_units_tsv CASCADE;
   DROP INDEX IF EXISTS ix_uq_units_name_active CASCADE;
   ```
4. **Quarto: Dropar a Tabela pai**:
   ```sql
   DROP TABLE IF EXISTS units CASCADE;
   ```

---

## 2. Estrutura Padrão de Migration Alembic de Remoção

Utilize sempre comandos com `IF EXISTS` e `CASCADE` no `upgrade()` para garantir idempotência em ambientes de CI e containers de teste:

```python
"""remove units and unit_id references

Revision ID: 0006
Revises: 0005
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_user_unit_id CASCADE"))
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS unit_id CASCADE"))

    conn.execute(sa.text("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_unit_id_fkey CASCADE"))
    conn.execute(sa.text("ALTER TABLE documents DROP COLUMN IF EXISTS unit_id CASCADE"))

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_units_tsv CASCADE"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_uq_units_name_active CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS units CASCADE"))

def downgrade() -> None:
    # Recriação da estrutura original caso seja necessário rollback
    ...
```

---

## 3. Isolamento nos Testes (Testcontainers & Savepoints)

* O Lumina utiliza **Testcontainers** para subir instâncias reais do PostgreSQL nos testes.
* O `conftest.py` cria o esquema uma única vez no início da sessão e utiliza *Savepoints / Nested Transactions* para cada teste.
* Portanto, alterações no `lumina/models.py` e novas migrations são validadas de forma imediata e limpa pela suíte de testes.
