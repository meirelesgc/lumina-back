from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends

from lumina.core.dependencies import CurrentUser, Session
from lumina.models import User
from lumina.schemas.common import Message
from lumina.schemas.invitation import (
    InvitationAcceptResponse,
    InvitationCreate,
    InvitationFilter,
    InvitationList,
    InvitationPublic,
    InvitationPublicCheck,
    InvitationRegisterAndAccept,
    InvitationRegisterResponse,
)
from lumina.services import invitation_service

router = APIRouter(
    prefix='/invitations',
    tags=['orientação, convites'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=InvitationPublic,
    summary='Criar convite',
    description='Cria um convite pendente associado a um e-mail.',
)
async def create_invitation(
    data: InvitationCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await invitation_service.create_invitation(
        session, current_user, data
    )


@router.get(
    '',
    response_model=InvitationList,
    summary='Listar convites',
    description=(
        'Lista convites emitidos pelo usuário atual ou todos se admin.'
    ),
)
async def list_invitations(
    session: Session,
    current_user: CurrentUser,
    filters: Annotated[InvitationFilter, Depends()],
):
    items = await invitation_service.list_invitations(
        session, current_user, filters
    )
    return {'invitations': items}


@router.get(
    '/pending-for-me',
    response_model=InvitationList,
    summary='Listar convites pendentes recebidos',
    description=(
        'Lista todos os convites pendentes e válidos direcionados ao e-mail'
        ' do usuário atual.'
    ),
)
async def list_pending_for_me(
    session: Session,
    current_user: CurrentUser,
):
    items = await invitation_service.list_pending_for_user(
        session, current_user
    )
    return {'invitations': items}


@router.get(
    '/{token}',
    response_model=InvitationPublicCheck,
    summary='Consultar convite por token',
    description=(
        'Consulta pública dos dados do convite para a página de aceite.'
    ),
)
async def check_invitation(
    token: str,
    session: Session,
):
    return await invitation_service.check_invitation_by_token(session, token)


@router.post(
    '/{token}/accept',
    response_model=InvitationAcceptResponse,
    summary='Aceitar convite com usuário autenticado',
    description='Aceita o convite e cria o vínculo de orientação acadêmica.',
)
async def accept_invitation(
    token: str,
    session: Session,
    current_user: CurrentUser,
):
    return await invitation_service.accept_invitation(
        session, current_user, token
    )


@router.post(
    '/{token}/register',
    status_code=HTTPStatus.CREATED,
    response_model=InvitationRegisterResponse,
    summary='Cadastrar e aceitar convite (passo único)',
    description=(
        'Cria a conta com o e-mail do convite e aceita o vínculo diretamente.'
    ),
)
async def register_and_accept(
    token: str,
    data: InvitationRegisterAndAccept,
    session: Session,
):
    return await invitation_service.register_and_accept_invitation(
        session, token, data
    )


@router.post(
    '/{token}/reject',
    response_model=Message,
    summary='Recusar convite',
    description='Marca o convite como recusado.',
)
async def reject_invitation(
    token: str,
    session: Session,
    current_user: Optional[User] = None,
):
    res = await invitation_service.reject_invitation(
        session, token, current_user
    )
    return Message(message=res['message'])


@router.delete(
    '/{invitation_id}',
    response_model=Message,
    summary='Cancelar convite',
    description='Cancela o convite pendente.',
)
async def cancel_invitation(
    invitation_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await invitation_service.cancel_invitation(
        session, current_user, invitation_id
    )
    return Message(message='Convite cancelado com sucesso.')
