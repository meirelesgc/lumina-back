from typing import List

from langchain_core.documents import Document

from lumina.core.dependencies import VStore


async def index_chunks_to_vstore(
    vstore: VStore,
    chunks: List[Document],
) -> None:
    """
    Grava os chunks na base vetorial (PGVector / VStore).
    """
    if not chunks:
        return

    await vstore.aadd_documents(chunks)
