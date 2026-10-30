"""
Cleaner de cabeçalhos e rodapés corridos da extração (OpenSpec:
strip-running-headers-footers). Páginas sintéticas no formato do
pymupdf4llm: texto bruto da página e caixas com `class`, `bbox` e `pos`.
"""

from lumina.services.ai.stages.extraction import (
    find_running_boxes,
    mask_ranges,
)

HEIGHT = 800.0
TOP = [50, 20, 550, 40]
MIDDLE = [50, 380, 550, 420]
BOTTOM = [50, 760, 550, 780]


def make_page(*boxes):
    """Monta uma página a partir de pares (classe, bbox, texto)."""
    text = ''
    page_boxes = []
    for cls, bbox, box_text in boxes:
        start = len(text)
        text += f'{box_text}\n\n'
        page_boxes.append({
            'class': cls,
            'bbox': bbox,
            'pos': [start, len(text)],
        })
    return {'text': text, 'boxes': page_boxes, 'height': HEIGHT}


def body(n):
    return ('text', MIDDLE, f'Parágrafo do corpo da página {n}.')


def test_cabecalho_do_layout_repetido_sai_de_todas_as_paginas():
    pages = [
        make_page(('page-header', TOP, '**DENGUE NO BRASIL**'), body(n))
        for n in range(2)
    ]

    assert find_running_boxes(pages) == {(0, 0), (1, 0)}


def test_rodape_do_layout_em_uma_pagina_so_fica():
    pages = [
        make_page(
            body(0), ('page-footer', BOTTOM, 'Figura 2 – Busca do SIMCC')
        ),
        make_page(body(1)),
    ]

    assert find_running_boxes(pages) == set()


def test_numero_de_pagina_que_muda_conta_como_a_mesma_linha():
    pages = [
        make_page(
            body(n),
            ('page-footer', BOTTOM, f'Revista Foco | p.01-24 | {n + 1}'),
        )
        for n in range(2)
    ]

    assert find_running_boxes(pages) == {(0, 1), (1, 1)}


def test_linha_de_texto_corrida_na_faixa_sai_menos_a_primeira():
    authors = ('text', TOP, 'Robson Lopes Cardoso, Níbia Sales Damasceno')
    pages = [make_page(authors, body(n)) for n in range(4)]

    assert find_running_boxes(pages) == {(1, 0), (2, 0), (3, 0)}


def test_linha_de_texto_na_faixa_abaixo_do_limite_fica():
    authors = ('text', TOP, 'Robson Lopes Cardoso, Níbia Sales Damasceno')
    # 3 de 11 páginas: abaixo de 30%.
    pages = [make_page(authors, body(n)) for n in range(3)]
    pages += [make_page(body(n)) for n in range(3, 11)]

    assert find_running_boxes(pages) == set()


def test_linha_de_texto_em_duas_paginas_fica():
    authors = ('text', TOP, 'Robson Lopes Cardoso, Níbia Sales Damasceno')
    pages = [make_page(authors, body(n)) for n in range(2)]

    assert find_running_boxes(pages) == set()


def test_linha_repetida_no_meio_da_pagina_fica():
    source = ('text', MIDDLE, '**Fonte:** Criada pelos autores (2023)')
    pages = [make_page(body(n), source) for n in range(4)]

    assert find_running_boxes(pages) == set()


def test_imagem_repetida_na_faixa_fica():
    logo = ('picture', TOP, '![](logo.png)')
    pages = [make_page(logo, body(n)) for n in range(4)]

    assert find_running_boxes(pages) == set()


def test_paginas_sem_repeticao_nao_tem_caixa_corrida():
    pages = [
        make_page(('page-footer', BOTTOM, '2026'), body(0)),
        make_page(('page-footer', BOTTOM, 'SALVADOR 2026'), body(1)),
    ]

    assert find_running_boxes(pages) == set()


def test_mascara_troca_o_intervalo_por_quebras_e_mantem_o_tamanho():
    text = 'CABEÇALHO\n\nCorpo da página.'

    masked = mask_ranges(text, [(0, 11)])

    assert masked == '\n' * 11 + 'Corpo da página.'
    assert len(masked) == len(text)


def test_mascara_sem_intervalos_devolve_o_mesmo_texto():
    text = 'Corpo da página.'

    assert mask_ranges(text, []) == text
