from io import BytesIO

import pymupdf
import pytest
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Table,
)

from lumina.utils.markdown_reportlab import (
    markdown_styles,
    markdown_to_flowables,
)


@pytest.fixture
def styles():
    return markdown_styles()


def render_text(flowables):
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build(flowables)
    with pymupdf.open(stream=buffer.getvalue(), filetype='pdf') as pdf:
        return ''.join(page.get_text() for page in pdf)


def paragraphs(flowables):
    return [f for f in flowables if isinstance(f, Paragraph)]


def test_titulos_usam_estilos_de_cabecalho(styles):
    flowables = markdown_to_flowables(
        '# Síntese\n## Achados\n### Detalhe\n#### Mais fundo', styles
    )

    names = [p.style.name for p in paragraphs(flowables)]
    texts = [p.text for p in paragraphs(flowables)]
    assert names == ['MdHeading1', 'MdHeading2', 'MdHeading3', 'MdHeading3']
    assert texts == ['Síntese', 'Achados', 'Detalhe', 'Mais fundo']


def test_lista_com_marcadores_vira_itens_com_bullet(styles):
    flowables = markdown_to_flowables(
        '- primeiro\n* segundo\n+ terceiro', styles
    )

    items = paragraphs(flowables)
    assert [p.text for p in items] == ['primeiro', 'segundo', 'terceiro']
    assert all(p.style.name == 'MdBullet' for p in items)
    assert all(p.bulletText == '•' for p in items)


def test_lista_numerada_preserva_numeracao(styles):
    flowables = markdown_to_flowables('1. um\n2) dois\n10. dez', styles)

    items = paragraphs(flowables)
    assert [p.bulletText for p in items] == ['1.', '2.', '10.']
    assert [p.text for p in items] == ['um', 'dois', 'dez']


def test_lista_aninhada_aumenta_recuo(styles):
    flowables = markdown_to_flowables('- pai\n  - filho', styles)

    pai, filho = paragraphs(flowables)
    assert filho.style.leftIndent > pai.style.leftIndent


def test_negrito_e_italico_viram_tags_do_reportlab(styles):
    (paragraph,) = markdown_to_flowables(
        'O edital **cumpre** o item *parcialmente* e __exige__ _ajuste_.',
        styles,
    )

    assert paragraph.text == (
        'O edital <b>cumpre</b> o item <i>parcialmente</i> '
        'e <b>exige</b> <i>ajuste</i>.'
    )


def test_codigo_em_linha_usa_fonte_monoespacada(styles):
    (paragraph,) = markdown_to_flowables('Campo `valor_total`.', styles)

    assert paragraph.text == 'Campo <font face="Courier">valor_total</font>.'


def test_tabela_gfm_vira_table_com_cabecalho_e_linhas(styles):
    text = (
        '| Critério | Nota |\n'
        '| :--- | ---: |\n'
        '| Prazo | **8** |\n'
        '| Custo | 5 |'
    )

    (table,) = markdown_to_flowables(text, styles)

    assert isinstance(table, Table)
    cells = [[cell.text for cell in row] for row in table._cellvalues]
    assert cells == [
        ['Critério', 'Nota'],
        ['Prazo', '<b>8</b>'],
        ['Custo', '5'],
    ]
    assert table._cellvalues[0][0].style.name == 'MdTableHeader'


def test_tabela_com_linhas_irregulares_completa_colunas(styles):
    text = '| A | B | C |\n|---|---|---|\n| 1 |\n| 1 | 2 | 3 | 4 |'

    (table,) = markdown_to_flowables(text, styles)

    assert [len(row) for row in table._cellvalues] == [3, 3, 3]


def test_bloco_de_codigo_preserva_conteudo_literal(styles):
    text = '```python\nif a < b and c:\n    **x**\n```'

    (code,) = markdown_to_flowables(text, styles)

    assert isinstance(code, Preformatted)
    assert '**x**' in render_text([code])


def test_texto_puro_preserva_quebras_de_linha(styles):
    text = 'Primeira linha\nSegunda linha\n\nNovo parágrafo'

    first, second = markdown_to_flowables(text, styles)

    assert first.text == 'Primeira linha<br/>Segunda linha'
    assert second.text == 'Novo parágrafo'
    assert first.style.name == 'MdBody'


def test_texto_vazio_nao_gera_flowables(styles):
    assert markdown_to_flowables('', styles) == []
    assert markdown_to_flowables(None, styles) == []
    assert markdown_to_flowables('  \n\n ', styles) == []


def test_caracteres_xml_sao_escapados(styles):
    (paragraph,) = markdown_to_flowables(
        'Valor < 10 & prazo > 5 <script>alert(1)</script> <b>x</b>', styles
    )

    assert paragraph.text == (
        'Valor &lt; 10 &amp; prazo &gt; 5 '
        '&lt;script&gt;alert(1)&lt;/script&gt; &lt;b&gt;x&lt;/b&gt;'
    )


def test_pdf_com_caracteres_especiais_compila_e_mostra_texto(styles):
    text = (
        '## Riscos & prazos\n'
        '- custo < 10% do total\n'
        '| Item | Limite |\n|---|---|\n| A&B | <5 |\n\n'
        'Entidade já escapada: &amp; e tag solta <br>'
    )

    rendered = render_text(markdown_to_flowables(text, styles))

    assert 'Riscos & prazos' in rendered
    assert 'custo < 10% do total' in rendered
    assert 'A&B' in rendered
    assert '<5' in rendered
    assert '&amp; e tag solta <br>' in rendered


def test_pdf_nao_exibe_marcadores_crus(styles):
    text = (
        '# Síntese\n\n'
        'O documento **atende** a *maioria* dos critérios.\n\n'
        '- item um\n1. item dois\n\n'
        '| Col | Val |\n|---|---|\n| a | b |'
    )

    rendered = render_text(markdown_to_flowables(text, styles))

    for marker in ('**', '# ', '- item', '|', '---'):
        assert marker not in rendered
    assert 'atende' in rendered
    assert 'item dois' in rendered
