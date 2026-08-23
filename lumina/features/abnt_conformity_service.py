# Orquestração da conformidade ABNT: upload do artigo, disparo em background da auditoria via engenharia de prompt e consulta do resultado, chamado pelos endpoints em lumina/routers/abnt.py.

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks

from lumina.features.abnt_check import abnt as abnt_check
from lumina.features.json_store import JsonResultStore
from lumina.features.processing_utils import (
    DEFAULT_ARTICLE_FILENAME,
    mark_completed,
    mark_error,
    mark_processing,
    now_iso,
    save_upload,
)

logger = logging.getLogger(__name__)

FEATURE_DIR = Path(__file__).resolve().parent

DATA_DIR = FEATURE_DIR.parent / 'storage' / 'abnt_conformity'
UPLOADS_DIR = DATA_DIR / 'uploads'
RESULTS_DIR = DATA_DIR / 'results'
RELATIVE_UPLOADS_PREFIX = 'abnt_conformity/uploads'

for directory in (UPLOADS_DIR, RESULTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_store() -> JsonResultStore:
    return JsonResultStore(RESULTS_DIR)


def list_results(doc_id: str) -> list[dict]:
    return get_store().list_by_doc_id(doc_id)


def run_analysis(
    analysis_id: str,
    doc_id: str,
    file_path: str,
    created_at: str,
    article_path: Path,
) -> None:
    store = get_store()
    try:
        report = abnt_check.compare(str(article_path))
        mark_completed(
            store, analysis_id, doc_id, file_path, created_at, report.model_dump()
        )
    except Exception as exc:
        logger.exception(
            'Falha na verificação de conformidade ABNT (doc_id=%s)', doc_id
        )
        mark_error(store, analysis_id, doc_id, file_path, created_at, str(exc))


def start_analysis(
    doc_id: str, filename: str | None, content: bytes, background_tasks: BackgroundTasks,
) -> dict:
    store = get_store()
    analysis_id = str(uuid4())
    created_at = now_iso()
    article_path, unique_filename = save_upload(
        UPLOADS_DIR, filename or DEFAULT_ARTICLE_FILENAME, content
    )
    file_path = f'{RELATIVE_UPLOADS_PREFIX}/{unique_filename}'
    payload = mark_processing(store, analysis_id, doc_id, file_path, created_at)
    background_tasks.add_task(
        run_analysis, analysis_id, doc_id, file_path, created_at, article_path
    )
    return payload
