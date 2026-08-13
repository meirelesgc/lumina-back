import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.documents import Document
from lumina.services.vector_service import process_file
import fitz

@pytest.mark.asyncio
async def test_process_file_pdf_metadata(tmp_path):
    """
    Testa se o processamento de PDF utiliza o CoordinateChunker e anexa
    corretamente as variáveis `chunk_id`, `page` e `rects`.
    """
    # Cria um PDF falso para teste
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Texto de teste para validar o CoordinateChunker.")
    pdf_path = tmp_path / "test_doc.pdf"
    doc.save(str(pdf_path))
    doc.close()

    mock_vstore = MagicMock()
    mock_vstore.aadd_documents = AsyncMock()
    mock_model = MagicMock()
    
    # Moca a chamada ao LLM de seções
    with patch('lumina.services.vector_service._get_sections_with_model', return_value=[]):
        await process_file(str(pdf_path), mock_vstore, mock_model)

    assert mock_vstore.aadd_documents.called
    documents = mock_vstore.aadd_documents.call_args[0][0]
    
    assert len(documents) > 0
    first_doc = documents[0]
    
    # Validações do contrato
    assert "chunk_id" in first_doc.metadata
    assert first_doc.metadata["chunk_id"].startswith("chunk_")
    assert "page" in first_doc.metadata
    assert first_doc.metadata["page"] == 0
    assert "rects" in first_doc.metadata
    assert isinstance(first_doc.metadata["rects"], list)
    assert len(first_doc.metadata["rects"]) > 0  # Achou a linha inserida

@pytest.mark.asyncio
async def test_process_file_txt_metadata_fallback(tmp_path):
    """
    Testa se o fallback para arquivos não-PDF funciona, garantindo que
    `rects` desce como lista vazia.
    """
    txt_path = tmp_path / "test_doc.txt"
    txt_path.write_text("Texto simples sem coordenadas.", encoding="utf-8")
    
    mock_vstore = MagicMock()
    mock_vstore.aadd_documents = AsyncMock()
    mock_model = MagicMock()
    
    with patch('lumina.services.vector_service._get_sections_with_model', return_value=[]):
        await process_file(str(txt_path), mock_vstore, mock_model)

    assert mock_vstore.aadd_documents.called
    documents = mock_vstore.aadd_documents.call_args[0][0]
    
    assert len(documents) > 0
    first_doc = documents[0]
    
    # Validações do contrato fallback
    assert "chunk_id" in first_doc.metadata
    assert "page" in first_doc.metadata
    assert "rects" in first_doc.metadata
    assert first_doc.metadata["rects"] == []  # Exatamente o fallback exigido
