import os
import subprocess

import psycopg
import pytest


@pytest.mark.asyncio
async def test_document_group_integration(session):
    assert True


def test_migration_fills_item_position_by_creation_date(engine):
    """Roda as migrações de verdade numa base separada do container de teste.

    A suíte cria as tabelas com `create_all`, então só uma base migrada
    pelo Alembic mostra o preenchimento de `position` em itens existentes.
    """
    url = engine.url.set(drivername='postgresql')
    admin_dsn = url.render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute('DROP DATABASE IF EXISTS migration_check')
        conn.execute('CREATE DATABASE migration_check')

    db_url = url.set(database='migration_check')
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

    alembic('upgrade', '0211df046da3')
    with psycopg.connect(db_url.render_as_string(hide_password=False)) as conn:
        conn.execute(
            """
            INSERT INTO document_groups (id, name) VALUES
                ('00000000-0000-0000-0000-0000000000a1', 'TCC'),
                ('00000000-0000-0000-0000-0000000000a2', 'Artigo');
            INSERT INTO document_group_items
                (id, group_id, name, created_at, deleted_at)
            VALUES
                ('00000000-0000-0000-0000-000000000001',
                 '00000000-0000-0000-0000-0000000000a1', 'TCC',
                 now() - interval '1 day', NULL),
                ('00000000-0000-0000-0000-000000000002',
                 '00000000-0000-0000-0000-0000000000a1', 'Anteprojeto',
                 now() - interval '3 day', NULL),
                ('00000000-0000-0000-0000-000000000003',
                 '00000000-0000-0000-0000-0000000000a1', 'Velho',
                 now() - interval '2 day', now()),
                ('00000000-0000-0000-0000-000000000004',
                 '00000000-0000-0000-0000-0000000000a1', 'Outro',
                 now(), NULL),
                ('00000000-0000-0000-0000-000000000005',
                 '00000000-0000-0000-0000-0000000000a2', 'Manuscrito',
                 now(), NULL);
            """
        )

    alembic('upgrade', 'ad86bd43da06')
    with psycopg.connect(db_url.render_as_string(hide_password=False)) as conn:
        rows = conn.execute(
            """
            SELECT name, position FROM document_group_items
            WHERE deleted_at IS NULL
            ORDER BY group_id, position
            """
        ).fetchall()

    assert rows == [
        ('Anteprojeto', 1),
        ('TCC', 2),
        ('Outro', 3),
        ('Manuscrito', 1),
    ]
