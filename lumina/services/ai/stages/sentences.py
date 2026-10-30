import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

Span = Tuple[int, int]
# Trecho anonimizado: (início e fim no original, início e fim no anonimizado)
Change = Tuple[int, int, int, int]

MIN_SENTENCE_CHARS = 40
ABBREVIATIONS = frozenset({
    'al.',
    'art.',
    'arts.',
    'cap.',
    'dr.',
    'dra.',
    'ed.',
    'eq.',
    'etc.',
    'fig.',
    'figs.',
    'inc.',
    'n.',
    'nº.',
    'p.',
    'pp.',
    'prof.',
    'profa.',
    'sr.',
    'sra.',
    'tab.',
    'v.',
    'vol.',
})
BOUNDARY = re.compile(
    r'\n{2,}'
    r'|\n(?=\s*(?:[-*|#]|\d+[.)]\s))'
    r'|(?<=[.!?;:])\s+(?=[A-ZÀ-Ý0-9(\[*-])'
)
INITIAL = re.compile(r'^[A-ZÀ-Ý]\.$')


def _ends_in_abbreviation(text: str, position: int) -> bool:
    words = text[:position].rsplit(maxsplit=1)
    if not words:
        return False
    word = words[-1].lstrip('([*')
    return word.lower() in ABBREVIATIONS or bool(INITIAL.match(word))


def _raw_spans(text: str) -> List[Span]:
    spans: List[Span] = []
    cursor = 0
    for match in BOUNDARY.finditer(text):
        if '\n\n' not in match.group() and _ends_in_abbreviation(
            text, match.start()
        ):
            continue
        spans.append((cursor, match.start()))
        cursor = match.end()
    spans.append((cursor, len(text)))
    return [span for span in spans if text[span[0] : span[1]].strip()]


def _merge_fragments(text: str, spans: List[Span]) -> List[Span]:
    """
    Junta fragmentos curtos à frase seguinte. O último fragmento não tem
    frase seguinte e fica na anterior.
    """
    merged: List[Span] = []
    pending: Optional[int] = None
    for span_start, end in spans:
        start = span_start if pending is None else pending
        if len(text[start:end].strip()) < MIN_SENTENCE_CHARS:
            pending = start
            continue
        merged.append((start, end))
        pending = None

    if pending is not None:
        if merged:
            merged[-1] = (merged[-1][0], spans[-1][1])
        else:
            merged.append((pending, spans[-1][1]))
    return merged


def _strip_span(text: str, span: Span) -> Span:
    start, end = span
    raw = text[start:end]
    return (
        start + len(raw) - len(raw.lstrip()),
        end - (len(raw) - len(raw.rstrip())),
    )


def split_sentences(text: str) -> List[Span]:
    """
    Posições das frases do texto, na ordem de leitura e sem os espaços das
    pontas. Só espaços ficam fora das frases.
    """
    spans = _merge_fragments(text, _raw_spans(text))
    return [_strip_span(text, span) for span in spans]


def mark_sentences(
    content: str, sentences: Optional[Sequence[Dict[str, Any]]]
) -> str:
    """
    Texto do chunk com o marcador `[sN]` antes de cada frase. Chunks
    indexados sem frases voltam como estão.
    """
    if not sentences:
        return content

    parts = [content[: sentences[0]['start']]]
    for index, sentence in enumerate(sentences):
        following = (
            sentences[index + 1]['start']
            if index + 1 < len(sentences)
            else len(content)
        )
        parts.append(f'[s{sentence["n"]}] ')
        parts.append(content[sentence['start'] : following])
    return ''.join(parts)


def _move(position: int, changes: Sequence[Change]) -> int:
    """
    Leva uma posição do texto original para o anonimizado. Uma posição
    dentro de uma entidade vai para o fim do marcador.
    """
    delta = 0
    for old_start, old_end, _, new_end in changes:
        if position <= old_start:
            break
        if position < old_end:
            return new_end
        delta = new_end - old_end
    return position + delta


def remap_sentences(
    sentences: List[Dict[str, Any]], changes: Sequence[Change]
) -> List[Dict[str, Any]]:
    """
    Atualiza as posições das frases depois da anonimização. Uma frase que
    fica toda dentro de uma entidade sai da lista.
    """
    remapped: List[Dict[str, Any]] = []
    for sentence in sentences:
        start = _move(sentence['start'], changes)
        end = _move(sentence['end'], changes)
        if start < end:
            remapped.append({
                **sentence,
                'n': len(remapped) + 1,
                'start': start,
                'end': end,
            })
    return remapped
