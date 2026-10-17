"""
O seletor de seções escolhe o contexto de cada critério pelo sumário do
documento. O sumário sai dos chunks da ingestão: uma linha por seção, na
ordem de leitura, com id, páginas, tamanho e o começo do texto
(OpenSpec: outline-section-selection).
"""

from langchain_core.documents import Document

from lumina.services.ai.stages.outline import (
    PREVIEW_CHARS,
    build_outline,
    outline_markdown,
)

INTRO = '1. Introdução'
METHODS = '2. Metodologia'
CRITERIA = '2.1 Critérios de elegibilidade'


def chunk(index: int, path: str, page: int, text: str, order: int = 0):
    title = path.rsplit(' > ', maxsplit=1)[-1]
    return Document(
        page_content=f'[{title}] {text}',
        metadata={
            'section_index': index,
            'section_title': title,
            'section_path': path,
            'page': page,
            'chunk_index_in_section': order,
            'chunk_id': f'chunk_{page}_{index}{order}',
        },
    )


def sample_chunks() -> list[Document]:
    return [
        chunk(2, f'{METHODS} > {CRITERIA}', 3, 'Foram incluídos artigos.'),
        chunk(0, INTRO, 0, 'A dengue é um problema de saúde.'),
        chunk(1, METHODS, 1, 'A revisão seguiu o PRISMA.', order=0),
        chunk(1, METHODS, 2, 'As bases foram Scopus e WoS.', order=1),
    ]


def test_secoes_seguem_a_ordem_de_leitura_com_ids_estaveis():
    outline = build_outline(sample_chunks())

    assert [s.id for s in outline] == ['s01', 's02', 's03']
    assert [s.title for s in outline] == [INTRO, METHODS, CRITERIA]


def test_secao_junta_os_chunks_e_as_paginas():
    methods = build_outline(sample_chunks())[1]

    assert (methods.first_page, methods.last_page) == (2, 3)
    assert [c.metadata['chunk_index_in_section'] for c in methods.chunks] == [
        0,
        1,
    ]
    assert methods.text == (
        'A revisão seguiu o PRISMA.\nAs bases foram Scopus e WoS.'
    )
    assert methods.tokens == len(methods.text) // 4


def test_previa_e_o_comeco_do_texto_sem_o_prefixo_de_titulo():
    long_text = 'palavra ' * 100
    section = build_outline([chunk(0, INTRO, 0, long_text)])[0]

    assert not section.preview.startswith('[')
    assert len(section.preview) <= PREVIEW_CHARS
    assert long_text.startswith(section.preview)


def test_markdown_indenta_pelo_caminho_de_titulos():
    lines = outline_markdown(build_outline(sample_chunks())).splitlines()

    assert lines[0] == f'- [s01] {INTRO} · p1 · ~8 tokens'
    assert lines[1] == '  "A dengue é um problema de saúde."'
    assert lines[2].startswith(f'- [s02] {METHODS} · p2–p3 · ~')
    assert lines[4].startswith(f'  - [s03] {CRITERIA} · p4 · ~')
    assert lines[5] == '    "Foram incluídos artigos."'
