from uuid import UUID

from fastapi import APIRouter

from iaEditais.core.dependencies import Model, Session
from iaEditais.services import assistant_service

router = APIRouter(
    prefix='/doc/{doc_id}/assistant',
    tags=['assistente ia, chat'],
)


@router.post('/chat')
async def chat_with_document(
    doc_id: UUID,
    body: dict,
    session: Session,
    model: Model,
):
    message = body.get('message', '')
    history = body.get('history', [])
    return await assistant_service.chat_with_document(
        doc_id=doc_id,
        message=message,
        history=history,
        model=model,
        session=session,
    )
