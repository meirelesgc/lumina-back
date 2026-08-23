# Orquestração da conformidade com template: upload do artigo, disparo em background da verificação híbrida (visual + determinística) e consulta do resultado, chamado pelos endpoints em lumina/routers/templates.py.

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks

from lumina.features.json_store import JsonResultStore
from lumina.features.processing_utils import (
    DEFAULT_ARTICLE_FILENAME,
    mark_completed,
    mark_error,
    mark_processing,
    now_iso,
    save_upload,
)
from lumina.features.template_check import (
    template as template_check,
)

logger = logging.getLogger(__name__)

FEATURE_DIR = Path(__file__).resolve().parent

DATA_DIR = FEATURE_DIR.parent / 'storage' / 'template_conformity'
UPLOADS_DIR = DATA_DIR / 'uploads'
RESULTS_DIR = DATA_DIR / 'results'
RELATIVE_UPLOADS_PREFIX = 'template_conformity/uploads'

for directory in (UPLOADS_DIR, RESULTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_store() -> JsonResultStore:
    return JsonResultStore(RESULTS_DIR)


def list_results(doc_id: str) -> list[dict]:
    return get_store().list_by_doc_id(doc_id)


async def run_analysis(
    analysis_id: str,
    doc_id: str,
    file_path: str,
    created_at: str,
    template_path: Path,
    article_path: Path,
) -> None:
    store = get_store()
    try:
        report = await template_check.compare(str(template_path), str(article_path))
        mark_completed(
            store, analysis_id, doc_id, file_path, created_at, report.model_dump()
        )
    except Exception as exc:
        logger.exception(
            'Falha na verificação de conformidade com template (doc_id=%s)',
            doc_id,
        )
        mark_error(store, analysis_id, doc_id, file_path, created_at, str(exc))


def start_analysis(
    doc_id: str, filename: str | None, content: bytes,
    template_path: Path, background_tasks: BackgroundTasks,
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
        run_analysis,
        analysis_id,
        doc_id,
        file_path,
        created_at,
        template_path,
        article_path,
    )
    return payload
