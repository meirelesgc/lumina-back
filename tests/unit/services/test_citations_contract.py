# ruff: noqa: PLR2004
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
