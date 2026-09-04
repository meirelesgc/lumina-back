from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.dependencies import Model, VStore
from lumina.models import (
    AppliedBranch,
    AppliedSource,
    AppliedTaxonomy,
    AppliedTypification,
    DocumentRelease,
)
from lumina.repositories import release_repo
from lumina.schemas.common import WSMessage
from lumina.schemas.document_release import DocumentReleasePublic
from lumina.services import (
    release_logic_service,
    tree_service,
    vector_service,
)
from lumina.services.run_logger import get_run_logger


# --- WebSocket Helper ---
async def _ws_update(redis: Redis, db_release: DocumentRelease, message: str):
    release_public = DocumentReleasePublic.model_validate(db_release)
    payload = release_public.model_dump(mode='json')
    ws_message = WSMessage(
        event='doc.release.update',
        message=message,
        payload=payload,
    )
    await redis.publish('ws:broadcast', ws_message.model_dump_json())


async def _save_eval_results(
    session: AsyncSession,
    eval_args: list[dict],
    release_id: UUID,
    user_id: Optional[UUID] = None,
):
    applied_typs: dict[UUID, AppliedTypification] = {}
    applied_taxes: dict[UUID, AppliedTaxonomy] = {}

    for branch_data in eval_args:
        branch_id = branch_data.get('id')
        if not branch_id:
            continue

        original_branch = await release_repo.get_full_branch(
            session, branch_id
        )
        if not original_branch:
            continue

        # Hierarquia
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


async def _record_citations_stage(
    run_logger: Any,
    release_id: UUID,
    simplified_args: list[dict],
) -> None:
    t_cit = datetime.now()
    await run_logger.start_stage(run_id=release_id, stage='citations')
    try:
        all_cited: list[str] = []
        total_hallucinated = 0
        total_boxes = 0
        for item in simplified_args:
            for cid in item.get('citations_provided', []):
                all_cited.append(cid)
            total_hallucinated += len(item.get('citations_hallucinated', []))
            for ref in item.get('references', []):
                total_boxes += len(ref.get('rects', []))

        cit_data = {
            'chunks_cited': sorted(list(set(all_cited))),
            'hallucinated_citations_count': total_hallucinated,
            'resolved_boxes_count': total_boxes,
        }
        d_cit = int((datetime.now() - t_cit).total_seconds() * 1000)
        await run_logger.complete_stage(
            run_id=release_id,
            stage='citations',
            duration_ms=d_cit,
            item_count=len(all_cited),
            data=cit_data,
        )
    except Exception as e:
        d_cit = int((datetime.now() - t_cit).total_seconds() * 1000)
        await run_logger.fail_stage(
            run_id=release_id,
            stage='citations',
            error=str(e),
            duration_ms=d_cit,
        )
        raise


async def _record_synthesis_stage(
    run_logger: Any,
    db_release: DocumentRelease,
    simplified_args: list[dict],
    model: Model,
    session: AsyncSession,
) -> None:
    t_synth = datetime.now()
    release_id = db_release.id
    await run_logger.start_stage(run_id=release_id, stage='synthesis')
    try:
        sorted_data = sorted(
            simplified_args,
            key=lambda x: x.get('score') or 0,
            reverse=True,
        )
        highest_ids = [str(x.get('id') or '') for x in sorted_data[:2]]
        lowest_ids = [str(x.get('id') or '') for x in sorted_data[-2:]]

        prompt = release_logic_service.generate_description_prompt(
            simplified_args
        )
        desc_response = model.invoke(prompt)
        desc_text = desc_response.content.strip()
        db_release.description = desc_text
        await session.commit()

        partitioned = release_logic_service.partition_synthesis_text(desc_text)
        synth_data = {
            'top_branches': {
                'highest_score_branch_ids': highest_ids,
                'lowest_score_branch_ids': lowest_ids,
            },
            'partitioned_text': partitioned,
        }
        d_synth = int((datetime.now() - t_synth).total_seconds() * 1000)
        await run_logger.complete_stage(
            run_id=release_id,
            stage='synthesis',
            duration_ms=d_synth,
            data=synth_data,
        )
    except Exception as e:
        d_synth = int((datetime.now() - t_synth).total_seconds() * 1000)
        await run_logger.fail_stage(
            run_id=release_id,
            stage='synthesis',
            error=str(e),
            duration_ms=d_synth,
        )
        raise


async def process_release_pipeline(
    session: AsyncSession,
    release_id: UUID,
    model: Model,
    vstore: VStore,
    redis: Redis,
) -> dict:
    db_release = await release_repo.get_release_with_details(
        session, release_id
    )
    if not db_release:
        raise ValueError(f'DocumentRelease {release_id} not found.')

    db_doc = db_release.history.document

    run_logger = get_run_logger()

    try:
        await _ws_update(redis, db_release, 'creating_vectors')
        await vector_service.create_vectors(
            db_release.file_path, vstore, model, run_id=release_id
        )

        await _ws_update(redis, db_release, 'evaluating')
        t_eval = datetime.now()
        await run_logger.start_stage(run_id=release_id, stage='evaluation')
        try:
            tree = await tree_service.get_tree_by_release(session, db_release)
            args = await release_logic_service.get_eval_args(
                vstore, tree, db_release
            )
            simplified_args = await release_logic_service.simplify_eval_args(
                args
            )
            chain = release_logic_service.get_chain(model)
            await release_logic_service.apply_tree(
                chain, simplified_args, run_id=release_id
            )
            await _save_eval_results(session, simplified_args, db_release.id)
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

        # Macroetapa: Resolução de Coordenadas e Citações
        await _record_citations_stage(run_logger, release_id, simplified_args)

        # Macroetapa: Síntese Executiva OiacIA
        await _record_synthesis_stage(
            run_logger,
            db_release,
            simplified_args,
            model,
            session,
        )

        await _ws_update(redis, db_release, 'complete')

        return {'doc': db_doc, 'release': db_release, 'status': 'success'}

    except Exception as e:
        raise e
