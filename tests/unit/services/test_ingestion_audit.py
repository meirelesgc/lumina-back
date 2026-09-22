# ruff: noqa: PLR2004, PLR0914
import json
from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest
from langchain_core.documents import Document

from lumina.core.settings import Settings
from lumina.services.ai.stages.audit import (
    export_ingestion_audit,
)
from lumina.services.ai.stages.chunking import (
    documents_to_markdown_preview,
)
from lumina.services.ai.stages.extraction import extract_pdf_chunks
from lumina.services.ai.stages.section_models import (
    Heading,
    Section,
    SectionRole,
)
from lumina.services.ai.stages.sections import tree_to_markdown


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / 'sample_doc.pdf'
    doc = pymupdf.open()
    page = doc.new_page(width=595.0, height=842.0)
    page.insert_text((50, 72), '1.0 DO OBJETO', fontsize=14)
    page.insert_text(
        (50, 100),
        'Contratacao de servicos de tecnologia da informacao.',
        fontsize=11,
    )
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_tree_to_markdown():
    sec = Section(
        heading=Heading(
            line_number=1,
            level=1,
            title='Objeto',
            raw='# Objeto',
            page=0,
        ),
        breadcrumb=['Edital', 'Objeto'],
        content='Texto descritivo do objeto.',
    )
    md = tree_to_markdown('test_doc.pdf', [sec])
    assert '# Árvore de Seções: test_doc.pdf' in md
    assert 'Edital > Objeto' in md
    assert 'H1' in md


def test_documents_to_markdown_preview():
    doc = Document(
        page_content='[Objeto] Conteudo do chunk.',
        metadata={
            'chunk_id': 'chunk_0_0',
            'section_path': 'Edital > Objeto',
            'page': 0,
            'section_level': 1,
        },
    )
    preview = documents_to_markdown_preview('test_doc.pdf', [doc])
    assert '# Chunks Gerados: test_doc.pdf' in preview
    assert '### Chunk 1 (Pág: 0 | Nível: H1)' in preview
    assert '[Objeto] Conteudo do chunk.' in preview


def test_export_ingestion_audit_creates_all_stages(
    sample_pdf: Path, tmp_path: Path
):
    audit_dir = tmp_path / 'audit'
    stem = sample_pdf.stem
    source_name = f'uploads/{sample_pdf.name}'

    full_markdown = (
        '# 1.0 DO OBJETO\n\n'
        'Contratacao de servicos de tecnologia da informacao.'
    )
    page_map = [
        {
            'page': 0,
            'start_line': 1,
            'end_line': 5,
            'char_count': len(full_markdown),
            'char_start': 0,
            'width': 595.0,
            'height': 842.0,
            'rotation': 0,
            'boxes': [
                {
                    'class': 'text',
                    'bbox': [50.0, 72.0, 500.0, 150.0],
                    'pos': [0, len(full_markdown)],
                }
            ],
        }
    ]
    sec = Section(
        heading=Heading(
            line_number=1,
            level=1,
            title='1.0 DO OBJETO',
            raw='# 1.0 DO OBJETO',
            page=0,
        ),
        breadcrumb=['1.0 DO OBJETO'],
        content='Contratacao de servicos de tecnologia da informacao.',
        role=SectionRole.METHODOLOGY,
        char_start=0,
        char_end=len(full_markdown),
        heading_char_start=0,
    )
    chunks = [
        Document(
            page_content='[1.0 DO OBJETO] Contratacao de servicos.',
            metadata={
                'chunk_id': 'chunk_0_0',
                'page': 0,
                'section_path': '1.0 DO OBJETO',
                'rects': [[50.0, 100.0, 350.0, 115.0]],
            },
        )
    ]

    export_ingestion_audit(
        full_path=str(sample_pdf),
        source_name=source_name,
        full_markdown=full_markdown,
        page_map=page_map,
        sections=[sec],
        chunks=chunks,
        audit_base_dir=audit_dir,
    )

    # 1. Raw markdown
    raw_md_file = audit_dir / '01_raw_markdown' / f'{stem}.md'
    raw_pages_file = audit_dir / '01_raw_markdown' / f'{stem}_pages.json'
    assert raw_md_file.exists()
    assert raw_pages_file.exists()
    assert full_markdown in raw_md_file.read_text(encoding='utf-8')

    # 2. Sections tree
    sec_json_file = audit_dir / '02_sections_tree' / f'{stem}_sections.json'
    sec_md_file = audit_dir / '02_sections_tree' / f'{stem}_sections.md'
    assert sec_json_file.exists()
    assert sec_md_file.exists()
    sec_data = json.loads(sec_json_file.read_text(encoding='utf-8'))
    assert sec_data['total_sections'] == 1
    assert sec_data['sections'][0]['title'] == '1.0 DO OBJETO'

    # 3. Chunks
    chunk_json_file = audit_dir / '03_chunks' / f'{stem}_chunks.json'
    chunk_md_file = audit_dir / '03_chunks' / f'{stem}_chunks.md'
    assert chunk_json_file.exists()
    assert chunk_md_file.exists()
    chunk_data = json.loads(chunk_json_file.read_text(encoding='utf-8'))
    assert chunk_data['total_chunks'] == 1

    # 4. Annotated PDF
    annotated_pdf = audit_dir / '04_annotated_pdfs' / f'{stem}_annotated.pdf'
    assert annotated_pdf.exists()
    with pymupdf.open(str(annotated_pdf)) as doc:
        assert len(doc) == 1
        page = doc[0]
        annots = list(page.annots())
        assert len(annots) >= 1
        assert annots[0].info.get('title') == 'chunk_0_0'


