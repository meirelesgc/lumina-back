"""
O anotador copia trechos de um leitor de PDF ou digita à mão, e o PDF usa a
tipografia do editor. A comparação com os gabaritos ignora essa diferença
(OpenSpec: retrieval-annotated-baseline).
"""

from tests.fixtures.answer_keys import normalize


def test_aspas_retas_e_curvas_sao_iguais():
    assert normalize('AND (microgrids OR "Smart grids")') == normalize(
        'AND (microgrids OR “Smart grids”)'
    )


def test_hifen_e_travessoes_sao_iguais():
    assert normalize('two main approaches predominated-artificial') == (
        normalize('two main approaches predominated—artificial')
    )
    assert normalize('[47,53,56-58]') == normalize('[47,53,56–58]')
