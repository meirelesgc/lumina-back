import os
import subprocess

import psycopg

BEFORE = '0adaecd70bea'
DOCUMENT = '00000000-0000-0000-0000-0000000000a1'
PROJECT = '00000000-0000-0000-0000-0000000000a2'
PROJECT_DOCUMENT = '00000000-0000-0000-0000-0000000000a3'
HISTORY_A = '00000000-0000-0000-0000-0000000000b1'
HISTORY_B = '00000000-0000-0000-0000-0000000000b2'
RELEASE_A = '00000000-0000-0000-0000-0000000000c1'
RELEASE_B = '00000000-0000-0000-0000-0000000000c2'


def table_exists(conn, name: str) -> bool:
    found = conn.execute('SELECT to_regclass(%s)', (name,)).fetchone()[0]
    return found is not None


def columns(conn, table: str) -> set[str]:
    rows = conn.execute(
        'SELECT column_name FROM information_schema.columns'
        ' WHERE table_name = %s',
        (table,),
    ).fetchall()
    return {row[0] for row in rows}


def seed(conn):
    for level in ('AUDITOR', 'ANALYST', 'ADMIN', 'DEFAULT'):
        conn.execute(
            'INSERT INTO users'
            ' (id, username, phone_number, email, password, access_level)'
            ' VALUES (gen_random_uuid(), %s, %s, %s, %s, %s)',
            (level, level, f'{level}@lumina.test', 'hash', level),
        )
    conn.execute(
        'INSERT INTO documents'
        ' (id, name, identifier, description, processing_status,'
        ' is_archived)'
        " VALUES (%s, 'Edital', 'ED-1', '', 'IDLE', false)",
        (DOCUMENT,),
    )
    conn.execute(
        "INSERT INTO projects (id, name, status) VALUES (%s, 'TCC', 'INICIADO')",
        (PROJECT,),
    )
    conn.execute(
        'INSERT INTO project_documents'
        ' (id, project_id, name, status, sent_to_kanban)'
        " VALUES (%s, %s, 'Artigo', 'COMPLETED', true)",
        (PROJECT_DOCUMENT, PROJECT),
    )
    for history, release, status in (
        (HISTORY_A, RELEASE_A, 'PENDING'),
        (HISTORY_B, RELEASE_B, 'COMPLETED'),
    ):
        conn.execute(
            'INSERT INTO document_histories (id, document_id, status)'
            ' VALUES (%s, %s, %s)',
            (history, DOCUMENT, status),
        )
        conn.execute(
            'INSERT INTO document_releases (id, history_id, file_path)'
            " VALUES (%s, %s, 'artigo.pdf')",
            (release, history),
        )


def test_migracao_preserva_releases_e_converte_niveis(engine):
    """Roda as migrações de verdade numa base separada do container de teste.

    A suíte cria as tabelas com `create_all`, então só uma base migrada pelo
    Alembic mostra o efeito sobre dados existentes (OpenSpec: remove-kanban).
    """
    url = engine.url.set(drivername='postgresql')
    admin_dsn = url.render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute('DROP DATABASE IF EXISTS remove_kanban_check')
        conn.execute('CREATE DATABASE remove_kanban_check')

    db_url = url.set(database='remove_kanban_check')
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
        seed(conn)

    alembic('upgrade', 'head')
    with psycopg.connect(dsn) as conn:
        releases = conn.execute(
            'SELECT document_id::text FROM document_releases'
        ).fetchall()
        assert releases == [(DOCUMENT,), (DOCUMENT,)]
        assert 'history_id' not in columns(conn, 'document_releases')
        assert not table_exists(conn, 'document_histories')
        assert not {'status', 'sent_to_kanban'} & columns(
            conn, 'project_documents'
        )
        levels = dict(
            conn.execute('SELECT username, access_level FROM users').fetchall()
        )
        assert levels == {
            'AUDITOR': 'DEFAULT',
            'ANALYST': 'DEFAULT',
            'ADMIN': 'ADMIN',
            'DEFAULT': 'DEFAULT',
        }

    alembic('downgrade', BEFORE)
    with psycopg.connect(dsn) as conn:
        assert conn.execute(
            'SELECT count(*), max(status) FROM document_histories'
        ).fetchone() == (1, 'PENDING')
        linked = conn.execute(
            'SELECT count(*) FROM document_releases r'
            ' JOIN document_histories h ON h.id = r.history_id'
            ' WHERE h.document_id = %s',
            (DOCUMENT,),
        ).fetchone()
        assert linked == (2,)
        assert {'status', 'sent_to_kanban'} <= columns(
            conn, 'project_documents'
        )
