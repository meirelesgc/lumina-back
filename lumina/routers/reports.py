from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from lumina.core.dependencies import CurrentUser, Session
from lumina.core.security import get_current_user
from lumina.services import (
    release_service,
    report_service,
    typification_service,
)

router = APIRouter(
    prefix='/export',
    tags=['document verification'],
    dependencies=[Depends(get_current_user)],
)


@router.get('/release/pdf')
async def export_document_release_pdf(
    session: Session,
    current_user: CurrentUser,
    document_release_id: UUID,
):
    await release_service.ensure_can_read_release(
        session, current_user, document_release_id
    )
    report_path = await report_service.generate_document_release_pdf(
        session=session,
        document_release_id=document_release_id,
    )

    return FileResponse(report_path, filename=report_path.split('/')[-1])


@router.get('/typifications/pdf')
async def export_typifications_pdf(
    session: Session,
    typification_id: UUID | None = None,
):
    return await typification_service.export_pdf(session, typification_id)
