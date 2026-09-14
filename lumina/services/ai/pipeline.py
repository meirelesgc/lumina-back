import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.dependencies import Model, Session, VStore
from lumina.core.settings import Settings
from lumina.models import (
    AppliedBranch,
    AppliedSource,
    AppliedTaxonomy,
    AppliedTypification,
    DocumentRelease,
)
from lumina.repositories import release_repo
from lumina.schemas.common import WSMessage
from lumina.schemas.document import DocumentProcessingStatus
from lumina.schemas.document_release import DocumentReleasePublic
from lumina.services import (
    notification_service,
    tree_service,
)
from lumina.services.ai import stages
from lumina.services.run_logger import get_run_logger

SETTINGS = Settings()


async def ws_update(
    redis: Redis, db_release: DocumentRelease, message: str
) -> None:
    """
    Publica evento de atualização da release no canal Redis ws:broadcast.
    """
    release_public = DocumentReleasePublic.model_validate(db_release)
    payload = release_public.model_dump(mode='json')
    ws_message = WSMessage(
        event='doc.release.update',
        message=message,
        payload=payload,
    )
    await redis.publish('ws:broadcast', ws_message.model_dump_json())


async def save_applied_snapshot(
    session: AsyncSession,
    simplified_args: list[dict],
    release_id: UUID,
    user_id: Optional[UUID] = None,
) -> None:
    """
    Clona e congela a árvore normativa ativa nas entidades Applied*
    associadas ao release_id.
    """
    applied_typs: dict[UUID, AppliedTypification] = {}
    applied_taxes: dict[UUID, AppliedTaxonomy] = {}

    for branch_data in simplified_args:
        branch_id = branch_data.get('id')
        if not branch_id:
            continue

        original_branch = await release_repo.get_full_branch(
            session, branch_id
        )
        if not original_branch:
            continue

        tax = original_branch.taxonomy
        typ = tax.typification

        # Applied Typification
        app_typ = applied_typs.get(typ.id)
        if not app_typ:
            app_typ = await release_repo.get_applied_typification(
                session, typ.id, release_id
            )
            if not app_typ:
                app_typ = AppliedTypification(
                    name=typ.name,
                    applied_release_id=release_id,
                    original_id=typ.id,
                    created_by=user_id,
                )
                for src in typ.sources:
                    app_typ.sources.append(
                        AppliedSource(
                            name=src.name,
                            description=src.description,
                            original_id=src.id,
                            created_by=user_id,
                        )
                    )
                release_repo.add_applied_entity(session, app_typ)
                await session.flush()
            applied_typs[typ.id] = app_typ

        # Applied Taxonomy
        app_tax = applied_taxes.get(tax.id)
        if not app_tax:
            app_tax = await release_repo.get_applied_taxonomy(
                session, tax.id, app_typ.id
            )
            if not app_tax:
                app_tax = AppliedTaxonomy(
                    title=tax.title,
                    description=tax.description,
                    applied_typification_id=app_typ.id,
                    original_id=tax.id,
                    created_by=user_id,
                )
                for src in tax.sources:
                    app_tax.sources.append(
                        AppliedSource(
                            name=src.name,
                            description=src.description,
                            original_id=src.id,
                            created_by=user_id,
                        )
                    )
                release_repo.add_applied_entity(session, app_tax)
                await session.flush()
            applied_taxes[tax.id] = app_tax

        # Applied Branch
        applied_branch = AppliedBranch(
            title=original_branch.title,
            description=original_branch.description,
            applied_taxonomy_id=app_tax.id,
            original_id=original_branch.id,
            created_by=user_id,
            fulfilled=branch_data.get('fulfilled'),
            score=branch_data.get('score'),
            feedback=branch_data.get('feedback'),
            presidio_mapping=str(branch_data.get('presidio_mapping')),
            references=branch_data.get('references', []),
        )
        release_repo.add_applied_entity(session, applied_branch)

    await session.flush()


