import re
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Tuple

from langchain_core.documents import Document

# Classes de box do pymupdf4llm que nao carregam texto de conteudo principal
IGNORED_BOX_CLASSES = frozenset({'page-header', 'page-footer', 'picture'})

_MARKUP_RE = re.compile(r'[*_`#|>\\]+')
_SEPARATOR_RE = re.compile(r'^[-:\s]*$')

Rect = Tuple[float, float, float, float]
Word = Tuple[float, float, float, float, str, int, int, int]
WordsProvider = Callable[[int], List[Word]]


def normalize_token(token: str) -> str:
    return _MARKUP_RE.sub('', token).lower()


def tokenize_with_offsets(text: str, base: int = 0) -> List[Tuple[str, int]]:
    """
    Tokens normalizados (sem markup) com o offset absoluto de cada um.
    """
    tokens: List[Tuple[str, int]] = []
    for match in re.finditer(r'\S+', text):
        raw = match.group()
        if _SEPARATOR_RE.match(raw):
            continue
        norm = normalize_token(raw)
        if norm:
            tokens.append((norm, base + match.start()))
    return tokens


def char_range_to_blocks(
    pages: List[Dict[str, Any]], start: int, end: int
) -> List[Dict[str, Any]]:
    """
    Boxes de conteudo que intersectam [start, end) do markdown consolidado.
    """
    blocks: List[Dict[str, Any]] = []
    for page in pages:
        base = page.get('char_start', 0)
        for box in page.get('boxes', []):
            if box.get('class') in IGNORED_BOX_CLASSES:
                continue
            box_start = base + box['pos'][0]
            box_end = base + box['pos'][1]
            if box_start < end and box_end > start:
                blocks.append({
                    'page': page['page'],
                    'bbox': tuple(box['bbox']),
                    'class': box.get('class'),
                    'box_start': box_start,
                    'box_end': box_end,
                })
    return blocks


def _center_inside(word: Word, bbox: Rect, tol: float = 1.5) -> bool:
    cx = (word[0] + word[2]) / 2
    cy = (word[1] + word[3]) / 2
    return (
        bbox[0] - tol <= cx <= bbox[2] + tol
        and bbox[1] - tol <= cy <= bbox[3] + tol
    )


def _union(rects: List[Rect]) -> Rect:
    return (
        min(r[0] for r in rects),
        min(r[1] for r in rects),
        max(r[2] for r in rects),
        max(r[3] for r in rects),
    )


def words_to_line_rects(words: List[Word]) -> List[Rect]:
    """
    Agrupa palavras por (block_no, line_no) e une seus retangulos.
    Funde grupos na mesma linha visual com sobreposicao vertical > 50%.
    """
    if not words:
        return []

    groups: Dict[Tuple[int, int], List[Rect]] = {}
    for w in words:
        groups.setdefault((w[5], w[6]), []).append((w[0], w[1], w[2], w[3]))

    merged: List[Rect] = []
    sorted_rects = sorted(
        (_union(rs) for rs in groups.values()), key=lambda r: (r[1], r[0])
    )

    for rect in sorted_rects:
        if merged:
            prev = merged[-1]
            overlap = min(prev[3], rect[3]) - max(prev[1], rect[1])
            min_height = min(prev[3] - prev[1], rect[3] - rect[1])
            if min_height > 0 and overlap > 0.5 * min_height:
                merged[-1] = _union([prev, rect])
                continue
        merged.append(rect)
    return merged


def refine_block_to_line_rects(  # noqa: PLR0913, PLR0917
    markdown: str,
    block: Dict[str, Any],
    start: int,
    end: int,
    words: List[Word],
    min_match_ratio: float = 0.3,
) -> List[Rect]:
    """
    Alinha os tokens do markdown do box com as palavras do PDF contidas no bbox
    via difflib e devolve as linhas correspondentes ao trecho.
    """
    fallback = [tuple(float(v) for v in block['bbox'])]

    box_words = sorted(
        (w for w in words if _center_inside(w, block['bbox'])),
        key=lambda w: (w[5], w[6], w[7]),
    )
    box_tokens = tokenize_with_offsets(
        markdown[block['box_start'] : block['box_end']],
        base=block['box_start'],
    )
    if not box_words or not box_tokens:
        return fallback

    word_tokens = [(i, normalize_token(w[4])) for i, w in enumerate(box_words)]
    word_tokens = [(i, t) for i, t in word_tokens if t]
    if not word_tokens:
        return fallback

    matcher = SequenceMatcher(
        None,
        [t for t, _ in box_tokens],
        [t for _, t in word_tokens],
        autojunk=False,
    )
    matched = matcher.get_matching_blocks()
    matched_count = sum(m.size for m in matched)
    if not box_tokens or (matched_count / len(box_tokens)) < min_match_ratio:
        return fallback

    token_to_word: Dict[int, int] = {}
    for m in matched:
        for k in range(m.size):
            token_to_word[m.a + k] = word_tokens[m.b + k][0]

    selected = [
        token_to_word[i]
        for i, (_, offset) in enumerate(box_tokens)
        if start <= offset < end and i in token_to_word
    ]
    if not selected:
        return fallback

    lo, hi = min(selected), max(selected)
    return words_to_line_rects(box_words[lo : hi + 1])


def locate_range(
    pages: List[Dict[str, Any]],
    markdown: str,
    start: int,
    end: int,
    words_provider: WordsProvider,
) -> List[Rect]:
    """
    Retorna lista de retangulos de linha (x0, y0, x1, y1) para o trecho.
    """
    result: List[Rect] = []
    for block in char_range_to_blocks(pages, start, end):
        rects = refine_block_to_line_rects(
            markdown, block, start, end, words_provider(block['page'])
        )
        result.extend(rects)
    return result


def enrich_chunks_with_line_rects(
    chunks: List[Document],
    pdf_doc: Any,
    page_map: List[Dict[str, Any]],
    full_markdown: str,
) -> List[Document]:
    """
    Enriquece cada chunk com seus retangulos por linha no formato legado:
    metadata['rects'] = [[x0, y0, x1, y1], ...]
    """
    cache: Dict[int, List[Word]] = {}

    def provider(page_idx: int) -> List[Word]:
        if page_idx not in cache:
            if 0 <= page_idx < len(pdf_doc):
                cache[page_idx] = pdf_doc[page_idx].get_text('words')
            else:
                cache[page_idx] = []
        return cache[page_idx]

    for chunk in chunks:
        c_start = chunk.metadata.get('char_start')
        c_end = chunk.metadata.get('char_end')
        c_page = chunk.metadata.get('page')

        if c_start is None or c_end is None or c_page is None:
            chunk.metadata['rects'] = []
            continue

        page_blocks = [p for p in page_map if p['page'] == c_page]
        raw_rects = locate_range(
            page_blocks, full_markdown, c_start, c_end, provider
        )

        formatted_rects = [
            [
                round(float(r[0]), 2),
                round(float(r[1]), 2),
                round(float(r[2]), 2),
                round(float(r[3]), 2),
            ]
            for r in raw_rects
        ]
        chunk.metadata['rects'] = formatted_rects

    return chunks
