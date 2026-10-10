"""
Etapas determinísticas da geração de sugestões: unidades de texto e lotes,
normalização, verificação de evidências e comparação de títulos.
"""

import re
import unicodedata
from bisect import bisect_left
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

from rapidfuzz import fuzz

from lumina.services.ai.stages.section_models import Section
from lumina.services.ai.stages.sections import flatten_sections

MARKDOWN_NOISE = re.compile(r'[*_#>|`]')
HYPHEN_BREAK = re.compile(r'(\w)-\s*\n\s*(\w)')
TITLE_NOISE = re.compile(r'[^0-9a-z]+')


@dataclass
class TextUnit:
    """Trecho contíguo do documento (seção ou preâmbulo)."""

    title: str
    char_start: int
    char_end: int


@dataclass
class TextBatch:
    """Conjunto de unidades enviado numa única chamada ao modelo."""

    index: int
    char_start: int
    char_end: int
    text: str


@dataclass
class EvidenceMatch:
    quote: str
    pages: List[int]
    char_start: int
    char_end: int
    score: float


def build_text_units(
    full_text: str, sections: Sequence[Section]
) -> List[TextUnit]:
    """
    Particiona o texto pelos inícios de seção, sem sobreposição. O trecho
    anterior ao primeiro cabeçalho vira a unidade 'Preâmbulo'. Sem seções,
    o documento inteiro é uma unidade só.
    """
    starts: List[Tuple[int, str]] = []
    for sec in flatten_sections(list(sections)):
        start = (
            sec.heading_char_start
            if sec.heading_char_start is not None
            else sec.char_start
        )
        if start is None:
            continue
        label = ' > '.join([*sec.breadcrumb, sec.title]) or sec.title
        starts.append((start, label))

    starts = sorted(dict(starts).items())
    units: List[TextUnit] = []
    first_start = starts[0][0] if starts else len(full_text)
    if full_text[:first_start].strip():
        units.append(TextUnit('Preâmbulo', 0, first_start))

    for idx, (start, label) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(full_text)
        if full_text[start:end].strip():
            units.append(TextUnit(label, start, end))

    return units


def build_batches(
    full_text: str, units: Sequence[TextUnit], max_chars: int
) -> List[TextBatch]:
    """
    Agrupa unidades consecutivas até `max_chars`. Uma unidade maior que o
    orçamento é fatiada em pedaços de no máximo `max_chars`.
    """
    pieces: List[TextUnit] = []
    for unit in units:
        start = unit.char_start
        while unit.char_end - start > max_chars:
            pieces.append(TextUnit(unit.title, start, start + max_chars))
            start += max_chars
        pieces.append(TextUnit(unit.title, start, unit.char_end))

    batches: List[TextBatch] = []
    current: List[TextUnit] = []

    def flush() -> None:
        if not current:
            return
        start, end = current[0].char_start, current[-1].char_end
        batches.append(
            TextBatch(len(batches), start, end, full_text[start:end])
        )
        current.clear()

    for piece in pieces:
        size = piece.char_end - piece.char_start
        if current and (piece.char_end - current[0].char_start) > max_chars:
            flush()
        current.append(piece)
        if size >= max_chars:
            flush()
    flush()
    return batches


def normalize_with_map(text: str) -> Tuple[str, List[int]]:
    """
    Normaliza para comparação (casefold, sem marcação Markdown, sem hífen
    de quebra de linha, espaços colapsados) e devolve, para cada caractere
    normalizado, o índice correspondente no texto original.
    """
    chars: List[str] = []
    index_map: List[int] = []
    i = 0
    length = len(text)
    pending_space = False

    while i < length:
        ch = text[i]
        if ch == '-' and i + 1 < length:
            j = i + 1
            while j < length and text[j] in ' \t':
                j += 1
            if (
                j < length
                and text[j] == '\n'
                and chars
                and chars[-1].isalnum()
            ):
                i = j + 1
                while i < length and text[i].isspace():
                    i += 1
                continue
        if MARKDOWN_NOISE.match(ch):
            i += 1
            continue
        if ch.isspace():
            pending_space = bool(chars)
            i += 1
            continue
        if pending_space:
            chars.append(' ')
            index_map.append(i)
            pending_space = False
        for folded in ch.casefold():
            chars.append(folded)
            index_map.append(i)
        i += 1

    return ''.join(chars), index_map


def normalize(text: str) -> str:
    return normalize_with_map(text)[0]


def offset_to_page(page_map: Sequence[Dict[str, Any]], offset: int) -> int:
    """Converte offset do texto completo em número de página (base 1)."""
    page = 0
    for entry in page_map:
        if entry.get('char_start', 0) <= offset:
            page = entry.get('page', page)
        else:
            break
    return page + 1


def pages_for_range(
    page_map: Sequence[Dict[str, Any]], start: int, end: int
) -> List[int]:
    first = offset_to_page(page_map, start)
    last = offset_to_page(page_map, max(start, end - 1))
    return list(range(first, last + 1))


class EvidenceLocator:
    """Localiza trechos citados pelo modelo no texto extraído."""

    def __init__(
        self,
        full_text: str,
        page_map: Sequence[Dict[str, Any]],
        min_score: float,
    ):
        self.full_text = full_text
        self.page_map = page_map
        self.min_score = min_score
        self.normalized, self.index_map = normalize_with_map(full_text)

    def _norm_range(self, start: int, end: int) -> Tuple[int, int]:
        return (
            bisect_left(self.index_map, start),
            bisect_left(self.index_map, end),
        )

    def _build(
        self, quote: str, norm_start: int, norm_end: int, score: float
    ) -> EvidenceMatch:
        start = self.index_map[norm_start]
        end = self.index_map[norm_end - 1] + 1
        return EvidenceMatch(
            quote=quote.strip(),
            pages=pages_for_range(self.page_map, start, end),
            char_start=start,
            char_end=end,
            score=score,
        )

    def locate(
        self,
        quote: str,
        hint_range: Optional[Tuple[int, int]] = None,
    ) -> Optional[EvidenceMatch]:
        """
        Procura o trecho de forma exata (normalizada) no documento e, se não
        encontrar, por similaridade aproximada dentro de `hint_range`.
        """
        needle = normalize(quote)
        if not needle:
            return None

        position = self.normalized.find(needle)
        if position >= 0:
            return self._build(quote, position, position + len(needle), 100)

        lo, hi = (
            self._norm_range(*hint_range)
            if hint_range
            else (0, len(self.normalized))
        )
        haystack = self.normalized[lo:hi]
        if not haystack:
            return None

        alignment = fuzz.partial_ratio_alignment(needle, haystack)
        if alignment is None or alignment.score < self.min_score:
            return None
        return self._build(
            quote,
            lo + alignment.dest_start,
            lo + alignment.dest_end,
            alignment.score,
        )


def normalize_title(title: str) -> str:
    """Normaliza títulos para comparação (sem acentos e pontuação)."""
    decomposed = unicodedata.normalize('NFKD', title or '')
    stripped = ''.join(c for c in decomposed if not unicodedata.combining(c))
    return TITLE_NOISE.sub(' ', stripped.casefold()).strip()


def find_similar_title(
    title: str, candidates: Iterable[Tuple[UUID, str]]
) -> Optional[Tuple[UUID, str]]:
    """Retorna a entidade cujo título normalizado é igual ao informado."""
    target = normalize_title(title)
    if not target:
        return None
    for entity_id, candidate_title in candidates:
        if normalize_title(candidate_title) == target:
            return entity_id, candidate_title
    return None
