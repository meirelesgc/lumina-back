from contextlib import contextmanager
from datetime import datetime

pytest_plugins = ['tests.ai.fixtures.ai_fixtures']

import factory
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from lumina.app import app
from lumina.core.database import get_session
from lumina.core.security import get_password_hash
from lumina.core.settings import Settings
from lumina.models import User, table_registry


def pytest_addoption(parser):
    parser.addoption(
        '--run-ai',
        action='store_true',
        default=False,
        help='Executa testes de IA que consomem tokens e chamam LLMs.',
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--run-ai'):
        skip_ai = pytest.mark.skip(
            reason=(
                'Testes de IA desativados por padrão para economizar tokens. '
                'Use --run-ai ou task test-ai para executar.'
            )
        )
        for item in items:
            if item.get_closest_marker('ai') is not None:
                item.add_marker(skip_ai)


@pytest.fixture
def client(session):
    def get_session_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_session] = get_session_override
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope='session')
def engine():
    # Caso do windows + Docker no CI
    import sys  # noqa: PLC0415

    if sys.platform == 'win32':
        yield create_async_engine(Settings().DATABASE_URL)

    else:
        try:
            with PostgresContainer('postgres:16', driver='psycopg') as postgres:
                _engine = create_async_engine(postgres.get_connection_url())
                yield _engine
        except Exception:
            yield create_async_engine(Settings().DATABASE_URL)


@pytest_asyncio.fixture(scope='session', loop_scope='session', autouse=True)
async def setup_database(engine):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(table_registry.metadata.create_all)
        yield
        async with engine.begin() as conn:
            await conn.run_sync(table_registry.metadata.drop_all)
    except Exception:
        yield


@pytest_asyncio.fixture
async def session(engine):
    connection = await engine.connect()
    transaction = await connection.begin()

    session = AsyncSession(
        bind=connection,
        join_transaction_mode='create_savepoint',
        expire_on_commit=False,
    )

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@contextmanager
def _mock_db_time(*, model, time=datetime(2024, 1, 1)):
    def fake_time_handler(mapper, connection, target):
        if hasattr(target, 'created_at'):
            target.created_at = time
        if hasattr(target, 'updated_at'):
            target.updated_at = time

    event.listen(model, 'before_insert', fake_time_handler)

    yield time

    event.remove(model, 'before_insert', fake_time_handler)


@pytest.fixture
def mock_db_time():
    return _mock_db_time


@pytest_asyncio.fixture
async def user(session):
    password = 'testtest'
    user = UserFactory(password=get_password_hash(password))

    session.add(user)
    await session.commit()
    await session.refresh(user)

    user.clean_password = password

    return user


@pytest_asyncio.fixture
async def other_user(session):
    password = 'testtest'
    user = UserFactory(password=get_password_hash(password))

    session.add(user)
    await session.commit()
    await session.refresh(user)

    user.clean_password = password

    return user


@pytest.fixture
def token(client, user):
    response = client.post(
        '/auth/token',
        data={'username': user.email, 'password': user.clean_password},
    )
    return response.json()['access_token']


class UserFactory(factory.Factory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'test{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@test.com')
    password = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    phone_number = factory.Sequence(lambda n: f'550199999{n:04d}')
