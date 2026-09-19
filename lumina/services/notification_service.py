import re
from typing import Any

import httpx
from sqlalchemy import select

from lumina.core.dependencies import Session
from lumina.core.settings import Settings
from lumina.models import DocumentRelease, User

SETTINGS = Settings()
EVOLUTION_HEADERS = {
    'Content-Type': 'application/json',
    'apikey': SETTINGS.EVOLUTION_KEY,
}


def prepare_phone_number(user: User):
    if not user.phone_number:
        return None
    phone_number = user.phone_number.strip().replace(' ', '').replace('-', '')
    if not re.fullmatch(r'55\d{10,11}', phone_number):
        return None
    return phone_number


async def send_message(payload: dict, session: Session) -> None:
    """
    Envia mensagens via WhatsApp (Evolution API) para a lista de user_ids.
    """
    user_ids = payload.get('user_ids', [])
    message_text = payload.get('message_text')

    if not user_ids or not message_text:
        return

    statement = select(User).where(User.id.in_(user_ids))
    query = await session.scalars(statement)
    users_to_notify = query.all()

    if not SETTINGS.EVOLUTION_URL:
        return

    async with httpx.AsyncClient() as client:
        for user in users_to_notify:
            phone_number = prepare_phone_number(user)
            if not phone_number:
                continue

            msg_payload = {'number': phone_number, 'text': message_text}
            try:
                await client.post(
                    SETTINGS.EVOLUTION_URL,
                    headers=EVOLUTION_HEADERS,
                    json=msg_payload,
                )
            except Exception:
                pass


async def publish_password_reset_notification(
    user: User, reset_token: str, session: Session
):
    if not user.phone_number:
        return {'status': 'skipped', 'reason': 'No phone number'}

    message_text = (
        f'Olá, {user.username}. '
        f'Seu código para redefinir a senha é: *{reset_token}*. '
        'Este código expira em 15 minutos. '
        'Se não foi você que solicitou, ignore esta mensagem.'
    )

    payload = {'user_ids': [user.id], 'message_text': message_text}
    await send_message(payload, session)
    return {'status': 'published'}


def format_user_welcome_message(username: str, temp_password: str) -> str:
    return (
        f'🚀 Olá, {username}! Seu cadastro em nosso sistema foi '
        f'concluído com sucesso.\n\n'
        f'Sua senha temporária para acesso é: *{temp_password}*\n\n'
        f'Por favor, acesse a plataforma e altere sua senha imediatamente.\n\n'
        f'Atenciosamente, A Equipe.'
    )


async def publish_user_welcome_notification(
    user: User, temp_password: str, session: Session
):
    if not user.phone_number:
        return {'status': 'skipped', 'reason': 'No phone number'}

    message_text = format_user_welcome_message(user.username, temp_password)
    payload = {'user_ids': [user.id], 'message_text': message_text}
    await send_message(payload, session)
    return {'status': 'published'}


def format_release_message(db_release: DocumentRelease):
    db_history = db_release.history
    db_doc = db_history.document
    return (
        f"Olá! O processo de verificação do documento '{db_doc.name}' "
        f'foi concluído com sucesso.'
    )


async def send_release_completed_notification(
    db_doc: Any, db_release: DocumentRelease, session: Session
) -> None:
    """
    Envia notificação aos editores do documento quando a release é concluída.
    """
    message_text = format_release_message(db_release)
    editors = getattr(db_doc, 'editors', []) or []
    user_ids = {editor.id for editor in editors if getattr(editor, 'id', None)}
    if user_ids:
        payload = {'user_ids': list(user_ids), 'message_text': message_text}
        await send_message(payload, session)


async def publish_test_whatsapp_notification(user: User, session: Session):
    clean_number = prepare_phone_number(user)
    if not clean_number:
        return {
            'status': 'error',
            'detail': 'Invalid phone format. Must be 55 + DDD + Number.',
        }

    message_text = (
        f'🤖 Olá, {user.username}! \n\n'
        f'Este é um teste de verificação do seu número no Lumina. '
        f'Se você recebeu esta mensagem, seu cadastro está correto.'
    )

    payload = {'user_ids': [user.id], 'message_text': message_text}
    await send_message(payload, session)
    return {'status': 'published', 'detail': 'Test message queued'}