async def run_document_ingestion(
    file_path: Path | str,
    vstore: VStore,
    model: Model,
    run_id: Optional[UUID] = None,
) -> None:
    """
    Executa a ingestão completa do documento passando pelas etapas de:
    extração -> seções -> anonimização -> indexação vetorial.
    """
    str_path = str(file_path)
    if os.path.exists(str_path):
        full_path = str_path
    else:
        unique_filename = str_path.rsplit('/', maxsplit=1)[-1]
        full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
        if not os.path.exists(full_path):
            return

    ext = os.path.splitext(full_path)[1].lower()
    if ext != '.pdf':
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')

    source_name = f'lumina/storage/uploads/{os.path.basename(full_path)}'

    raw_chunks, _ = await stages.extraction.extract_pdf_with_telemetry(
        full_path, source_name, run_id=run_id
    )
    formatted_docs = await stages.sections.assign_sections_with_telemetry(
        raw_chunks, model, run_id=run_id
    )

    anonymized = await stages.anonymization.anonymize_chunks(
        formatted_docs, run_id=run_id
    )
    await stages.indexing.index_chunks_to_vstore(
        vstore, anonymized, run_id=run_id
    )


async def process_release_pipeline(
    session: AsyncSession,
    release_id: UUID,
    model: Model,
    vstore: VStore,
    redis: Redis,
) -> dict:
    """
    Orquestra todas as etapas do pipeline de avaliação de release:
    ingestão/vetorização -> recuperação ponderada -> avaliação paralela ->
    resolução de citações -> síntese executiva OiacIA.
    """
    db_release = await release_repo.get_release_with_details(
        session, release_id
    )
    if not db_release:
        raise ValueError(f'DocumentRelease {release_id} not found.')

    db_doc = db_release.history.document
    run_logger = get_run_logger()

    # 1. Ingestão e Vetorização
    await ws_update(redis, db_release, 'creating_vectors')
    await run_document_ingestion(
        db_release.file_path, vstore, model, run_id=release_id
    )

    # 2. Avaliação da Árvore Normativa
    await ws_update(redis, db_release, 'evaluating')
    t_eval = datetime.now()
    await run_logger.start_stage(run_id=release_id, stage='evaluation')
    try:
        tree = await tree_service.get_tree_by_release(session, db_release)
        args = await stages.retrieval.get_eval_args(vstore, tree, db_release)
        simplified_args = await stages.retrieval.simplify_eval_args(args)
        chain = stages.evaluation.get_evaluation_chain(model)
        await stages.evaluation.evaluate_criteria_batch(
            chain, simplified_args, run_id=release_id
        )
        await save_applied_snapshot(session, simplified_args, db_release.id)
        d_eval = int((datetime.now() - t_eval).total_seconds() * 1000)
        await run_logger.complete_stage(
            run_id=release_id,
            stage='evaluation',
            duration_ms=d_eval,
            item_count=len(simplified_args),
        )
    except Exception as e:
        d_eval = int((datetime.now() - t_eval).total_seconds() * 1000)
        await run_logger.fail_stage(
            run_id=release_id,
            stage='evaluation',
            error=str(e),
            duration_ms=d_eval,
        )
        raise

    # 3. Macroetapa: Resolução de Coordenadas e Citações
    await stages.citations.record_citations_stage(
        run_logger, release_id, simplified_args
    )

    # 4. Macroetapa: Síntese Executiva OiacIA
    await stages.synthesis.record_synthesis_stage(
        run_logger,
        db_release,
        simplified_args,
        model,
        session,
    )

    await ws_update(redis, db_release, 'complete')

    return {'doc': db_doc, 'release': db_release, 'status': 'success'}


async def run_release_pipeline(
    release_id: UUID,
    session: Session,
    model: Model,
    vstore: VStore,
    redis: Redis,
) -> None:
    """
    Função principal executada em background pelo FastAPI para processar
    uma nova release documental. Substitui o antigo workers/docs/releases.py.
    """
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
        result = await process_release_pipeline(
            session, release_id, model, vstore, redis
        )

        db_doc.processing_status = DocumentProcessingStatus.IDLE
        await session.commit()

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        await run_logger.complete_run(
            run_id=release_id, duration_ms=duration_ms
        )

        # Envia notificação de conclusão aos editores
        await notification_service.send_release_completed_notification(
            db_doc=db_doc,
            db_release=result['release'],
            session=session,
        )

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


# Alias para retrocompatibilidade direta
release_pipeline = run_release_pipeline
