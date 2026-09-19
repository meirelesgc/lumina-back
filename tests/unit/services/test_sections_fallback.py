from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import fitz
import pytest
from langchain_core.documents import Document

from lumina.services.ai.pipeline import run_document_ingestion
from lumina.services.ai.stages.sections import (
    DEFAULT_SECTION_TITLE,
    assign_sections_to_chunks,
    assign_sections_with_telemetry,
    detect_sections_with_model,
    normalize_with_mapping,
)

EXPECTED_CHUNK_COUNT = 2
EXPECTED_STUB_STR_LEN = 5


def test_assign_sections_to_chunks_default():
    """
    Testa se assign_sections_to_chunks atribui 'NÃO ENCONTRADA' e o prefixo
    SECTION em todos os chunks de entrada.
    """
    chunks = [
        Document(page_content='Texto 1', metadata={'page': 0}),
        Document(page_content='Texto 2', metadata={'page': 1}),
    ]

    docs, meta = assign_sections_to_chunks(chunks)

    assert len(docs) == EXPECTED_CHUNK_COUNT
    for doc in docs:
        assert doc.metadata['section_title'] == DEFAULT_SECTION_TITLE
        assert doc.page_content.startswith(
            f'SECTION: {DEFAULT_SECTION_TITLE}\n\n'
        )

    assert meta['default_assigned'] == DEFAULT_SECTION_TITLE
    assert meta['sections_detected'] == []
    assert meta['mapping_success_rate'] == 1.0


def test_stubs_compatibility():
    """
    Testa compatibilidade dos stubs detect_sections_with_model
    e normalize_with_mapping.
    """
    docs = [Document(page_content='Teste')]
    sections, window = detect_sections_with_model(docs)
    assert sections == []
    assert not window

    norm, mapping = normalize_with_mapping('Texto')
    assert norm == 'texto'
    assert len(mapping) == EXPECTED_STUB_STR_LEN


@pytest.mark.asyncio
async def test_sections_telemetry_wrappers():
    """
    Testa se os wrappers assíncronos com telemetria executam sem erros.
    """
    chunks = [Document(page_content='PDF Chunk', metadata={})]
    res_pdf = await assign_sections_with_telemetry(chunks, run_id=uuid4())
    assert res_pdf[0].metadata['section_title'] == DEFAULT_SECTION_TITLE


@pytest.mark.asyncio
async def test_pipeline_ingestion_pdf_with_default_sections(tmp_path):
    """
    Valida a ingestão completa de PDF garantindo que os chunks recebam
    a seção padrão 'NÃO ENCONTRADA'.
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), 'Texto de teste do PDF para ingestão.')
    pdf_path = tmp_path / 'test_default_sections.pdf'
    doc.save(str(pdf_path))
    doc.close()

    mock_vstore = MagicMock()
    mock_vstore.aadd_documents = AsyncMock()
    mock_model = MagicMock()

    await run_document_ingestion(str(pdf_path), mock_vstore, mock_model)

    assert mock_vstore.aadd_documents.called
    ingested_docs = mock_vstore.aadd_documents.call_args[0][0]
    assert len(ingested_docs) > 0
    first_doc = ingested_docs[0]
    assert first_doc.metadata['section_title'] == DEFAULT_SECTION_TITLE
    assert first_doc.page_content.startswith(
        f'SECTION: {DEFAULT_SECTION_TITLE}\n\n'
    )


@pytest.mark.asyncio
async def test_pipeline_ingestion_unsupported_format_raises_error(tmp_path):
    """
    Valida que a tentativa de ingestão de formatos não suportados (ex: .txt)
    levanta ValueError informando a extensão inválida.
    """
    txt_path = tmp_path / 'test_unsupported.txt'
    txt_path.write_text('Texto de arquivo TXT simples.', encoding='utf-8')

    mock_vstore = MagicMock()
    mock_model = MagicMock()

    with pytest.raises(
        ValueError, match='Tipo de arquivo não suportado: .txt'
    ):
        await run_document_ingestion(str(txt_path), mock_vstore, mock_model)
