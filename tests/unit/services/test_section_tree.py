# ruff: noqa: PLR2004
from lumina.services.ai.stages.sections import (
    build_section_tree,
    build_sections_tree_from_markdown,
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


def test_inline_label_becomes_section_with_its_line_text():
    md = (
        '# 5. Conclusions\n\n'
        'Texto da conclusao com mais de vinte caracteres.\n\n'
        '**Funding:** This research was supported by CNPq.\n\n'
        '**Conflicts of Interest:** The authors declare no conflicts.\n'
    )
    flat = flatten_sections(build_sections_tree_from_markdown(md))

    assert [s.title for s in flat] == [
        '5. Conclusions',
        'Funding',
        'Conflicts of Interest',
    ]
    assert 'This research was supported by CNPq.' in flat[1].content
    assert 'This research' not in flat[0].content


def test_structured_abstract_labels_stay_inside_abstract():
    md = (
        '# RESUMO\n\n'
        '**Objetivo** : Este artigo propoe uma solucao de busca.\n\n'
        '**Metodologia** : A pesquisa segue uma abordagem experimental.\n\n'
        '# 1 INTRODUÇÃO\n\n'
        'Texto da introducao com mais de vinte caracteres.\n'
    )
    flat = flatten_sections(build_sections_tree_from_markdown(md))

    assert [s.title for s in flat] == ['RESUMO', '1 INTRODUÇÃO']
    assert 'abordagem experimental' in flat[0].content


def test_inline_label_char_range_starts_at_its_own_line():
    md = (
        '# Conclusions\n\n'
        'Texto da conclusao.\n\n'
        '**Funding:** This research was supported by CNPq.'
    )
    tree = build_section_tree(parse_headings_from_markdown(md), md)
    funding = tree[1]

    assert funding.char_start == md.index('**Funding:**')
    assert md[funding.char_start : funding.char_end] == funding.content
    assert funding.content.startswith('**Funding:** This research')
