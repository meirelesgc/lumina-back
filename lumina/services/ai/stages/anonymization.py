import re
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from langchain_core.documents import Document

from lumina.services.run_logger import get_run_logger
from lumina.utils.PresidioAnonymizer import PresidioAnonymizer


def extract_entities_count(replacement_keys: List[str]) -> Dict[str, int]:
    """
    Agrupa e contabiliza o total de entidades mascaradas por categoria.
    """
    entities_count: Dict[str, int] = {}
    for k in replacement_keys:
        match = re.match(r'<([A-Za-z0-9_]+)_\d+>', k)
        if not match:
            continue
        ent = match.group(1)
        if 'PHONE' in ent:
            ent_key = 'PHONE'
        elif 'EMAIL' in ent:
            ent_key = 'EMAIL'
        else:
            ent_key = ent
        entities_count[ent_key] = entities_count.get(ent_key, 0) + 1
    return entities_count


async def anonymize_chunks(
    chunks: List[Document], run_id: Optional[UUID] = None
) -> List[Document]:
    """
    Anonimiza os blocos de texto usando PresidioAnonymizer, preservando
    o dicionário de reversão nos metadados de cada bloco e registrando
    a telemetria no RunLogger.
    """
    if not chunks:
        return []

    run_logger = get_run_logger()
    t_start = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='anonymization')

    try:
        anonymizer = PresidioAnonymizer()
        anonymized = anonymizer.anonymize_chunks(chunks)
        keys = list(anonymizer.existing_presidio_mapping.keys())
        counts = extract_entities_count(keys)
        if run_id:
            d_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.complete_stage(
                run_id=run_id,
                stage='anonymization',
                duration_ms=d_ms,
                item_count=len(keys),
                data={
                    'entities_detected_count': counts,
                    'replacement_keys': keys,
                },
            )
        return anonymized
    except Exception as e:
        if run_id:
            d_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.fail_stage(
                run_id=run_id,
                stage='anonymization',
                error=str(e),
                duration_ms=d_ms,
            )
        raise
