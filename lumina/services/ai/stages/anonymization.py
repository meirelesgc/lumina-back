from typing import List

from langchain_core.documents import Document

from lumina.utils.PresidioAnonymizer import PresidioAnonymizer


async def anonymize_chunks(chunks: List[Document]) -> List[Document]:
    """
    Anonimiza os blocos de texto usando PresidioAnonymizer, preservando
    o dicionário de reversão nos metadados de cada bloco.
    """
    if not chunks:
        return []

    return PresidioAnonymizer().anonymize_chunks(chunks)
