from datetime import datetime
from uuid import UUID

from fastapi import Depends
from redis import Redis

from lumina.core.cache import get_redis
from lumina.core.dependencies import Model, Session, VStore
from lumina.core.settings import Settings
from lumina.repositories import release_repo
from lumina.schemas import DocumentProcessingStatus
from lumina.services import (
    notification_service,
    release_orchestrator,
)
from lumina.services.run_logger import get_run_logger
from lumina.workers.utils import send_message

SETTINGS = Settings()


async def release_pipeline(
    release_id: UUID,
    session: Session,
    model: Model,
    vstore: VStore,
    redis: Redis = Depends(get_redis),
):
    db_release = await release_repo.get_release_with_details(
        session, release_id
    )
    if not db_release:
        raise Exception(f'DocumentRelease {release_id} not found.')

    db_doc = db_release.history.document

    db_doc.processing_status = DocumentProcessingStatus.PROCESSING
    await session.commit()

    run_logger = get_run_logger()
    doc_name = (
        str(db_release.file_path).split('/')[-1]
        if db_release.file_path
        else getattr(db_doc, 'title', None)
    )
    start_time = datetime.now()
    await run_logger.start_run(
        run_id=release_id,
        document_id=db_doc.id,
        document_name=doc_name,
        metadata={'version': getattr(db_release, 'version', '1.0.0')},
    )

    try:
        result = await release_orchestrator.process_release_pipeline(
            session, release_id, model, vstore, redis
        )

        db_doc.processing_status = DocumentProcessingStatus.IDLE
        await session.commit()

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        await run_logger.complete_run(
            run_id=release_id, duration_ms=duration_ms
        )

        message_text = notification_service.format_release_message(
            result['release']
        )
        user_ids = {editor.id for editor in db_doc.editors if editor.id}
        payload = {'user_ids': list(user_ids), 'message_text': message_text}
        await send_message(payload, session)

    except Exception as e:
        await session.rollback()
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        await run_logger.fail_run(
            run_id=release_id, error=str(e), duration_ms=duration_ms
        )
        db_doc.processing_status = DocumentProcessingStatus.FAILED
        release_repo.add_document(session, db_doc)
        await session.commit()
        raise e
