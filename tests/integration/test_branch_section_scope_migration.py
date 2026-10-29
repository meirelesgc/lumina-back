import os
import subprocess

import psycopg

BEFORE = 'ad86bd43da06'
TYPIFICATION = '00000000-0000-0000-0000-0000000000a1'
TAXONOMY = '00000000-0000-0000-0000-0000000000b1'
BRANCH = '00000000-0000-0000-0000-0000000000c1'
REQUIREMENT = '00000000-0000-0000-0000-0000000000d1'


def table_exists(conn, name: str) -> bool:
    found = conn.execute('SELECT to_regclass(%s)', (name,)).fetchone()[0]
    return found is not None


def test_migracao_deixa_ramos_existentes_sem_marcacao(engine):
    """Roda as migrações de verdade numa base separada do container de teste.

    A suíte cria as tabelas com `create_all`, então só uma base migrada pelo
    Alembic mostra o efeito sobre ramos já cadastrados e com classificação
    do LLM (OpenSpec: manual-branch-section-scope).
    """
    url = engine.url.set(drivername='postgresql')
    admin_dsn = url.render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute('DROP DATABASE IF EXISTS section_scope_check')
        conn.execute('CREATE DATABASE section_scope_check')

    db_url = url.set(database='section_scope_check')
    dsn = db_url.render_as_string(hide_password=False)
    env = {
        **os.environ,
        'DATABASE_URL': db_url.set(
            drivername='postgresql+psycopg'
        ).render_as_string(hide_password=False),
    }

    def alembic(*args):
        subprocess.run(
            ['alembic', *args], env=env, check=True, capture_output=True
        )

    alembic('upgrade', BEFORE)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "INSERT INTO typifications (id, name) VALUES (%s, 'Revisão')",
            (TYPIFICATION,),
        )
        conn.execute(
            'INSERT INTO taxonomies (id, title, description, typification_id)'
            " VALUES (%s, 'Métodos', '', %s)",
            (TAXONOMY, TYPIFICATION),
        )
        conn.execute(
            'INSERT INTO branches (id, title, description, taxonomy_id)'
            " VALUES (%s, 'Busca', 'Estratégia de busca', %s)",
            (BRANCH, TAXONOMY),
        )
        conn.execute(
            """
            INSERT INTO branch_section_requirements
                (id, branch_id, scope, expected_section, generation_model,
                 generation_version, is_active)
            VALUES (%s, %s, 'SPECIFIC_SECTION', 'Métodos', 'llm', 1, true)
            """,
            (REQUIREMENT, BRANCH),
        )

    alembic('upgrade', 'head')
    with psycopg.connect(dsn) as conn:
        marking = conn.execute(
            'SELECT section_scope, expected_section FROM branches'
        ).fetchall()
        assert marking == [('UNKNOWN', None)]
        assert not table_exists(conn, 'branch_section_requirements')

    alembic('downgrade', BEFORE)
    with psycopg.connect(dsn) as conn:
        assert table_exists(conn, 'branch_section_requirements')
        assert conn.execute(
            'SELECT count(*) FROM branch_section_requirements'
        ).fetchone() == (0,)
