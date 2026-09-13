from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

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
    raw_citations: list, sessions: list
) -> tuple[list[str], list[str], list[dict]]:
    """
    Filtra citações retornadas pela LLM, separando citações válidas
    de alucinações e resolvendo as coordenadas das válidas.
    Retorna: (fornecidas, alucinadas, referências_resolvidas).
    """
    valid_chunk_ids = set()
    for d in sessions:
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

    resolved_refs = resolve_citations(valid_objs, sessions)
    return provided, hallucinated, resolved_refs


def audit_citations(simplified_args: list[dict]) -> dict:
    """
    Consolida métricas de citações fornecidas, alucinadas e caixas resolvidas
    para a auditoria de release.
    """
    all_cited: list[str] = []
    total_hallucinated = 0
    total_boxes = 0
    for item in simplified_args:
        for cid in item.get('citations_provided', []):
            all_cited.append(cid)
        total_hallucinated += len(item.get('citations_hallucinated', []))
        for ref in item.get('references', []):
            total_boxes += len(ref.get('rects', []))

    return {
        'chunks_cited': sorted(list(set(all_cited))),
        'hallucinated_citations_count': total_hallucinated,
        'resolved_boxes_count': total_boxes,
    }


async def record_citations_stage(
    run_logger: Any,
    release_id: UUID,
    simplified_args: list[dict],
) -> None:
    """
    Registra a macroetapa de citações no RunLogger.
    """
    t_cit = datetime.now()
    await run_logger.start_stage(run_id=release_id, stage='citations')
    try:
        cit_data = audit_citations(simplified_args)
        d_cit = int((datetime.now() - t_cit).total_seconds() * 1000)
        await run_logger.complete_stage(
            run_id=release_id,
            stage='citations',
            duration_ms=d_cit,
            item_count=len(cit_data['chunks_cited']),
            data=cit_data,
        )
    except Exception as e:
        d_cit = int((datetime.now() - t_cit).total_seconds() * 1000)
        await run_logger.fail_stage(
            run_id=release_id,
            stage='citations',
            error=str(e),
            duration_ms=d_cit,
        )
        raise
