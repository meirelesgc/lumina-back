# ruff: noqa: PLR2004
from lumina.services.ai.stages.sentences import (
    mark_sentences,
    remap_sentences,
    split_sentences,
)


def texts(text: str) -> list[str]:
    return [text[start:end] for start, end in split_sentences(text)]


def test_divide_o_texto_em_frases_na_ordem_de_leitura():
    text = (
        'A revisão incluiu estudos publicados entre 2010 e 2020. '
        'Os autores buscaram em quatro bases de dados diferentes. '
        'A seleção ficou a cargo de dois revisores independentes.'
    )

    assert texts(text) == [
        'A revisão incluiu estudos publicados entre 2010 e 2020.',
        'Os autores buscaram em quatro bases de dados diferentes.',
        'A seleção ficou a cargo de dois revisores independentes.',
    ]


def test_abreviacao_nao_encerra_frase():
    text = (
        'Segundo Silva et al. A incidência caiu no período estudado. '
        'O Art. 5 da norma exige relatório anual dos resultados obtidos.'
    )

    assert texts(text) == [
        'Segundo Silva et al. A incidência caiu no período estudado.',
        'O Art. 5 da norma exige relatório anual dos resultados obtidos.',
    ]


def test_inicial_de_nome_nao_encerra_frase():
    text = 'O estudo de J. Silva mostrou queda relevante na incidência anual.'

    assert texts(text) == [text]


def test_linha_em_branco_e_item_de_lista_encerram_frase():
    text = (
        'Primeiro parágrafo sem ponto final no texto extraído\n\n'
        'Segundo parágrafo também sem ponto final no texto\n'
        '- item de lista com tamanho suficiente para ficar só'
    )

    assert texts(text) == [
        'Primeiro parágrafo sem ponto final no texto extraído',
        'Segundo parágrafo também sem ponto final no texto',
        '- item de lista com tamanho suficiente para ficar só',
    ]


def test_fragmento_curto_pertence_a_frase_seguinte():
    text = (
        '| Curto |\n'
        '| Linha de tabela com conteúdo suficiente para valer sozinha |'
    )

    assert texts(text) == [text]


def test_fragmento_final_fica_na_ultima_frase():
    text = (
        'Uma frase com tamanho suficiente para valer sozinha no texto.\n\nFim'
    )

    assert texts(text) == [text]


def test_texto_curto_vira_uma_frase():
    assert texts('Curto.') == ['Curto.']


def test_texto_sem_conteudo_nao_gera_frase():
    assert split_sentences('  \n ') == []


def test_marca_as_frases_e_mantem_o_prefixo():
    content = '[Método] Primeira frase. Segunda frase.'
    sentences = [
        {'n': 1, 'start': 9, 'end': 24, 'rects': []},
        {'n': 2, 'start': 25, 'end': 39, 'rects': []},
    ]

    assert mark_sentences(content, sentences) == (
        '[Método] [s1] Primeira frase. [s2] Segunda frase.'
    )


def test_chunk_sem_frases_fica_sem_marcadores():
    assert mark_sentences('[Método] Texto.', None) == '[Método] Texto.'
    assert mark_sentences('[Método] Texto.', []) == '[Método] Texto.'


def test_remapeia_as_frases_depois_de_um_marcador():
    sentences = [
        {'n': 1, 'start': 0, 'end': 20, 'rects': []},
        {'n': 2, 'start': 21, 'end': 33, 'rects': []},
    ]
    # 'Maria Silva' (0 a 11) virou '<PERSON_0>' (0 a 10)
    after = '<PERSON_0> assinou. Depois saiu.'

    remapped = remap_sentences(sentences, [(0, 11, 0, 10)])

    assert after[remapped[0]['start'] : remapped[0]['end']] == (
        '<PERSON_0> assinou.'
    )
    assert after[remapped[1]['start'] : remapped[1]['end']] == 'Depois saiu.'


def test_entidade_na_fronteira_fica_inteira_na_primeira_frase():
    sentences = [
        {'n': 1, 'start': 0, 'end': 13, 'rects': []},
        {'n': 2, 'start': 13, 'end': 30, 'rects': []},
    ]
    # A entidade de 10 a 16 atravessa a fronteira e vira um marcador de 10 a 20
    remapped = remap_sentences(sentences, [(10, 16, 10, 20)])

    assert remapped[0]['end'] == 20
    assert remapped[1]['start'] == 20
    assert remapped[1]['end'] == 34


def test_frase_engolida_por_entidade_sai_e_a_numeracao_continua():
    sentences = [
        {'n': 1, 'start': 0, 'end': 5, 'rects': []},
        {'n': 2, 'start': 6, 'end': 10, 'rects': []},
        {'n': 3, 'start': 11, 'end': 20, 'rects': []},
    ]

    remapped = remap_sentences(sentences, [(3, 10, 3, 8)])

    assert [s['n'] for s in remapped] == [1, 2]
    assert remapped[1]['start'] == 9
