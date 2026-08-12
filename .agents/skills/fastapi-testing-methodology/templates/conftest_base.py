"""
Template de Configuração Global de Testes (conftest_base.py)

Demonstra a otimização de banco de dados rodando DDL apenas uma vez
e controlando o isolamento via transações/savepoints.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from lumina.models import table_registry
from lumina.core.settings import Settings

@pytest.fixture(scope="session")
def engine():
    _engine = create_async_engine(Settings().DATABASE_URL)
    yield _engine

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database(engine):
    """
    Cria as tabelas APENAS UMA VEZ no início de toda a sessão de testes.
    """
    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.drop_all)

@pytest_asyncio.fixture
async def session(engine):
    """
    Inicia a sessão, mas faz ROLLBACK ao final de cada teste.
    Isto evita I/O pesado de Drop/Create tables a cada caso.
    """
    connection = await engine.connect()
    transaction = await connection.begin()
    
    # Usa um savepoint para nested transactions (útil caso a aplicação dê seus próprios commits)
    nested = await connection.begin_nested()
    
    session = AsyncSession(bind=connection, expire_on_commit=False)
    
    # Hook para reiniciar o savepoint caso o service faça commit
    @pytest.hookimpl
    async def restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = await connection.begin_nested()
            
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
