import secrets
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Optional, Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.settings import SETTINGS
from lumina.models import AccessType, Advisorship, Invitation, User
from lumina.repositories import (
    advisorship_repo,
    invitation_repo,
    project_repo,
    user_repo,
)
from lumina.schemas.advisorship import AdvisorshipPublic
from lumina.schemas.invitation import (
    InvitationAcceptResponse,
    InvitationCreate,
    InvitationFilter,
    InvitationPublic,
    InvitationPublicCheck,
    InvitationRegisterAndAccept,
)
from lumina.schemas.user import UserCreate, UserPublic
from lumina.services import audit_service, auth_service, user_service


def is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        return expires_at < datetime.now(timezone.utc).replace(tzinfo=None)
    return expires_at < datetime.now(timezone.utc)


async def create_invitation(
    session: AsyncSession, current_user: User, data: InvitationCreate
) -> Invitation:
    clean_email = data.email.strip().lower()

    if current_user.email and current_user.email.lower() == clean_email:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Você não pode convidar seu próprio e-mail.',
        )

    if data.project_id:
        project = await project_repo.get_by_id(session, data.project_id)
        if not project or project.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Projeto não encontrado.',
            )

    target_user = await user_repo.get_by_email(session, clean_email)
    if target_user and not target_user.deleted_at:
        active_advisorship = await advisorship_repo.get_active_pair(
            session=session,
            advisor_id=current_user.id,
            advisee_id=target_user.id,
            project_id=data.project_id,
            role_type=data.role_type.value,
        )
        if active_advisorship:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=(
                    'Já existe um vínculo ativo de orientação com este'
                    ' usuário.'
                ),
            )

    existing_invite = await invitation_repo.get_pending_by_email_and_inviter(
        session=session,
        email=clean_email,
        inviter_id=current_user.id,
        project_id=data.project_id,
    )
    if existing_invite:
        if not is_expired(existing_invite.expires_at):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe um convite pendente para este e-mail.',
            )
        existing_invite.status = 'CANCELLED'

    days = SETTINGS.INVITATION_EXPIRE_DAYS
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    token = secrets.token_urlsafe(32)

    invitation = Invitation(
        email=clean_email,
        inviter_id=current_user.id,
        token=token,
        project_id=data.project_id,
        role_type=data.role_type.value,
        topic=data.topic,
        status='PENDING',
        expires_at=expires_at,
    )
    invitation.set_creation_audit(current_user.id)
    invitation_repo.add_invitation(session, invitation)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='CREATE',
        table_name=Invitation.__tablename__,
        record_id=invitation.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(invitation)
    return invitation


async def check_invitation_by_token(
    session: AsyncSession, token: str
) -> InvitationPublicCheck:
    invitation = await invitation_repo.get_by_token(session, token)
    if not invitation or invitation.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Convite não encontrado.',
        )

    expired = is_expired(invitation.expires_at)
    is_valid = invitation.status == 'PENDING' and not expired

    user = await user_repo.get_by_email(session, invitation.email)
    user_exists = user is not None and user.deleted_at is None

    inviter_name = (
        invitation.inviter.username if invitation.inviter else 'Desconhecido'
    )
    inviter_email = invitation.inviter.email if invitation.inviter else ''
    project_title = invitation.project.title if invitation.project else None

    return InvitationPublicCheck(
        token=invitation.token,
        email=invitation.email,
        status=invitation.status,
        is_valid=is_valid,
        is_expired=expired,
        user_exists=user_exists,
        inviter_name=inviter_name,
        inviter_email=inviter_email,
        project_title=project_title,
        topic=invitation.topic,
        role_type=invitation.role_type,
        expires_at=invitation.expires_at,
    )


async def accept_invitation(
    session: AsyncSession, current_user: User, token: str
) -> InvitationAcceptResponse:
    invitation = await invitation_repo.get_by_token(session, token)
    if not invitation or invitation.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Convite não encontrado.',
        )

    if invitation.status != 'PENDING':
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=(
                f'O convite não está pendente (status: {invitation.status}).'
            ),
        )

    if is_expired(invitation.expires_at):
        raise HTTPException(
            status_code=HTTPStatus.GONE,
            detail='Este convite expirou.',
        )

    if current_user.email.lower() != invitation.email.lower():
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Este convite foi emitido para outro e-mail.',
        )

    advisorship = await advisorship_repo.get_active_pair(
        session=session,
        advisor_id=invitation.inviter_id,
        advisee_id=current_user.id,
        project_id=invitation.project_id,
        role_type=invitation.role_type,
    )

    if not advisorship:
        advisorship = Advisorship(
            advisor_id=invitation.inviter_id,
            advisee_id=current_user.id,
            project_id=invitation.project_id,
            role_type=invitation.role_type,
            topic=invitation.topic,
            status='ACTIVE',
        )
        advisorship.set_creation_audit(current_user.id)
        advisorship_repo.add_advisorship(session, advisorship)
        await audit_service.register_action(
            session=session,
            user_id=current_user.id,
            action='CREATE',
            table_name=Advisorship.__tablename__,
            record_id=advisorship.id,
            old_data=None,
        )

    old_status = invitation.status
    invitation.status = 'ACCEPTED'
    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.set_update_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Invitation.__tablename__,
        record_id=invitation.id,
        old_data={'status': old_status},
        new_data={'status': 'ACCEPTED'},
    )

    await session.commit()
    await session.refresh(invitation)
    if advisorship:
        await session.refresh(advisorship)

    return InvitationAcceptResponse(
        message='Convite aceito com sucesso.',
        invitation=InvitationPublic.model_validate(invitation),
        advisorship=(
            AdvisorshipPublic.model_validate(advisorship)
            if advisorship
            else None
        ),
    )


