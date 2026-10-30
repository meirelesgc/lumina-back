import logging
from typing import Any, Dict, List

from lumina.schemas.ai import Citation

logger = logging.getLogger(__name__)

RECT_COORDS_COUNT = 4


def cited_sentences(citation: Citation, meta: Dict) -> List[Dict]:
    """
    Frases citadas que existem no chunk, em ordem de leitura. Números
    inexistentes ficam de fora e vão para o log.
    """
    by_number = {s['n']: s for s in meta.get('sentences') or []}
    numbers = sorted(set(citation.sentences))
    invalid = [n for n in numbers if n not in by_number]
    if invalid:
        logger.warning(
            'Frases inexistentes citadas em %s: %s',
            citation.chunk_id,
            invalid,
        )
    return [by_number[n] for n in numbers if n in by_number]


def resolve_citations(
    citations: List[Citation], retrieved_chunks: List[Any]
) -> List[Dict]:
    """
    Resolve citações em retângulos físicos (rects: x1, y1, x2, y2) e número
    de página para destaque no PDF. Usa os retângulos das frases citadas e,
    sem eles, os do chunk inteiro.
    """
    resolved = []
    chunk_map = {
        chunk.metadata.get('chunk_id'): chunk
        for chunk in retrieved_chunks
        if hasattr(chunk, 'metadata') and chunk.metadata.get('chunk_id')
    }

    seen = set()
    for citation in citations:
        if citation.chunk_id not in chunk_map:
            continue

        chunk = chunk_map[citation.chunk_id]
        meta = chunk.metadata
        sentences = cited_sentences(citation, meta)
        key = (citation.chunk_id, tuple(s['n'] for s in sentences))
        if key in seen:
            continue

        raw_rects = [r for s in sentences for r in s['rects']]
        mapped_rects = []
        for r in raw_rects or meta.get('rects', []):
            if len(r) == RECT_COORDS_COUNT:
                mapped_rects.append({
                    'x1': r[0],
                    'y1': r[1],
                    'x2': r[2],
                    'y2': r[3],
                })

        snippet = ' '.join(
            chunk.page_content[s['start'] : s['end']] for s in sentences
        )
        resolved.append({
            'chunk_id': citation.chunk_id,
            'text_snippet': snippet or citation.text_snippet,
            'page': meta.get('page'),
            'rects': mapped_rects,
        })
        seen.add(key)

    return resolved


def process_citations(
    raw_citations: list, chunks: list
) -> tuple[list[str], list[str], list[dict]]:
    """
    Filtra citações retornadas pela LLM, separando citações válidas
    de alucinações e resolvendo as coordenadas das válidas.
    Retorna: (fornecidas, alucinadas, referências_resolvidas).
    """
    valid_chunk_ids = set()
    for d in chunks:
        cid = d.metadata.get('chunk_id') if hasattr(d, 'metadata') else None
        if not cid and hasattr(d, 'id'):
            cid = str(d.id)
        if cid:
            valid_chunk_ids.add(str(cid))

    provided: list[str] = []
    hallucinated: list[str] = []
    valid_objs: list[Citation] = []

    for c in raw_citations:
        cid = None
        if isinstance(c, dict):
            cid = str(c.get('chunk_id') or '')
            if cid in valid_chunk_ids:
                valid_objs.append(Citation(**c))
            elif cid:
                hallucinated.append(cid)
        elif isinstance(c, Citation):
            cid = str(c.chunk_id or '')
            if cid in valid_chunk_ids:
                valid_objs.append(c)
            elif cid:
                hallucinated.append(cid)
        if cid:
            provided.append(cid)

    resolved_refs = resolve_citations(valid_objs, chunks)
    return provided, hallucinated, resolved_refs
