# ruff: noqa: PLR2004
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import fitz
import pytest
from langchain_core.documents import Document

from lumina.services.ai.pipeline import run_document_ingestion
from lumina.services.ai.stages.sections import (
    assign_sections_to_chunks,
    assign_sections_with_telemetry,
    detect_sections_with_model,
    normalize_with_mapping,
)

EXPECTED_CHUNK_COUNT = 2
EXPECTED_STUB_STR_LEN = 5


def test_assign_sections_to_chunks_stubs():
    """
    Testa compatibilidade da funcao assign_sections_to_chunks.
    """
    chunks = [
        Document(
            page_content='Texto 1',
            metadata={'page': 0, 'section_title': 'Secao A'},
        ),
        Document(
            page_content='Texto 2',
            metadata={'page': 1, 'section_title': 'Secao B'},
        ),
    ]

    docs, meta = assign_sections_to_chunks(chunks)

    assert len(docs) == EXPECTED_CHUNK_COUNT
    assert docs[0].metadata['section_title'] == 'Secao A'
    assert docs[0].page_content.startswith('SECTION: Secao A\n\n')
    assert docs[1].metadata['section_title'] == 'Secao B'
    assert docs[1].page_content.startswith('SECTION: Secao B\n\n')


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
    Testa se os wrappers assincronos com telemetria executam sem erros.
    """
    chunks = [
        Document(
            page_content='PDF Chunk',
            metadata={'section_title': 'Introdução', 'section_role': 'intro'},
        )
    ]
    res_pdf = await assign_sections_with_telemetry(chunks, run_id=uuid4())
    assert res_pdf[0].metadata['section_title'] == 'Introdução'


@pytest.mark.asyncio
async def test_pipeline_ingestion_pdf_with_sections(tmp_path):
    """
    Valida a ingestão completa de PDF no novo pipeline verificando a
    identificação de seções reais, corte e enriquecimento de coordenadas.
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 50), '# 1.0. DO OBJETO\n\nAquisição de computadores.'
    )
    pdf_path = tmp_path / 'test_sections_ingestion.pdf'
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
    assert first_doc.metadata['section_title'] == '1.0. DO OBJETO'
    assert first_doc.metadata['page'] == 0
    assert first_doc.metadata['chunk_id'] == 'chunk_0_0'
    assert 'rects' in first_doc.metadata
    assert len(first_doc.metadata['rects']) > 0
    assert first_doc.page_content.startswith('[1.0. DO OBJETO]')


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
