"""
Jornada: o analista envia uma revisão sistemática para avaliação e espera
que o parecer de cada critério se apoie também nos trechos que repetem as
palavras do critério, e não só nos trechos que a busca vetorial acha
parecidos (OpenSpec: lexical-search-any-term, issue #16).

A busca léxica não usa o vetor, então os chunks entram com embeddings
falsos. Os PDFs anotados passam pela ingestão de produção.
"""

from pathlib import Path

import pytest
import pytest_asyncio
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_postgres import PGVector

from lumina.services.ai.pipeline import run_document_ingestion
from lumina.services.ai.stages.retrieval import branch_lexical_search
from lumina.services.ai.stages.sections import SECTION_SUMMARY_RECORD_TYPE
from lumina.services.ai.stages.vector_store_sql import lexical_search
from tests.ai.evaluation.support import document_filter
from tests.fixtures.answer_keys import (
    RETRIEVAL_KEYS,
    doc_id,
    expected_branches,
    pdf_for,
)

pytestmark = pytest.mark.asyncio(loop_scope='session')

# Documento em inglês: a busca léxica em português não o encontra (#38).
ENGLISH_KEYS = {'systematic_review/smart_tech_microgrids.retrieval.yaml'}
PORTUGUESE_KEYS = [k for k in RETRIEVAL_KEYS if doc_id(k) not in ENGLISH_KEYS]

ISSUE_BRANCH = (
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
    Coleção `langchain` com os PDFs anotados em português e uma revisão
    escrita à mão. A busca léxica lê a coleção direto pelo SQL.
    """
    store = PGVector(
        embeddings=DeterministicFakeEmbedding(size=16),
        connection=engine,
        use_jsonb=True,
        async_mode=True,
    )
    for key in PORTUGUESE_KEYS:
        await run_document_ingestion(pdf_for(key), store, model=None)
    await store.aadd_documents([
        chunk(JUSTIFICATION, REVIEW_SOURCE),
        chunk('A busca foi feita nas bases MEDLINE e Embase.', REVIEW_SOURCE),
        chunk(
            'Os critérios de elegibilidade incluíram estudos observacionais.',
            REVIEW_SOURCE,
        ),
        chunk(
            'Resumo da seção: justificativa da revisão sistemática.',
            REVIEW_SOURCE,
            record_type=SECTION_SUMMARY_RECORD_TYPE,
        ),
        chunk(
            'A justificativa da revisão sistemática aparece no manuscrito.',
            OTHER_SOURCE,
        ),
    ])
    yield store
    await store.adelete_collection()


async def test_ramo_de_varias_palavras_recebe_o_trecho_da_justificativa(
    session, vstore
):
    # Nenhum chunk contém todas as palavras do ramo.
    docs = await lexical_search(session, ISSUE_BRANCH, REVIEW_SOURCE, k=5)

    assert docs
    assert docs[0].page_content == JUSTIFICATION


@pytest.mark.parametrize('retrieval_key', PORTUGUESE_KEYS, ids=doc_id)
async def test_ramos_com_evidencia_recebem_chunks_do_documento(
    session, vstore, retrieval_key: Path
):
    source = document_filter(retrieval_key)['source']
    empty = []
    for _, branch in expected_branches(retrieval_key):
        if not branch['evidence']:
            continue
        title = branch['title'].strip()
        query = f'{title}: {branch["description"].strip()}'
        docs = await branch_lexical_search(session, title, query, source, k=5)
        if not docs:
            empty.append(branch['id'])
        assert all(d.metadata['source'] == source for d in docs)

    assert not empty, f'{doc_id(retrieval_key)}: ramos sem chunk: {empty}'


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


async def test_busca_ignora_outro_documento_e_resumos_de_secao(
    session, vstore
):
    docs = await lexical_search(session, ISSUE_BRANCH, REVIEW_SOURCE, k=10)

    assert all(d.metadata['source'] == REVIEW_SOURCE for d in docs)
    assert all('record_type' not in d.metadata for d in docs)


@pytest.mark.parametrize(
    'query',
    [
        'Justificativa & revisão | sistemática',
        '!justificativa (revisão) "sistemática": dengue',
    ],
)
async def test_simbolos_do_ramo_viram_texto(session, vstore, query):
    docs = await lexical_search(session, query, REVIEW_SOURCE, k=5)

    assert docs[0].page_content == JUSTIFICATION


@pytest.mark.parametrize('query', ['', '   ', 'de a o para com'])
async def test_ramo_sem_termo_pesquisavel_devolve_lista_vazia(
    session, vstore, query
):
    assert await lexical_search(session, query, REVIEW_SOURCE, k=5) == []