async def register_and_accept_invitation(
    session: AsyncSession, token: str, data: InvitationRegisterAndAccept
) -> dict:
    invitation = await invitation_repo.get_by_token(session, token)
    if not invitation or invitation.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Convite não encontrado.',
        )

    if invitation.status != 'PENDING':
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=(
                f'O convite não está pendente (status: {invitation.status}).'
            ),
        )

    if is_expired(invitation.expires_at):
        raise HTTPException(
            status_code=HTTPStatus.GONE,
            detail='Este convite expirou.',
        )

    existing_user = await user_repo.get_by_email(session, invitation.email)
    if existing_user and not existing_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=(
                'Usuário já cadastrado com este e-mail. Faça login'
                ' para aceitar.'
            ),
        )

    new_user = await user_service.create_user(
        session=session,
        data=UserCreate(
            username=data.username,
            email=invitation.email,
            phone_number=data.phone_number,
            password=data.password,
            access_level=AccessType.DEFAULT,
        ),
    )

    advisorship = Advisorship(
        advisor_id=invitation.inviter_id,
        advisee_id=new_user.id,
        project_id=invitation.project_id,
        role_type=invitation.role_type,
        topic=invitation.topic,
        status='ACTIVE',
    )
    advisorship.set_creation_audit(new_user.id)
    advisorship_repo.add_advisorship(session, advisorship)

    old_status = invitation.status
    invitation.status = 'ACCEPTED'
    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.set_update_audit(new_user.id)

    await audit_service.register_action(
        session=session,
        user_id=new_user.id,
        action='UPDATE',
        table_name=Invitation.__tablename__,
        record_id=invitation.id,
        old_data={'status': old_status},
        new_data={'status': 'ACCEPTED'},
    )

    await session.commit()
    await session.refresh(invitation)
    await session.refresh(advisorship)

    auth_data = await auth_service.login(session, new_user)

    return {
        'message': 'Conta criada e convite aceito com sucesso.',
        'user': UserPublic.model_validate(new_user),
        'token': auth_data,
        'invitation': InvitationPublic.model_validate(invitation),
        'advisorship': AdvisorshipPublic.model_validate(advisorship),
    }


async def reject_invitation(
    session: AsyncSession, token: str, current_user: Optional[User] = None
) -> dict:
    invitation = await invitation_repo.get_by_token(session, token)
    if not invitation or invitation.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Convite não encontrado.',
        )

    if invitation.status != 'PENDING':
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=(
                f'O convite não está pendente (status: {invitation.status}).'
            ),
        )

    old_status = invitation.status
    invitation.status = 'REJECTED'
    invitation.rejected_at = datetime.now(timezone.utc)
    if current_user:
        invitation.set_update_audit(current_user.id)
        await audit_service.register_action(
            session=session,
            user_id=current_user.id,
            action='UPDATE',
            table_name=Invitation.__tablename__,
            record_id=invitation.id,
            old_data={'status': old_status},
            new_data={'status': 'REJECTED'},
        )

    await session.commit()
    return {'message': 'Convite recusado com sucesso.'}


async def cancel_invitation(
    session: AsyncSession, current_user: User, invitation_id: UUID
) -> None:
    invitation = await invitation_repo.get_by_id(session, invitation_id)
    if not invitation or invitation.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Convite não encontrado.',
        )

    is_admin = current_user.access_level == AccessType.ADMIN
    is_inviter = invitation.inviter_id == current_user.id

    if not is_admin and not is_inviter:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Apenas quem enviou o convite ou admin pode cancelá-lo.',
        )

    invitation.status = 'CANCELLED'
    invitation.set_deletion_audit(current_user.id)

    await session.commit()


async def list_invitations(
    session: AsyncSession, current_user: User, filters: InvitationFilter
) -> Sequence[Invitation]:
    is_admin = current_user.access_level == AccessType.ADMIN
    if not is_admin:
        filters.inviter_id = current_user.id

    return await invitation_repo.list_all(session, filters)
