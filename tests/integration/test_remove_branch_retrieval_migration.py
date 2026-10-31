import os
import subprocess

import psycopg
from psycopg.types.json import Jsonb

BEFORE = '0adaecd70bea'
TYPIFICATION = '00000000-0000-0000-0000-0000000000a1'
TAXONOMY = '00000000-0000-0000-0000-0000000000b1'
BRANCH = '00000000-0000-0000-0000-0000000000c1'
EXPANSION = '00000000-0000-0000-0000-0000000000d1'
COLLECTION = '00000000-0000-0000-0000-0000000000e1'


def table_exists(conn, name: str) -> bool:
    found = conn.execute('SELECT to_regclass(%s)', (name,)).fetchone()[0]
    return found is not None


def column_exists(conn, table: str, column: str) -> bool:
    return (
        conn.execute(
            'SELECT 1 FROM information_schema.columns'
            ' WHERE table_name = %s AND column_name = %s',
            (table, column),
        ).fetchone()
        is not None
    )


def migrated_database(engine, name: str):
    """Cria uma base vazia e devolve o DSN e o executor do Alembic."""
    url = engine.url.set(drivername='postgresql')
    admin_dsn = url.render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS {name}')
        conn.execute(f'CREATE DATABASE {name}')

    db_url = url.set(database=name)
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

    return db_url.render_as_string(hide_password=False), alembic


def seed_expansion(conn):
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
        INSERT INTO branch_query_expansions
            (id, branch_id, expansion_text, expansion_type, generation_model,
             generation_version, is_active)
        VALUES (%s, %s, 'bases consultadas', 'paraphrase', 'llm', 1, true)
        """,
        (EXPANSION, BRANCH),
    )


def seed_vector_store(conn):
    """Recria só as colunas que a migração toca nas tabelas do PGVector."""
    conn.execute('CREATE TABLE langchain_pg_collection (uuid uuid, name text)')
    conn.execute(
        'CREATE TABLE langchain_pg_embedding'
        ' (id text, collection_id uuid, document text, cmetadata jsonb)'
    )
    conn.execute(
        "INSERT INTO langchain_pg_collection VALUES (%s, 'langchain')",
        (COLLECTION,),
    )
    for doc_id, metadata in (
        ('chunk', {'source': 'a.pdf'}),
        ('resumo', {'source': 'a.pdf', 'record_type': 'section_summary'}),
    ):
        conn.execute(
            'INSERT INTO langchain_pg_embedding VALUES (%s, %s, %s, %s)',
            (doc_id, COLLECTION, doc_id, Jsonb(metadata)),
        )


def test_migracao_apaga_expansoes_e_resumos_e_preserva_chunks(engine):
    """Roda as migrações de verdade numa base separada do container de teste.

    A suíte cria as tabelas com `create_all`, e as tabelas do PGVector só
    existem depois do primeiro uso, então só uma base migrada pelo Alembic
    mostra o efeito sobre os dados (OpenSpec: remover-recuperacao-por-ramo).
    """
    dsn, alembic = migrated_database(engine, 'remove_retrieval_check')

    alembic('upgrade', BEFORE)
    with psycopg.connect(dsn) as conn:
        seed_expansion(conn)
        seed_vector_store(conn)

    alembic('upgrade', 'head')
    with psycopg.connect(dsn) as conn:
        assert not table_exists(conn, 'branch_query_expansions')
        assert not column_exists(
            conn, 'applied_branches', 'expansion_generation_version'
        )
        assert conn.execute(
            'SELECT id FROM langchain_pg_embedding'
        ).fetchall() == [('chunk',)]

    alembic('downgrade', BEFORE)
    with psycopg.connect(dsn) as conn:
        assert conn.execute(
            'SELECT count(*) FROM branch_query_expansions'
        ).fetchone() == (0,)
        assert column_exists(
            conn, 'applied_branches', 'expansion_generation_version'
        )


def test_migracao_roda_em_base_sem_tabelas_do_pgvector(engine):
    dsn, alembic = migrated_database(engine, 'remove_retrieval_empty')

    alembic('upgrade', 'head')

    with psycopg.connect(dsn) as conn:
        assert not table_exists(conn, 'branch_query_expansions')
        assert not table_exists(conn, 'langchain_pg_embedding')
