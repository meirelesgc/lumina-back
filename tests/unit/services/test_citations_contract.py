# ruff: noqa: PLR2004
from unittest.mock import patch

from langchain_core.documents import Document

from lumina.schemas.ai import Citation
from lumina.schemas.common import DocumentReference
from lumina.services.ai.stages.citations import resolve_citations


def test_resolve_citations_with_new_pipeline_chunks():
    """
    Garante que resolve_citations aceita os chunks gerados pelo novo pipeline
    e devolve referências válidas segundo o schema DocumentReference.
    """
    chunk = Document(
        page_content=(
            '[Habilitação] O licitante deverá comprovar sua qualificação.'
        ),
        metadata={
            'chunk_id': 'chunk_0_3',
            'page': 0,
            'rects': [
                [50.0, 100.0, 500.0, 115.0],
                [50.0, 120.0, 480.0, 135.0],
            ],
            'section_title': 'Habilitação',
        },
    )

    citation = Citation(
        chunk_id='chunk_0_3',
        text_snippet='comprovar sua qualificação',
    )

    resolved = resolve_citations([citation], [chunk])

    assert len(resolved) == 1
    ref = resolved[0]
    assert ref['chunk_id'] == 'chunk_0_3'
    assert ref['page'] == 0
    assert ref['text_snippet'] == 'comprovar sua qualificação'
    assert len(ref['rects']) == 2
    assert ref['rects'][0] == {
        'x1': 50.0,
        'y1': 100.0,
        'x2': 500.0,
        'y2': 115.0,
    }

    validated = DocumentReference.model_validate(ref)
    assert validated.page == 0
    assert len(validated.rects) == 2
    assert validated.rects[0].x1 == 50.0


def chunk_com_frases() -> Document:
    return Document(
        page_content='[Método] Primeira frase. Segunda frase. Terceira frase.',
        metadata={
            'chunk_id': 'chunk_3_1',
            'page': 3,
            'rects': [
                [10.0, 10.0, 90.0, 20.0],
                [10.0, 22.0, 90.0, 32.0],
                [10.0, 34.0, 90.0, 44.0],
            ],
            'sentences': [
                {
                    'n': 1,
                    'start': 9,
                    'end': 24,
                    'rects': [[10.0, 10.0, 90.0, 20.0]],
                },
                {
                    'n': 2,
                    'start': 25,
                    'end': 39,
                    'rects': [[10.0, 22.0, 90.0, 32.0]],
                },
                {'n': 3, 'start': 40, 'end': 55, 'rects': []},
            ],
        },
    )


def rects_de(ref: dict) -> list[float]:
    return [rect['y1'] for rect in ref['rects']]


def test_citacao_de_uma_frase_destaca_so_a_frase():
    [ref] = resolve_citations(
        [Citation(chunk_id='chunk_3_1', sentences=[2])], [chunk_com_frases()]
    )

    assert ref['chunk_id'] == 'chunk_3_1'
    assert ref['page'] == 3
    assert rects_de(ref) == [22.0]
    assert ref['text_snippet'] == 'Segunda frase.'
    DocumentReference.model_validate(ref)


def test_frases_vizinhas_viram_uma_referencia_na_ordem_de_leitura():
    [ref] = resolve_citations(
        [Citation(chunk_id='chunk_3_1', sentences=[2, 1])],
        [chunk_com_frases()],
    )

    assert rects_de(ref) == [10.0, 22.0]
    assert ref['text_snippet'] == 'Primeira frase. Segunda frase.'


def test_citacoes_diferentes_no_mesmo_chunk_geram_duas_referencias():
    refs = resolve_citations(
        [
            Citation(chunk_id='chunk_3_1', sentences=[1]),
            Citation(chunk_id='chunk_3_1', sentences=[2]),
        ],
        [chunk_com_frases()],
    )

    assert [rects_de(ref) for ref in refs] == [[10.0], [22.0]]


def test_citacao_repetida_gera_uma_referencia():
    refs = resolve_citations(
        [
            Citation(chunk_id='chunk_3_1', sentences=[1, 2]),
            Citation(chunk_id='chunk_3_1', sentences=[2, 1, 1]),
        ],
        [chunk_com_frases()],
    )

    assert len(refs) == 1


def test_numero_de_frase_inexistente_e_ignorado_e_registrado():
    with patch('lumina.services.ai.stages.citations.logger') as logger:
        [ref] = resolve_citations(
            [Citation(chunk_id='chunk_3_1', sentences=[2, 40])],
            [chunk_com_frases()],
        )

    assert rects_de(ref) == [22.0]
    assert '[40]' in str(logger.warning.call_args)


def test_citacao_sem_frase_valida_destaca_o_chunk_inteiro():
    for numbers in ([], [40]):
        [ref] = resolve_citations(
            [Citation(chunk_id='chunk_3_1', sentences=numbers)],
            [chunk_com_frases()],
        )
        assert rects_de(ref) == [10.0, 22.0, 34.0]


def test_frase_sem_retangulo_destaca_o_chunk_inteiro():
    [ref] = resolve_citations(
        [Citation(chunk_id='chunk_3_1', sentences=[3])], [chunk_com_frases()]
    )

    assert rects_de(ref) == [10.0, 22.0, 34.0]
    assert ref['text_snippet'] == 'Terceira frase.'


def test_modelo_pode_citar_frases_com_o_marcador():
    citation = Citation(chunk_id='chunk_3_1', sentences=['s2', 3, 'x'])

    assert citation.sentences == [2, 3]


def test_citacao_com_frases_nulas_vale_como_sem_frases():
    assert Citation(chunk_id='chunk_3_1', sentences=None).sentences == []