def test_extract_pdf_chunks_audit_flag_disabled(
    sample_pdf: Path, tmp_path: Path, monkeypatch
):
    audit_dir = tmp_path / 'audit_disabled'
    custom_settings = Settings(
        DEBUG_INGESTION_AUDIT=False,
        INGESTION_AUDIT_DIRECTORY=audit_dir,
    )
    monkeypatch.setattr(
        'lumina.services.ai.stages.extraction.SETTINGS', custom_settings
    )

    chunks, pages, null_b, ws = extract_pdf_chunks(
        str(sample_pdf), 'sample_doc.pdf'
    )
    assert len(chunks) >= 1
    assert pages == 1
    assert not audit_dir.exists()


def test_extract_pdf_chunks_audit_flag_enabled(
    sample_pdf: Path, tmp_path: Path, monkeypatch
):
    audit_dir = tmp_path / 'audit_enabled'
    custom_settings = Settings(
        DEBUG_INGESTION_AUDIT=True,
        INGESTION_AUDIT_DIRECTORY=audit_dir,
    )
    monkeypatch.setattr(
        'lumina.services.ai.stages.extraction.SETTINGS', custom_settings
    )
    monkeypatch.setattr(
        'lumina.services.ai.stages.audit.SETTINGS', custom_settings
    )

    chunks, pages, null_b, ws = extract_pdf_chunks(
        str(sample_pdf), 'sample_doc.pdf'
    )
    assert len(chunks) >= 1
    assert (audit_dir / '01_raw_markdown' / f'{sample_pdf.stem}.md').exists()
    assert (
        audit_dir / '04_annotated_pdfs' / f'{sample_pdf.stem}_annotated.pdf'
    ).exists()


def test_extract_pdf_chunks_audit_failure_is_resilient(
    sample_pdf: Path, tmp_path: Path, monkeypatch
):
    custom_settings = Settings(
        DEBUG_INGESTION_AUDIT=True,
        INGESTION_AUDIT_DIRECTORY=tmp_path / 'audit_fail',
    )
    monkeypatch.setattr(
        'lumina.services.ai.stages.extraction.SETTINGS', custom_settings
    )

    with patch(
        'lumina.services.ai.stages.extraction.export_ingestion_audit',
        side_effect=RuntimeError('Disk write error'),
    ):
        chunks, pages, null_b, ws = extract_pdf_chunks(
            str(sample_pdf), 'sample_doc.pdf'
        )
        assert len(chunks) >= 1
