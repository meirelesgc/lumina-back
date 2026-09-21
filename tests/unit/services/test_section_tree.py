# ruff: noqa: PLR2004
from lumina.services.ai.stages.sections import (
    build_section_tree,
    flatten_sections,
    parse_headings_from_markdown,
    tree_to_dict,
)


def test_parse_headings_and_page_map():
    md = """# Titulo 1
Texto da pagina 0

## Subtitulo 1.1
Mais texto

# Titulo 2
Texto final
"""
    page_map = [
        {'page': 0, 'start_line': 1, 'end_line': 4},
        {'page': 1, 'start_line': 5, 'end_line': 8},
    ]

    headings = parse_headings_from_markdown(md, page_map)
    assert len(headings) == 3
    assert headings[0].title == 'Titulo 1'
    assert headings[0].page == 0
    assert headings[1].title == 'Subtitulo 1.1'
    assert headings[1].page == 0
    assert headings[2].title == 'Titulo 2'
    assert headings[2].page == 1


def test_build_section_tree_hierarchy_and_breadcrumbs():
    md = """# 1. Introdução
Texto introdutório.

## 1.1 Contexto
Detalhes contextuais.

### 1.1.1 Detalhes
Mais detalhes.

# 2. Conclusão
Encerramento.
"""
    headings = parse_headings_from_markdown(md)
    tree = build_section_tree(headings, md)

    assert len(tree) == 2
    assert tree[0].title == '1. Introdução'
    assert len(tree[0].children) == 1
    assert tree[0].children[0].title == '1.1 Contexto'
    assert tree[0].children[0].breadcrumb == ['1. Introdução', '1.1 Contexto']

    sub_child = tree[0].children[0].children[0]
    assert sub_child.title == '1.1.1 Detalhes'
    assert sub_child.breadcrumb == [
        '1. Introdução',
        '1.1 Contexto',
        '1.1.1 Detalhes',
    ]

    assert tree[1].title == '2. Conclusão'
    assert len(tree[1].children) == 0


def test_build_section_tree_char_offsets_integrity():
    md = (
        '# Capitulo 1\n\n'
        'Conteudo do capitulo 1.\n\n'
        '# Capitulo 2\n\n'
        'Conteudo do capitulo 2.'
    )
    headings = parse_headings_from_markdown(md)
    tree = build_section_tree(headings, md)

    sec1 = tree[0]
    sec2 = tree[1]

    assert sec1.content == 'Conteudo do capitulo 1.'
    assert md[sec1.char_start : sec1.char_end] == sec1.content

    assert sec2.content == 'Conteudo do capitulo 2.'
    assert md[sec2.char_start : sec2.char_end] == sec2.content


def test_flatten_sections_and_tree_to_dict():
    md = """# Sec 1
Texto 1

## Sec 1.1
Texto 1.1

# Sec 2
Texto 2
"""
    headings = parse_headings_from_markdown(md)
    tree = build_section_tree(headings, md)
    flat = flatten_sections(tree)

    assert len(flat) == 3
    assert [s.title for s in flat] == ['Sec 1', 'Sec 1.1', 'Sec 2']

    d = tree_to_dict(tree)
    assert len(d) == 2
    assert d[0]['title'] == 'Sec 1'
    assert len(d[0]['children']) == 1
    assert d[0]['children'][0]['title'] == 'Sec 1.1'
