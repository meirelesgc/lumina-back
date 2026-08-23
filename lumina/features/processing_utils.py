# Utilitários genéricos de processamento assíncrono em background, compartilhados pelas conformidades de template e de ABNT (armazenamento do artigo enviado e atualização do envelope de status em lumina.features.json_store.JsonResultStore).

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from lumina.features.json_store import JsonResultStore

DEFAULT_ARTICLE_FILENAME = 'artigo.pdf'


def safe_stem(doc_id: str) -> str:
    return ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in doc_id)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_upload(directory: Path, doc_id: str, filename: str, content: bytes) -> Path:
    suffix = Path(filename).suffix or '.pdf'
    path = directory / f'{safe_stem(doc_id)}{suffix}'
    path.write_bytes(content)
    return path


def mark_processing(store: JsonResultStore, doc_id: str) -> None:
    store.save(
        doc_id,
        {
            'doc_id': doc_id,
            'status': 'processing',
            'updated_at': now_iso(),
            'report': None,
            'error': None,
        },
    )


def mark_completed(store: JsonResultStore, doc_id: str, report: dict) -> None:
    store.save(
        doc_id,
        {
            'doc_id': doc_id,
            'status': 'completed',
            'updated_at': now_iso(),
            'report': report,
            'error': None,
        },
    )


def mark_error(store: JsonResultStore, doc_id: str, error: str) -> None:
    store.save(
        doc_id,
        {
            'doc_id': doc_id,
            'status': 'error',
            'updated_at': now_iso(),
            'report': None,
            'error': error,
        },
    )
