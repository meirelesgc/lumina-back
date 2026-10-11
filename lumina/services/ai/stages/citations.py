from typing import Any, Dict, List

from lumina.schemas.ai import Citation

RECT_COORDS_COUNT = 4


def resolve_citations(
    citations: List[Citation], retrieved_chunks: List[Any]
) -> List[Dict]:
    """
    Resolve identificadores de chunks em retângulos físicos
    (rects: x1, y1, x2, y2) e número de página para destaque no PDF.
    """
    resolved = []
    chunk_map = {
        chunk.metadata.get('chunk_id'): chunk.metadata
        for chunk in retrieved_chunks
        if hasattr(chunk, 'metadata') and chunk.metadata.get('chunk_id')
    }

    seen = set()
    for citation in citations:
        if citation.chunk_id in seen:
            continue

        if citation.chunk_id in chunk_map:
            meta = chunk_map[citation.chunk_id]
            raw_rects = meta.get('rects', [])
            mapped_rects = []
            for r in raw_rects:
                if len(r) == RECT_COORDS_COUNT:
                    mapped_rects.append({
                        'x1': r[0],
                        'y1': r[1],
                        'x2': r[2],
                        'y2': r[3],
                    })

            resolved.append({
                'chunk_id': citation.chunk_id,
                'text_snippet': citation.text_snippet,
                'page': meta.get('page'),
                'rects': mapped_rects,
            })
            seen.add(citation.chunk_id)

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
