from uuid import uuid4

from lumina.services.ai.stages.section_models import Heading, Section
from lumina.services.ai.tree_suggestion.text import (
    EvidenceLocator,
    TextUnit,
    build_batches,
    build_text_units,
    find_similar_title,
    normalize,
    normalize_title,
)

PAGE_MAP = [
    {'page': 0, 'char_start': 0},
    {'page': 1, 'char_start': 100},
    {'page': 2, 'char_start': 200},
]


def _section(title, start):
    return Section(
        heading=Heading(line_number=0, level=1, title=title, raw=title),
        char_start=start,
        heading_char_start=start,
    )


def test_build_text_units_partitions_text_with_preamble():
    text = 'Intro. ' + 'A' * 20 + 'B' * 20
    sections = [_section('Seção A', 7), _section('Seção B', 27)]

    units = build_text_units(text, sections)

    assert [u.title for u in units] == ['Preâmbulo', 'Seção A', 'Seção B']
    assert [(u.char_start, u.char_end) for u in units] == [
        (0, 7),
        (7, 27),
        (27, 47),
    ]


def test_build_text_units_without_sections_uses_whole_document():
    units = build_text_units('texto sem cabeçalhos', [])

    assert len(units) == 1
    assert units[0].char_end == len('texto sem cabeçalhos')


def test_build_batches_respects_budget_and_order():
    text = 'x' * 250
    units = [
        TextUnit('a', 0, 40),
        TextUnit('b', 40, 90),
        TextUnit('c', 90, 250),
    ]

    batches = build_batches(text, units, max_chars=100)

    assert all(len(b.text) <= 100 for b in batches)  # noqa: PLR2004
    assert batches[0].char_start == 0
    assert batches[-1].char_end == 250  # noqa: PLR2004
    assert [b.index for b in batches] == list(range(len(batches)))
    starts = [b.char_start for b in batches]
    assert starts == sorted(starts)


def test_normalize_removes_markup_hyphen_breaks_and_spaces():
    assert normalize('**O  RESU-\nMO** deve\n ter') == 'o resumo deve ter'


def test_locate_exact_quote_returns_pages():
    text = 'a' * 150 + ' O resumo deve conter 500 palavras. ' + 'b' * 100
    locator = EvidenceLocator(text, PAGE_MAP, min_score=90)

    match = locator.locate('o resumo deve CONTER 500 palavras')

    assert match is not None
    assert match.pages == [2]
    assert match.score == 100  # noqa: PLR2004


def test_locate_quote_across_line_break_and_pages():
    text = (
        'x' * 90 + ' O texto deve ser digi-\ntado em fonte Arial. ' + 'y' * 50
    )
    locator = EvidenceLocator(text, PAGE_MAP, min_score=90)

    match = locator.locate('O texto deve ser digitado em fonte Arial.')

    assert match is not None
    assert match.pages == [1, 2]


def test_locate_fuzzy_within_hint_range():
    text = 'z' * 120 + ' As margens superior e esquerda devem ter 3 cm. '
    locator = EvidenceLocator(text, PAGE_MAP, min_score=90)

    match = locator.locate(
        'As margens superior e esquerda devem ter 3cm.',
        hint_range=(100, len(text)),
    )

    assert match is not None
    assert match.pages == [2]


def test_locate_rejects_invented_quote():
    text = 'O resumo deve conter no máximo 500 palavras.'
    locator = EvidenceLocator(text, PAGE_MAP, min_score=90)

    assert locator.locate('O espaçamento entre linhas deve ser duplo.') is None


def test_find_similar_title_ignores_accents_and_punctuation():
    existing_id = uuid4()
    scope = [(uuid4(), 'Referências'), (existing_id, 'Elementos Pré-textuais')]

    assert normalize_title('Elementos pré textuais!') == (
        'elementos pre textuais'
    )
    assert find_similar_title('elementos pre-textuais', scope) == (
        existing_id,
        'Elementos Pré-textuais',
    )
    assert find_similar_title('Formatação', scope) is None
