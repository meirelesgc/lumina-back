import argparse
import asyncio
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from lumina.core.database import async_session
from lumina.core.llm import get_fast_model
from lumina.models import Branch, Taxonomy
from lumina.repositories import (
    branch_query_expansion_repo,
    branch_section_requirement_repo,
)
from lumina.services.ai.branch_analyzer import (
    BranchNormativeContext,
    analyze_branch_section_requirement,
    persist_branch_section_requirement,
)
from lumina.services.ai.query_expansion_service import (
    generate_query_expansions,
    persist_branch_expansions,
)

logger = logging.getLogger('lumina.scripts.enrich_existing_branches')


async def _load_active_branches(
    session, limit: Optional[int] = None
) -> list[Branch]:
    """Carrega branches ativas (deleted_at IS NULL) da base."""
    stmt = (
        select(Branch)
        .options(joinedload(Branch.taxonomy).joinedload(Taxonomy.typification))
        .where(Branch.deleted_at.is_(None))
        .order_by(Branch.created_at.asc())
    )
    if limit:
        stmt = stmt.limit(limit)
    result = await session.scalars(stmt)
    return list(result.unique())


def _build_context(branch: Branch) -> BranchNormativeContext:
    taxonomy = branch.taxonomy
    typification = taxonomy.typification if taxonomy else None
    return BranchNormativeContext(
        branch_title=branch.title,
        branch_description=branch.description,
        taxonomy_title=taxonomy.title if taxonomy else None,
        taxonomy_description=taxonomy.description if taxonomy else None,
        typification_name=typification.name if typification else None,
    )


async def enrich_branch(  # noqa: PLR0913, PLR0917
    branch_id: UUID,
    context: BranchNormativeContext,
    semaphore: asyncio.Semaphore,
    index: int,
    total: int,
    dry_run: bool = False,
    force: bool = False,
) -> str:
    """
    Gera (e persiste, salvo em dry-run) a análise de seção (Fase 2) e as
    expansões de consulta (Fase 1) de uma branch, pulando o que já
    estiver ativo salvo com `force=True`. Sessão própria por branch,
    seguindo o mesmo padrão dos jobs de background já existentes.
    """
    actions: list[str] = []
    async with semaphore, async_session() as session:
        has_requirement = bool(
            (
                await branch_section_requirement_repo.get_active_grouped(
                    session, [branch_id]
                )
            ).get(branch_id)
        )
        has_expansions = bool(
            (
                await branch_query_expansion_repo.list_active_grouped(
                    session, [branch_id]
                )
            ).get(branch_id)
        )

        llm = get_fast_model()
        model_name = getattr(llm, 'model_name', 'unknown')

        if force or not has_requirement:
            requirement = await analyze_branch_section_requirement(
                context, model=llm
            )
            if not dry_run:
                await persist_branch_section_requirement(
                    session, branch_id, requirement, model_name
                )
            actions.append(f'section_requirement={requirement.scope.value}')
        else:
            actions.append('section_requirement=já ativo (skip)')

        if force or not has_expansions:
            expansions = await generate_query_expansions(context, model=llm)
            if not dry_run and expansions.expansions:
                await persist_branch_expansions(
                    session, branch_id, expansions.expansions, model_name
                )
            actions.append(f'expansions={len(expansions.expansions)}')
        else:
            actions.append('expansions=já ativas (skip)')

        if not dry_run:
            await session.commit()

    summary = f'[{index}/{total}] {context.branch_title}: ' + ' | '.join(
        actions
    )
    print(summary)
    return summary


async def run_enrichment(
    limit: Optional[int] = None,
    concurrency: int = 5,
    dry_run: bool = False,
    force: bool = False,
) -> list[str]:
    """Enriquece branches ativas com expansões de consulta e análise de
    seção que ainda não possuem (Fases 1 e 2 do plano de recuperação)."""
    print('🔍 Buscando branches ativas (deleted_at IS NULL)...')
    async with async_session() as session:
        branches = await _load_active_branches(session, limit)
        contexts = [(branch.id, _build_context(branch)) for branch in branches]

    total = len(contexts)
    print(f'📋 Total de branches ativas encontradas: {total}')
    if total == 0:
        print('Nenhuma branch encontrada para enriquecer.')
        return []

    if dry_run:
        print('⚠️  Modo dry-run: chamadas de LLM ocorrem, mas nada é salvo.')

    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        enrich_branch(
            branch_id=branch_id,
            context=context,
            semaphore=semaphore,
            index=i + 1,
            total=total,
            dry_run=dry_run,
            force=force,
        )
        for i, (branch_id, context) in enumerate(contexts)
    ]
    results = await asyncio.gather(*tasks)

    print('\n' + '=' * 60)
    print('✅ Enriquecimento concluído.')
    print('=' * 60)
    return results


def parse_args():
    parser = argparse.ArgumentParser(
        description='Enriquece branches ativas já existentes com '
        'expansões de consulta (Fase 1) e análise de seção esperada '
        '(Fase 2), pulando as que já possuem dados ativos.'
    )
    parser.add_argument(
        '--limit',
        '-l',
        type=int,
        default=None,
        help='Limita a quantidade de branches processadas.',
    )
    parser.add_argument(
        '--concurrency',
        '-c',
        type=int,
        default=5,
        help='Número de branches processadas simultaneamente.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Chama a LLM mas não persiste nada no banco.',
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Regenera mesmo branches que já possuem dados ativos.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    asyncio.run(
        run_enrichment(
            limit=args.limit,
            concurrency=args.concurrency,
            dry_run=args.dry_run,
            force=args.force,
        )
    )


if __name__ == '__main__':
    main()
