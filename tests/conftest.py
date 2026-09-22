import contextlib
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import factory
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from lumina.app import app
from lumina.core.database import get_session
from lumina.core.llm import set_fast_model_override
from lumina.core.security import get_password_hash
from lumina.models import User, table_registry
from lumina.schemas.branch import (
    BranchSectionRequirement,
    SectionRequirementScope,
)

pytest_plugins = ['tests.ai.fixtures.ai_fixtures']


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


@pytest.fixture(autouse=True)
def mock_fast_model_for_tests(request):
    """Garante que nenhum teste rotineiro chame APIs reais de LLM."""
    if not request.config.getoption('--run-ai'):
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=BranchSectionRequirement(
                scope=SectionRequirementScope.UNKNOWN,
                expected_section=None,
                reasoning='Mock padrão para testes.',
            )
        )
        mock_llm.with_structured_output.return_value = mock_structured
        set_fast_model_override(mock_llm)
        yield mock_llm
        set_fast_model_override(None)
    else:
        yield None


def _build_null_session() -> MagicMock:
    """Sessão fake sem efeitos colaterais, para tarefas em background."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = []
    session.scalars = AsyncMock(return_value=scalars_result)
    session.execute = AsyncMock(return_value=MagicMock())
    return session


@contextlib.asynccontextmanager
async def _null_async_session():
    yield _build_null_session()


@pytest.fixture(autouse=True)
def isolate_background_task_db_writes(monkeypatch):
    """
    Impede que tarefas em background disparadas por create_branch/
    update_branch (análise de seção, geração de expansões de consulta)
    gravem no banco real configurado em DATABASE_URL quando disparadas
    fora de uma sessão de teste controlada — via `asyncio.create_task`
    ou o `BackgroundTasks` real do FastAPI/TestClient. Mesmo espírito de
    `mock_fast_model_for_tests`: nenhum teste rotineiro deve ter efeitos
    colaterais em serviços externos (aqui, o Postgres configurado no
    ambiente local/`.env`, e não o container efêmero de testes).
    """
    monkeypatch.setattr(
        'lumina.services.ai.branch_analyzer.async_session',
        _null_async_session,
    )
    monkeypatch.setattr(
        'lumina.services.ai.query_expansion_service.async_session',
        _null_async_session,
    )


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
    with PostgresContainer('postgres:16', driver='psycopg') as postgres:
        _engine = create_async_engine(postgres.get_connection_url())
        yield _engine


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
