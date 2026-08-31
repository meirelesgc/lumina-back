# Orquestração da conformidade com template: upload do artigo, disparo em background da verificação híbrida (visual + determinística) e consulta do resultado, chamado pelos endpoints em lumina/routers/templates.py.

from __future__ import annotations

import logging
from http import HTTPStatus
from pathlib import Path
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.database import async_session
from lumina.core.settings import Settings
from lumina.features.processing_utils import (
    DEFAULT_ARTICLE_FILENAME,
    save_upload,
)
from lumina.features.schemas import (
    ConformityFilter,
    ProcessingResult,
)
from lumina.features.template_check import (
    template as template_check,
)
from lumina.models import TemplateConformityResult
from lumina.repositories import template_conformity_repo
from lumina.services import audit_service

logger = logging.getLogger(__name__)

SETTINGS = Settings()
DATA_DIR = Path(SETTINGS.STORAGE_DIRECTORY) / 'template_conformity'
UPLOADS_DIR = DATA_DIR / 'uploads'
RELATIVE_UPLOADS_PREFIX = 'template_conformity/uploads'

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

RESULT_NOT_FOUND_DETAIL = 'Resultado de conformidade não encontrado.'


async def list_results(
    session: AsyncSession, filters: ConformityFilter
) -> list[TemplateConformityResult]:
    return await template_conformity_repo.list_all(session, filters)


async def count_results(
    session: AsyncSession, filters: ConformityFilter
) -> int:
    return await template_conformity_repo.count(session, filters)


async def get_result_by_id(
    session: AsyncSession, result_id: UUID
) -> TemplateConformityResult:
    record = await template_conformity_repo.get_by_id(session, result_id)
    if not record or record.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=RESULT_NOT_FOUND_DETAIL,
        )
    return record


async def delete_result(
    session: AsyncSession, user_id: UUID, result_id: UUID
) -> None:
    record = await get_result_by_id(session, result_id)

    old_data = ProcessingResult.model_validate(record).model_dump(mode='json')
    record.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=TemplateConformityResult.__tablename__,
        record_id=record.id,
        old_data=old_data,
    )

    await session.commit()


async def _execute_analysis(
    session: AsyncSession,
    analysis_id: UUID,
    template_path: Path,
    article_path: Path,
) -> None:
    record = await template_conformity_repo.get_by_id(session, analysis_id)
    if not record:
        return

    try:
        report = await template_check.compare(
            str(template_path), str(article_path)
        )
        record.status = 'completed'
        record.report = report.model_dump()
        record.error = None
    except Exception as exc:
        logger.exception(
            'Falha na verificação de conformidade com template (analysis_id=%s, doc_id=%s)',
            analysis_id,
            record.doc_id,
        )
        record.status = 'error'
        record.error = str(exc)

    record.updated_at = func.now()
    await session.commit()


async def run_analysis(
    analysis_id: UUID,
    template_path: Path,
    article_path: Path,
    session: AsyncSession | None = None,
) -> None:
    if session is not None:
        await _execute_analysis(
            session, analysis_id, template_path, article_path
        )
    else:
        async with async_session() as bg_session:
            await _execute_analysis(
                bg_session, analysis_id, template_path, article_path
            )


async def start_analysis(
    session: AsyncSession,
    user_id: UUID,
    doc_id: str,
    filename: str | None,
    content: bytes,
    template_path: Path,
    background_tasks: BackgroundTasks,
) -> TemplateConformityResult:
    article_path, unique_filename = save_upload(
        UPLOADS_DIR, filename or DEFAULT_ARTICLE_FILENAME, content
    )
    file_path = f'{RELATIVE_UPLOADS_PREFIX}/{unique_filename}'

    record = TemplateConformityResult(
        doc_id=doc_id,
        file_path=file_path,
        status='processing',
    )
    record.set_creation_audit(user_id)

    template_conformity_repo.add(session, record)
    await session.flush()

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=TemplateConformityResult.__tablename__,
        record_id=record.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(record)

    background_tasks.add_task(
        run_analysis,
        record.id,
        template_path,
        article_path,
        session=session,
    )
    return record
