# ruff: noqa: PLR2004
from langchain_core.documents import Document

from lumina.services.ai.stages.chunking import (
    clean_whitespace,
    create_chunks_from_sections,
    create_default_text_splitter,
    slice_section_by_pages,
)
from lumina.services.ai.stages.section_models import Heading, Section


def test_slice_section_by_pages_strictly_monopage():
    # Markdown com 100 caracteres distribuídos em 2 páginas
    md = 'A' * 50 + 'B' * 50
    page_map = [
        {'page': 0, 'char_start': 0, 'char_count': 50},
        {'page': 1, 'char_start': 50, 'char_count': 50},
    ]
    # Seção que cruza a fronteira das duas páginas (de 20 a 80)
    sec = Section(
        heading=Heading(
            line_number=1, level=1, title='Sec', raw='# Sec', page=0
        ),
        char_start=20,
        char_end=80,
    )

    slices = slice_section_by_pages(sec, page_map, md)

    assert len(slices) == 2
    assert slices[0]['page'] == 0
    assert slices[0]['text'] == 'A' * 30
    assert slices[0]['char_start'] == 20
    assert slices[0]['char_end'] == 50

    assert slices[1]['page'] == 1
    assert slices[1]['text'] == 'B' * 30
    assert slices[1]['char_start'] == 50
    assert slices[1]['char_end'] == 80


def test_create_chunks_from_sections_metadata_and_chunk_ids():
    md = (
        '# Objeto\n\n'
        'Aquisicao de computadores.\n\n'
        '# Habilitacao\n\n'
        'Certidao regular.'
    )
    page_map = [
        {'page': 0, 'char_start': 0, 'char_count': len(md)},
    ]
    sec1 = Section(
        heading=Heading(
            line_number=1, level=1, title='Objeto', raw='# Objeto', page=0
        ),
        breadcrumb=['Objeto'],
        content='Aquisicao de computadores.',
        char_start=md.index('Aquisicao'),
        char_end=md.index('Aquisicao') + len('Aquisicao de computadores.'),
    )
    sec2 = Section(
        heading=Heading(
            line_number=5,
            level=1,
            title='Habilitacao',
            raw='# Habilitacao',
            page=0,
        ),
        breadcrumb=['Habilitacao'],
        content='Certidao regular.',
        char_start=md.index('Certidao'),
        char_end=md.index('Certidao') + len('Certidao regular.'),
    )

    docs = create_chunks_from_sections(
        [sec1, sec2],
        page_map,
        md,
        'doc.pdf',
        create_default_text_splitter(100, 20),
    )

    assert len(docs) == 2
    assert docs[0].page_content == '[Objeto] Aquisicao de computadores.'
    assert docs[0].metadata['chunk_id'] == 'chunk_0_0'
    assert docs[0].metadata['page'] == 0
    assert docs[0].metadata['section_title'] == 'Objeto'
    assert docs[0].metadata['chunk_index'] == 0

    assert docs[1].page_content == '[Habilitacao] Certidao regular.'
    assert docs[1].metadata['chunk_id'] == 'chunk_0_1'
    assert docs[1].metadata['page'] == 0
    assert docs[1].metadata['section_title'] == 'Habilitacao'
    assert docs[1].metadata['chunk_index'] == 1


def test_clean_whitespace():
    docs = [
        Document(page_content='Texto 1\n\n\n\n\nTexto 2'),
    ]
    cleaned = clean_whitespace(docs)
    assert cleaned[0].page_content == 'Texto 1\n\nTexto 2'
