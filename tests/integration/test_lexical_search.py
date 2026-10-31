"""
Jornada: o analista pergunta ao chat sobre uma revisão sistemática e espera
que a resposta se apoie também nos trechos que repetem as palavras da
pergunta, e não só nos trechos que a busca vetorial acha parecidos
(OpenSpec: lexical-search-any-term, issue #16).

A busca léxica não usa o vetor, então os chunks entram com embeddings falsos.
"""

import pytest
import pytest_asyncio
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_postgres import PGVector

from lumina.services.ai.stages.vector_store_sql import lexical_search

pytestmark = pytest.mark.asyncio(loop_scope='session')

LONG_QUESTION = (
    'Existência de justificativa da revisão: O manuscrito apresenta uma '
    'justificativa clara para a realização da Revisão Sistemática?'
)
REVIEW_SOURCE = 'lumina/storage/uploads/revisao.pdf'
OTHER_SOURCE = 'lumina/storage/uploads/outra_revisao.pdf'
LONG_SOURCE = 'lumina/storage/uploads/revisao_longa.pdf'
JUSTIFICATION = (
    'A justificativa desta revisão sistemática é a ausência de sínteses '
    'recentes sobre o controle da dengue no Brasil.'
)


def chunk(text: str, source: str, **metadata) -> Document:
    return Document(page_content=text, metadata={'source': source, **metadata})


@pytest_asyncio.fixture(scope='module', loop_scope='session')
async def vstore(engine):
    """
    Coleção `langchain` com uma revisão escrita à mão. A busca léxica lê a
    coleção direto pelo SQL.
    """
    store = PGVector(
        embeddings=DeterministicFakeEmbedding(size=16),
        connection=engine,
        use_jsonb=True,
        async_mode=True,
    )
    await store.aadd_documents([
        chunk(JUSTIFICATION, REVIEW_SOURCE),
        chunk('A busca foi feita nas bases MEDLINE e Embase.', REVIEW_SOURCE),
        chunk(
            'Os critérios de elegibilidade incluíram estudos observacionais.',
            REVIEW_SOURCE,
        ),
        chunk(
            'A justificativa da revisão sistemática aparece no manuscrito.',
            OTHER_SOURCE,
        ),
    ])
    yield store
    await store.adelete_collection()


async def test_pergunta_de_varias_palavras_recebe_o_trecho_da_justificativa(
    session, vstore
):
    # Nenhum chunk contém todas as palavras da pergunta.
    docs = await lexical_search(session, LONG_QUESTION, REVIEW_SOURCE, k=5)

    assert docs
    assert docs[0].page_content == JUSTIFICATION


async def test_chunk_curto_vem_antes_do_longo_que_repete_os_termos(
    session, vstore
):
    short = 'Justificativa da revisão: faltam sínteses recentes.'
    long = 'Justificativa e revisão do orçamento. ' * 3 + (
        'O texto administrativo segue sem relação com o critério. ' * 30
    )
    await vstore.aadd_documents([
        chunk(long, LONG_SOURCE),
        chunk(short, LONG_SOURCE),
    ])

    docs = await lexical_search(
        session, 'Existência de justificativa da revisão', LONG_SOURCE, k=5
    )

    assert [d.page_content for d in docs] == [short, long]


async def test_busca_ignora_outro_documento(session, vstore):
    docs = await lexical_search(session, LONG_QUESTION, REVIEW_SOURCE, k=10)

    assert all(d.metadata['source'] == REVIEW_SOURCE for d in docs)


@pytest.mark.parametrize(
    'query',
    [
        'Justificativa & revisão | sistemática',
        '!justificativa (revisão) "sistemática": dengue',
    ],
)
async def test_simbolos_da_pergunta_viram_texto(session, vstore, query):
    docs = await lexical_search(session, query, REVIEW_SOURCE, k=5)

    assert docs[0].page_content == JUSTIFICATION


@pytest.mark.parametrize('query', ['', '   ', 'de a o para com'])
async def test_pergunta_sem_termo_pesquisavel_devolve_lista_vazia(
    session, vstore, query
):
    assert await lexical_search(session, query, REVIEW_SOURCE, k=5) == []
