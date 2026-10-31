from fastapi import APIRouter
from fastapi.responses import FileResponse

from lumina.core.dependencies import CurrentUser, Session
from lumina.services import upload_service

router = APIRouter(prefix='/uploads', tags=['arquivos enviados'])


@router.get('/{file_path:path}')
async def read_upload(
    file_path: str, session: Session, current_user: CurrentUser
):
    path = await upload_service.get_authorized_path(
        session, current_user, file_path
    )
    return FileResponse(path)
