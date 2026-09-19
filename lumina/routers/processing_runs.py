from http import HTTPStatus
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from lumina.core.dependencies import AdminUser
from lumina.schemas.processing_run import (
    ProcessingEvent,
    ProcessingRunDetail,
    ProcessingRunListResponse,
    ProcessingStatus,
)
from lumina.services.run_logger import get_run_logger

router = APIRouter(
    prefix='/processing-runs',
    tags=['Processing Runs'],
)


@router.get('', response_model=ProcessingRunListResponse)
async def list_processing_runs(
    _admin: AdminUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[ProcessingStatus] = Query(default=None),
    release_id: Optional[UUID] = Query(default=None),
    document_id: Optional[UUID] = Query(default=None),
) -> ProcessingRunListResponse:
    logger = get_run_logger()
    return await logger.list_runs(
        limit=limit,
        offset=offset,
        status=status,
        release_id=release_id,
        document_id=document_id,
    )


@router.get('/{run_id}', response_model=ProcessingRunDetail)
async def get_processing_run(
    run_id: UUID,
    _admin: AdminUser,
) -> ProcessingRunDetail:
    logger = get_run_logger()
    detail = await logger.get_run_detail(run_id)
    if not detail:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f'ProcessingRun {run_id} not found.',
        )
    return detail


@router.get('/{run_id}/events', response_model=List[ProcessingEvent])
async def get_processing_run_events(
    run_id: UUID,
    _admin: AdminUser,
) -> List[ProcessingEvent]:
    logger = get_run_logger()
    events = await logger.get_run_events(run_id)
    if not events:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f'ProcessingRun {run_id} not found or has no events.',
        )
    return events
