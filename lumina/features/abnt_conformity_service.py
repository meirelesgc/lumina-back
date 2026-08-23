# Orquestração da conformidade ABNT: upload do artigo, disparo em background da auditoria via engenharia de prompt e consulta do resultado, chamado pelos endpoints em lumina/routers/abnt.py.

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from fastapi import BackgroundTasks

from lumina.features.abnt_check import abnt as abnt_check
from lumina.features.json_store import JsonResultStore
from lumina.features.processing_utils import (
    DEFAULT_ARTICLE_FILENAME,
    mark_completed,
    mark_error,
    mark_processing,
    save_upload,
)

logger = logging.getLogger(__name__)

FEATURE_DIR = Path(__file__).resolve().parent

DATA_DIR = FEATURE_DIR.parent / 'storage' / 'abnt_conformity'
UPLOADS_DIR = DATA_DIR / 'uploads'
RESULTS_DIR = DATA_DIR / 'results'

for directory in (UPLOADS_DIR, RESULTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_store() -> JsonResultStore:
    return JsonResultStore(RESULTS_DIR)


def run_analysis(doc_id: str, article_path: Path) -> None:
    store = get_store()
    try:
        report = abnt_check.compare(str(article_path))
        mark_completed(store, doc_id, report.model_dump())
    except Exception as exc:
        logger.exception(
            'Falha na verificação de conformidade ABNT (doc_id=%s)', doc_id
        )
        mark_error(store, doc_id, str(exc))


def start_analysis(
    doc_id: str, filename: str | None, content: bytes, background_tasks: BackgroundTasks,
) -> None:
    store = get_store()
    article_path = save_upload(UPLOADS_DIR, doc_id, filename or DEFAULT_ARTICLE_FILENAME, content)
    mark_processing(store, doc_id)
    background_tasks.add_task(run_analysis, doc_id, article_path)
