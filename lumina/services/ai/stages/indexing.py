from datetime import datetime
from typing import List, Optional
from uuid import UUID

from langchain_core.documents import Document

from lumina.core.dependencies import VStore
from lumina.services.run_logger import get_run_logger


async def index_chunks_to_vstore(
    vstore: VStore,
    chunks: List[Document],
    run_id: Optional[UUID] = None,
) -> None:
    """
    Grava os chunks na base vetorial (PGVector / VStore) e
    registra a telemetria no RunLogger.
    """
    if not chunks:
        return

    run_logger = get_run_logger()
    t_start = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='embeddings')

    try:
        await vstore.aadd_documents(chunks)
        if run_id:
            d_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.complete_stage(
                run_id=run_id,
                stage='embeddings',
                duration_ms=d_ms,
                item_count=len(chunks),
                data={'chunks_count': len(chunks)},
            )
    except Exception as e:
        if run_id:
            d_embed = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.fail_stage(
                run_id=run_id,
                stage='embeddings',
                error=str(e),
                duration_ms=d_embed,
            )
        raise
