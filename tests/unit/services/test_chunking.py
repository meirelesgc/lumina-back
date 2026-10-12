# ruff: noqa: PLR2004
from langchain_core.documents import Document

from lumina.services.ai.stages import chunking
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


def _section(md, title, level, body, breadcrumb):
    line_number = md[: md.index(f'# {title}')].count('\n') + 1
    return Section(
        heading=Heading(
            line_number=line_number,
            level=level,
            title=title,
            raw=f'# {title}',
            page=0,
        ),
        breadcrumb=breadcrumb,
        content=body,
        char_start=md.index(body),
        char_end=md.index(body) + len(body),
    )


def test_create_chunks_from_sections_includes_subsections():
    md = (
        '# 2. Desenvolvimento\n\n'
        'Visao geral.\n\n'
        '# 2.1 Vetor\n\n'
        'O mosquito transmite.\n\n'
        '# 2.2 Diagnostico\n\n'
        'Exame clinico.'
    )
    page_map = [{'page': 0, 'char_start': 0, 'char_count': len(md)}]
    parent = _section(
        md, '2. Desenvolvimento', 1, 'Visao geral.', ['2. Desenvolvimento']
    )
    parent.children = [
        _section(
            md,
            '2.1 Vetor',
            2,
            'O mosquito transmite.',
            ['2. Desenvolvimento', '2.1 Vetor'],
        ),
        _section(
            md,
            '2.2 Diagnostico',
            2,
            'Exame clinico.',
            ['2. Desenvolvimento', '2.2 Diagnostico'],
        ),
    ]

    docs = create_chunks_from_sections([parent], page_map, md, 'doc.pdf')

    assert [d.page_content for d in docs] == [
        '[2. Desenvolvimento] Visao geral.',
        '[2.1 Vetor] O mosquito transmite.',
        '[2.2 Diagnostico] Exame clinico.',
    ]
    assert docs[2].metadata['section_title'] == '2.2 Diagnostico'
    assert docs[2].metadata['section_path'] == (
        '2. Desenvolvimento > 2.2 Diagnostico'
    )
    assert [d.metadata['section_index'] for d in docs] == [0, 1, 2]


def test_clean_whitespace():
    docs = [
        Document(page_content='Texto 1\n\n\n\n\nTexto 2'),
    ]
    cleaned = clean_whitespace(docs)
    assert cleaned[0].page_content == 'Texto 1\n\nTexto 2'


def _single_section_chunks_args():
    md = '# Objeto\n\nAquisicao de computadores.'
    page_map = [{'page': 0, 'char_start': 0, 'char_count': len(md)}]
    sec = Section(
        heading=Heading(
            line_number=1, level=1, title='Objeto', raw='# Objeto', page=0
        ),
        breadcrumb=['Objeto'],
        content='Aquisicao de computadores.',
        char_start=md.index('Aquisicao'),
        char_end=md.index('Aquisicao') + len('Aquisicao de computadores.'),
    )
    return [sec], page_map, md


def test_chunk_context_not_called_when_flag_disabled(mocker):
    mock_generate = mocker.patch.object(
        chunking, 'generate_chunk_context', return_value='contexto extra'
    )
    mocker.patch.object(
        chunking.SETTINGS, 'CONTEXTUAL_CHUNK_ENRICHMENT_ENABLED', False
    )

    sections, page_map, md = _single_section_chunks_args()
    docs = create_chunks_from_sections(sections, page_map, md, 'doc.pdf')

    mock_generate.assert_not_called()
    assert 'chunk_context' not in docs[0].metadata


def test_chunk_context_called_when_flag_enabled(mocker):
    mock_generate = mocker.patch.object(
        chunking, 'generate_chunk_context', return_value='contexto extra'
    )
    mocker.patch.object(
        chunking.SETTINGS, 'CONTEXTUAL_CHUNK_ENRICHMENT_ENABLED', True
    )

    sections, page_map, md = _single_section_chunks_args()
    docs = create_chunks_from_sections(sections, page_map, md, 'doc.pdf')

    mock_generate.assert_called()
    assert docs[0].metadata['chunk_context'] == 'contexto extra'
