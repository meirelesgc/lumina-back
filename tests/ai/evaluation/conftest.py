import pytest_asyncio

from tests.ai.evaluation.support import build_vectorstore, ingest_answer_keys


@pytest_asyncio.fixture(scope='session', loop_scope='session')
async def indexed_vectorstore(engine):
    """
    Base vetorial com todos os PDFs anotados, ingerida uma vez por sessão.
    A busca léxica lê a coleção `langchain` direto
    pelo SQL, então os testes compartilham a mesma coleção.
    """
    vstore = build_vectorstore(engine)
    await ingest_answer_keys(vstore)
    yield vstore
    await vstore.adelete_collection()
