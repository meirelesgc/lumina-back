import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document

from lumina.services.release_logic_service import get_expanded_chunks, _fetch_chunks_by_indices, apply_tree


@pytest.mark.asyncio
async def test_get_expanded_chunks_empty():
    mock_vstore = MagicMock()
    result = await get_expanded_chunks(mock_vstore, [])
    assert result == []


@pytest.mark.asyncio
async def test_get_expanded_chunks_missing_metadata():
    mock_vstore = MagicMock()
    chunk_no_meta = Document(page_content="Sem metadata", metadata={})
    result = await get_expanded_chunks(mock_vstore, [chunk_no_meta])
    assert result == []


@pytest.mark.asyncio
async def test_get_expanded_chunks_with_direct_sql():
    # Simula PGVector com _make_async_session e EmbeddingStore
    mock_vstore = MagicMock()
    mock_session = AsyncMock()
    
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_session
    mock_ctx.__aexit__.return_value = None
    mock_vstore._make_async_session.return_value = mock_ctx
    
    mock_collection = MagicMock()
    mock_collection.uuid = "mock-uuid"
    mock_vstore.aget_collection = AsyncMock(return_value=mock_collection)
    
    from langchain_postgres.vectorstores import _get_embedding_collection_store
    EmbeddingStore, _ = _get_embedding_collection_store(None)
    mock_vstore.EmbeddingStore = EmbeddingStore
    
    record1 = MagicMock(id=1, document="Texto chunk 0", cmetadata={"source": "doc1", "chunk_index": 0})
    record2 = MagicMock(id=2, document="Texto chunk 1", cmetadata={"source": "doc1", "chunk_index": 1})
    record3 = MagicMock(id=3, document="Texto chunk 2", cmetadata={"source": "doc1", "chunk_index": 2})
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [record1, record2, record3]
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    original = [
        Document(page_content="Texto chunk 1", metadata={"source": "doc1", "chunk_index": 1})
    ]
    
    expanded = await get_expanded_chunks(mock_vstore, original)
    
    assert len(expanded) == 3
    assert [c.metadata["chunk_index"] for c in expanded] == [0, 1, 2]
    assert not mock_vstore.asimilarity_search.called


@pytest.mark.asyncio
async def test_get_expanded_chunks_fallback():
    # Quando não há _make_async_session, usa o fallback asimilarity_search
    mock_vstore = MagicMock(spec=["asimilarity_search"])
    fallback_doc = Document(page_content="Fallback text", metadata={"source": "doc1", "chunk_index": 0})
    mock_vstore.asimilarity_search = AsyncMock(return_value=[fallback_doc])
    
    original = [
        Document(page_content="Texto chunk 0", metadata={"source": "doc1", "chunk_index": 0})
    ]
    
    expanded = await get_expanded_chunks(mock_vstore, original)
    assert len(expanded) == 1
    assert mock_vstore.asimilarity_search.called


@pytest.mark.asyncio
async def test_apply_tree_resolves_citations_into_references():
    mock_chain = MagicMock()
    mock_chain.abatch = AsyncMock(return_value=[
        {
            "feedback": "O resumo possui boa redação.",
            "fulfilled": True,
            "score": 9,
            "citations": [
                {"chunk_id": "chunk_0_1", "text_snippet": "Texto do resumo"},
                {"chunk_id": "chunk_fantasma", "text_snippet": "Inexistente"}
            ]
        }
    ])
    
    mock_chunk = Document(
        page_content="Texto do resumo",
        metadata={"chunk_id": "chunk_0_1", "page": 0, "rects": [[10.0, 20.0, 100.0, 40.0]]}
    )
    
    eval_args = [
        {
            "id": "mock-branch-id",
            "document": "[FONTE] chunk_id: chunk_0_1\nTexto do resumo",
            "source": "Fonte 1",
            "requirement": "Redação: concisa",
            "expected_session": "Resumo",
            "query": "Analise o item",
            "_sessions": [mock_chunk]
        }
    ]
    
    result = await apply_tree(mock_chain, eval_args)
    
    assert len(result) == 1
    item = result[0]
    assert item["score"] == 9
    assert item["fulfilled"] is True
    assert "references" in item
    assert len(item["references"]) == 1
    assert item["references"][0]["chunk_id"] == "chunk_0_1"
    assert item["references"][0]["page"] == 0
    assert item["references"][0]["rects"] == [{"x1": 10.0, "y1": 20.0, "x2": 100.0, "y2": 40.0}]

