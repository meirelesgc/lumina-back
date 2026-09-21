# ruff: noqa: PLR2004
from unittest.mock import MagicMock

from langchain_core.documents import Document

from lumina.services.ai.stages.positioning import (
    char_range_to_blocks,
    enrich_chunks_with_line_rects,
    locate_range,
    words_to_line_rects,
)

MD = (
    '# Titulo\n\n'
    'O fornecedor deve **apresentar** certidao negativa.\n\n'
    'Texto final aqui.'
)

# Palavras PyMuPDF: (x0, y0, x1, y1, texto, block_no, line_no, word_no)
WORDS = [
    (10.0, 100.0, 40.0, 110.0, 'O', 0, 0, 0),
    (42.0, 100.0, 90.0, 110.0, 'fornecedor', 0, 0, 1),
    (92.0, 100.0, 120.0, 110.0, 'deve', 0, 0, 2),
    (10.0, 112.0, 80.0, 122.0, 'apresentar', 0, 1, 0),
    (82.0, 112.0, 130.0, 122.0, 'certidao', 0, 1, 1),
    (132.0, 112.0, 170.0, 122.0, 'negativa.', 0, 1, 2),
]


def _make_pages():
    start = MD.index('O fornecedor')
    end = MD.index('negativa.') + len('negativa.')
    return [
        {
            'page': 0,
            'char_start': 0,
            'boxes': [
                {
                    'class': 'page-header',
                    'bbox': [0, 0, 10, 10],
                    'pos': [0, 8],
                },
                {
                    'class': 'text',
                    'bbox': [5.0, 95.0, 175.0, 125.0],
                    'pos': [start, end],
                },
            ],
        }
    ]


def test_char_range_to_blocks_filters_header():
    blocks = char_range_to_blocks(_make_pages(), 0, len(MD))
    assert len(blocks) == 1
    assert blocks[0]['class'] == 'text'
    assert blocks[0]['page'] == 0


def test_locate_range_line_rects_alignment():
    start = MD.index('O fornecedor')
    end = MD.index('negativa.') + len('negativa.')
    rects = locate_range(_make_pages(), MD, start, end, lambda p: WORDS)

    assert len(rects) == 2
    # Primeira linha: (10, 100, 120, 110)
    assert rects[0] == (10.0, 100.0, 120.0, 110.0)
    # Segunda linha: (10, 112, 170, 122)
    assert rects[1] == (10.0, 112.0, 170.0, 122.0)


def test_words_to_line_rects_merges_visual_line():
    words = [
        (0.0, 10.0, 8.0, 20.0, 'a)', 0, 0, 0),
        (12.0, 10.5, 90.0, 20.5, 'texto', 0, 1, 0),
    ]
    merged = words_to_line_rects(words)
    assert len(merged) == 1
    assert merged[0][0] == 0.0
    assert merged[0][2] == 90.0


def test_enrich_chunks_with_line_rects_legacy_format():
    start = MD.index('O fornecedor')
    end = MD.index('negativa.') + len('negativa.')
    chunk = Document(
        page_content='O fornecedor deve apresentar certidao negativa.',
        metadata={
            'chunk_id': 'chunk_0_0',
            'page': 0,
            'char_start': start,
            'char_end': end,
        },
    )

    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = WORDS
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1

    enrich_chunks_with_line_rects([chunk], mock_doc, _make_pages(), MD)

    assert 'rects' in chunk.metadata
    rects = chunk.metadata['rects']
    assert len(rects) == 2
    assert rects[0] == [10.0, 100.0, 120.0, 110.0]
    assert rects[1] == [10.0, 112.0, 170.0, 122.0]
