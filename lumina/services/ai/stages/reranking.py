from typing import List, Optional

from langchain_core.documents import Document


def rerank_chunks(
    query: str,
    chunks: List[Document],
    top_n: int,
) -> Optional[List[Document]]:
    """
    Ponto de extensão para reranking de candidatos com cross-encoder
    (Fase 5 do plano de recuperação de chunks).

    Objetivo futuro: reordenar `chunks` (um conjunto ampliado de
    candidatos, tipicamente 20-30) por um modelo de reranking dedicado
    (cross-encoder local ou API gerenciada), retornando os `top_n`
    melhores na nova ordem.

    Decisão de arquitetura (qual cross-encoder/API usar) em aberto — ver
    issue de rastreamento marcada como discussão.

    Estado atual: sem efeito. Retorna None. O chamador mantém a lista
    fundida por RRF sem reordenação enquanto a flag
    `CROSS_ENCODER_RERANKING_ENABLED` estiver desligada (padrão) ou
    enquanto esta função não for implementada.
    """
    # TODO: implementação futura — ver issue #13 (discussion)
    return None
