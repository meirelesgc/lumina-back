import argparse
import asyncio
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from lumina.core.database import async_session
from lumina.models import Branch, Taxonomy
from lumina.schemas.branch import SectionRequirementScope
from lumina.services.ai.branch_analyzer import (
    BranchNormativeContext,
    analyze_branch_section_requirement,
)

logger = logging.getLogger('lumina.scripts.analyze_existing_branches')


async def process_single_branch(
    branch: Branch,
    semaphore: asyncio.Semaphore,
    index: int,
    total: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Processa uma única branch com controle de concorrência."""
    taxonomy = branch.taxonomy
    typification = taxonomy.typification if taxonomy else None

    context = BranchNormativeContext(
        branch_title=branch.title,
        branch_description=branch.description,
        taxonomy_title=taxonomy.title if taxonomy else None,
        taxonomy_description=taxonomy.description if taxonomy else None,
        typification_name=typification.name if typification else None,
    )

    if dry_run:
        print(
            f'[{index}/{total}] [DRY-RUN] Branch: {branch.title} '
            f'| Taxonomia: {context.taxonomy_title or "N/A"}'
        )
        return {
            'branch_id': str(branch.id),
            'branch_title': branch.title,
            'branch_description': branch.description,
            'taxonomy_id': str(branch.taxonomy_id)
            if branch.taxonomy_id
            else None,
            'taxonomy_title': context.taxonomy_title,
            'typification_name': context.typification_name,
            'scope': 'DRY_RUN',
            'expected_section': None,
            'reasoning': 'Execução em modo dry-run (sem chamada de LLM).',
        }

    async with semaphore:
        requirement = await analyze_branch_section_requirement(context)

    sec_display = (
        f" -> '{requirement.expected_section}'"
        if requirement.expected_section
        else ''
    )
    print(
        f'[{index}/{total}] Branch: {branch.title} '
        f'| Escopo: {requirement.scope.value}{sec_display}'
    )

    return {
        'branch_id': str(branch.id),
        'branch_title': branch.title,
        'branch_description': branch.description,
        'taxonomy_id': str(branch.taxonomy_id) if branch.taxonomy_id else None,
        'taxonomy_title': context.taxonomy_title,
        'typification_name': context.typification_name,
        'scope': requirement.scope.value,
        'expected_section': requirement.expected_section,
        'reasoning': requirement.reasoning,
    }


async def run_analysis(
    output_path: Optional[str] = None,
    limit: Optional[int] = None,
    concurrency: int = 5,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Carrega branches da base e executa a análise de requisito de seção."""
    print('🔍 Buscando branches ativas no banco de dados...')
    async with async_session() as session:
        stmt = (
            select(Branch)
            .options(
                joinedload(Branch.taxonomy).joinedload(Taxonomy.typification)
            )
            .where(Branch.deleted_at.is_(None))
            .order_by(Branch.created_at.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await session.scalars(stmt)
        branches = list(result.unique())

    total = len(branches)
    print(f'📋 Total de branches ativas encontradas: {total}')
    if total == 0:
        print('Nenhuma branch encontrada para análise.')
        return []

    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        process_single_branch(
            branch=b,
            semaphore=semaphore,
            index=i + 1,
            total=total,
            dry_run=dry_run,
        )
        for i, b in enumerate(branches)
    ]

    results = await asyncio.gather(*tasks)

    # Sumário estatístico
    scopes = Counter(r['scope'] for r in results)
    sections = Counter(
        r['expected_section']
        for r in results
        if r.get('expected_section')
        and r['scope'] == SectionRequirementScope.SPECIFIC_SECTION.value
    )

    print('\n' + '=' * 60)
    print('📊 RESUMO DA ANÁLISE DE SEÇÕES')
    print('=' * 60)
    print(f'Total de branches processadas: {total}')
    for scope, count in scopes.items():
        pct = (count / total) * 100 if total > 0 else 0
        print(f'  • {scope}: {count} ({pct:.1f}%)')

    if sections:
        print('\n📌 Seções específicas sugeridas:')
        for sec, count in sections.most_common(10):
            print(f'  - {sec}: {count}')

    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
        print(f'\n💾 Relatório detalhado salvo em: {out_file.resolve()}')

    return results


def parse_args():
    parser = argparse.ArgumentParser(
        description='Analisa branches existentes na base de dados com IA '
        'para identificar escopo de seção.'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default='lumina/storage/reports/branches_section_analysis.json',
        help='Caminho do arquivo JSON para salvar os resultados.',
    )
    parser.add_argument(
        '--limit',
        '-l',
        type=int,
        default=None,
        help='Limita a quantidade de branches analisadas.',
    )
    parser.add_argument(
        '--concurrency',
        '-c',
        type=int,
        default=5,
        help='Número de análises executadas simultaneamente.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Apenas lista as branches encontradas sem chamar a LLM.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    asyncio.run(
        run_analysis(
            output_path=args.output,
            limit=args.limit,
            concurrency=args.concurrency,
            dry_run=args.dry_run,
        )
    )


if __name__ == '__main__':
    main()
