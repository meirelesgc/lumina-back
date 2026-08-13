import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document
from lumina.schemas.ai import Citation, AnswerWithCitations
from lumina.services.ai_service import resolve_citations, create_ai_response

def test_resolve_citations_valid():
    """Testa se as citations válidas são resolvidas corretamente e as inválidas descartadas"""
    chunks = [
        Document(page_content="Texto", metadata={"chunk_id": "chunk_1", "page": 1, "rects": [[10, 10, 20, 20]]}),
        Document(page_content="Fallback", metadata={"chunk_id": "chunk_txt", "page": 0, "rects": []})
    ]
    
    citations = [
        Citation(chunk_id="chunk_1", text_snippet="Texto"),
        Citation(chunk_id="chunk_txt", text_snippet="Fallback"),
        Citation(chunk_id="chunk_fantasma", text_snippet="Não existe")
    ]
    
    resolved = resolve_citations(citations, chunks)
    
    assert len(resolved) == 2
    assert resolved[0]["chunk_id"] == "chunk_1"
    assert resolved[0]["rects"] == [{"x1": 10, "y1": 10, "x2": 20, "y2": 20}]
    assert resolved[1]["chunk_id"] == "chunk_txt"
    assert resolved[1]["rects"] == []

@pytest.mark.asyncio
async def test_create_ai_response_structured():
    """Testa se o fluxo completo descarta alucinações de chunk e entrega o JSON"""
    # Mock vstore and its chunks
    mock_vstore = MagicMock()
    mock_chunk = Document(page_content="Fake Content", metadata={"chunk_id": "real_chunk", "page": 2, "rects": [[0,0,10,10]]})
    mock_vstore.asimilarity_search = AsyncMock(return_value=[mock_chunk])
    
    # Mock model to return structured output
    mock_model = MagicMock()
    mock_structured = MagicMock()
    
    # O LLM tenta citar um chunk real e um alucinado
    mock_structured.invoke.return_value = AnswerWithCitations(
        answer="Resposta do LLM",
        citations=[
            Citation(chunk_id="real_chunk", text_snippet="Content"),
            Citation(chunk_id="hallucinated", text_snippet="Fake")
        ]
    )
    mock_model.with_structured_output.return_value = mock_structured
    
    # Mock dependencies
    from lumina.models import DocumentRelease
    mock_session = AsyncMock()
    mock_release = MagicMock(spec=DocumentRelease)
    mock_release.file_path = "path/file.pdf"
    
    with pytest.MonkeyPatch.context() as m:
        # Pular as partes que envolvem BD
        m.setattr("lumina.services.release_service.get_releases_by_document", AsyncMock(return_value=[MagicMock(id=1)]))
        m.setattr("lumina.services.release_service.get_release_with_details", AsyncMock(return_value=mock_release))
        m.setattr("lumina.services.ai_service.get_document_auto_context", AsyncMock(return_value=[]))
        m.setattr("lumina.services.release_logic_service.get_expanded_chunks", AsyncMock(return_value=[mock_chunk]))
        
        response = await create_ai_response(
            session=mock_session,
            user_id="uuid",
            doc_id="uuid",
            data=MagicMock(content="Pergunta"),
            model=mock_model,
            vstore=mock_vstore,
            recent_messages=[]
        )
        
    assert response["answer"] == "Resposta do LLM"
    assert len(response["references"]) == 1
    assert response["references"][0]["chunk_id"] == "real_chunk"
    assert response["references"][0]["rects"][0]["x1"] == 0.0
