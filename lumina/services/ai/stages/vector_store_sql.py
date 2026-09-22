from typing import List

import sqlalchemy as sa
from langchain_core.documents import Document
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

COLLECTION_NAME = 'langchain'

_embedding = sa.table(
    'langchain_pg_embedding',
    sa.column('document'),
    sa.column('cmetadata', JSONB),
    sa.column('collection_id'),
)
_collection = sa.table(
    'langchain_pg_collection',
    sa.column('uuid'),
    sa.column('name'),
)


def _base_join():
    return _embedding.join(
        _collection, _embedding.c.collection_id == _collection.c.uuid
    )


def _rows_to_documents(rows) -> List[Document]:
    return [
        Document(page_content=row.document or '', metadata=row.cmetadata or {})
        for row in rows
    ]


async def fetch_chunk_siblings(
    session: AsyncSession, source: str, section_index: int, page: int
) -> List[Document]:
    """
    Retorna todos os chunks normais (exclui resumos de seção) de uma
    mesma seção/página, ordenados por `chunk_index_in_section`, para
    expansão de vizinhos e merge de janelas (Fase 3). Reaproveita a
    mesma sessão de banco do chamador (mesmo padrão dos repositórios).
    """
    stmt = (
        select(_embedding.c.document, _embedding.c.cmetadata)
        .select_from(_base_join())
        .where(
            _collection.c.name == COLLECTION_NAME,
            _embedding.c.cmetadata['source'].astext == source,
            _embedding.c.cmetadata['section_index'].astext
            == str(section_index),
            _embedding.c.cmetadata['page'].astext == str(page),
            _embedding.c.cmetadata['record_type'].astext.is_(None),
        )
        .order_by(
            sa.cast(
                _embedding.c.cmetadata['chunk_index_in_section'].astext,
                sa.Integer,
            )
        )
    )
    result = await session.execute(stmt)
    return _rows_to_documents(result.all())


async def lexical_search(
    session: AsyncSession, query: str, source: str, k: int
) -> List[Document]:
    """
    Busca léxica (full-text search) sobre os chunks normais de um
    documento, para fusão híbrida dense + léxica via RRF (Fase 4).
    Reaproveita a mesma sessão de banco do chamador.
    """
    if not query or not query.strip():
        return []

    tsquery = func.plainto_tsquery('portuguese', query)
    tsvector = func.to_tsvector('portuguese', _embedding.c.document)
    rank = func.ts_rank(tsvector, tsquery).label('rank')

    stmt = (
        select(_embedding.c.document, _embedding.c.cmetadata, rank)
        .select_from(_base_join())
        .where(
            _collection.c.name == COLLECTION_NAME,
            _embedding.c.cmetadata['source'].astext == source,
            _embedding.c.cmetadata['record_type'].astext.is_(None),
            tsvector.op('@@')(tsquery),
        )
        .order_by(rank.desc())
        .limit(k)
    )
    result = await session.execute(stmt)
    return _rows_to_documents(result.all())
