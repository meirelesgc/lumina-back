# Utilitários genéricos de processamento assíncrono em background, compartilhados pelas conformidades de template e de ABNT (armazenamento do artigo enviado e atualização do envelope de status em lumina.features.json_store.JsonResultStore).

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from lumina.features.json_store import JsonResultStore

DEFAULT_ARTICLE_FILENAME = 'artigo.pdf'


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_upload(directory: Path, filename: str, content: bytes) -> tuple[Path, str]:
    suffix_name = Path(filename).name or DEFAULT_ARTICLE_FILENAME
    unique_filename = f'{uuid4()}_{suffix_name}'
    path = directory / unique_filename
    path.write_bytes(content)
    return path, unique_filename


def mark_processing(
    store: JsonResultStore,
    analysis_id: str,
    doc_id: str,
    file_path: str,
    created_at: str,
) -> dict:
    payload = {
        'id': analysis_id,
        'doc_id': doc_id,
        'status': 'processing',
        'file_path': file_path,
        'created_at': created_at,
        'updated_at': created_at,
        'report': None,
        'error': None,
    }
    store.save(analysis_id, payload)
    return payload


def mark_completed(
    store: JsonResultStore,
    analysis_id: str,
    doc_id: str,
    file_path: str,
    created_at: str,
    report: dict,
) -> None:
    store.save(
        analysis_id,
        {
            'id': analysis_id,
            'doc_id': doc_id,
            'status': 'completed',
            'file_path': file_path,
            'created_at': created_at,
            'updated_at': now_iso(),
            'report': report,
            'error': None,
        },
    )


def mark_error(
    store: JsonResultStore,
    analysis_id: str,
    doc_id: str,
    file_path: str,
    created_at: str,
    error: str,
) -> None:
    store.save(
        analysis_id,
        {
            'id': analysis_id,
            'doc_id': doc_id,
            'status': 'error',
            'file_path': file_path,
            'created_at': created_at,
            'updated_at': now_iso(),
            'report': None,
            'error': error,
        },
    )
