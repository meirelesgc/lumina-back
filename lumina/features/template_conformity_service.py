# Orquestração da conformidade com template: upload do artigo, disparo em background da verificação híbrida (visual + determinística) e consulta do resultado, chamado pelos endpoints em lumina/routers/templates.py.

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from fastapi import BackgroundTasks

from lumina.features.json_store import JsonResultStore
from lumina.features.processing_utils import (
    DEFAULT_ARTICLE_FILENAME,
    mark_completed,
    mark_error,
    mark_processing,
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

for directory in (UPLOADS_DIR, RESULTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_store() -> JsonResultStore:
    return JsonResultStore(RESULTS_DIR)


async def run_analysis(doc_id: str, template_path: Path, article_path: Path) -> None:
    store = get_store()
    try:
        report = await template_check.compare(str(template_path), str(article_path))
        mark_completed(store, doc_id, report.model_dump())
    except Exception as exc:
        logger.exception(
            'Falha na verificação de conformidade com template (doc_id=%s)',
            doc_id,
        )
        mark_error(store, doc_id, str(exc))


def start_analysis(
    doc_id: str, filename: str | None, content: bytes,
    template_path: Path, background_tasks: BackgroundTasks,
) -> None:
    store = get_store()
    article_path = save_upload(UPLOADS_DIR, doc_id, filename or DEFAULT_ARTICLE_FILENAME, content)
    mark_processing(store, doc_id)
    background_tasks.add_task(run_analysis, doc_id, template_path, article_path)
