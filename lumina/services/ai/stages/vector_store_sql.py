from typing import List

import sqlalchemy as sa
from langchain_core.documents import Document
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import JSONB, TSQUERY
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


async def lexical_search(
    session: AsyncSession, query: str, source: str, k: int
) -> List[Document]:
    """
    Busca léxica (full-text search) sobre os chunks de um documento,
    para fusão híbrida dense + léxica via RRF.
    Aceita chunks com qualquer termo da consulta: o `plainto_tsquery`
    normaliza o texto e liga os termos com `&`, que vira `|`. O
    `ts_rank` divide a pontuação pelo tamanho do chunk (normalização 2),
    para um chunk longo não subir só por repetir os termos.
    Reaproveita a mesma sessão de banco do chamador.
    """
    if not query or not query.strip():
        return []

    tsquery = sa.cast(
        func.replace(
            sa.cast(func.plainto_tsquery('portuguese', query), sa.Text),
            '&',
            '|',
        ),
        TSQUERY,
    )
    tsvector = func.to_tsvector('portuguese', _embedding.c.document)
    rank = func.ts_rank(tsvector, tsquery, 2).label('rank')

    stmt = (
        select(_embedding.c.document, _embedding.c.cmetadata, rank)
        .select_from(_base_join())
        .where(
            _collection.c.name == COLLECTION_NAME,
            _embedding.c.cmetadata['source'].astext == source,
            tsvector.op('@@')(tsquery),
        )
        .order_by(rank.desc())
        .limit(k)
    )
    result = await session.execute(stmt)
    return _rows_to_documents(result.all())
