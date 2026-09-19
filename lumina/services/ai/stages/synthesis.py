from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from lumina import prompts as PROMPTS
from lumina.core.dependencies import Model
from lumina.models import DocumentRelease


def generate_synthesis_prompt(simplified_args: list[dict]) -> str:
    """
    Gera o prompt para a síntese executiva OiacIA comparando os 2 critérios de
    maior nota com os 2 critérios de menor nota.
    """
    sorted_data = sorted(
        simplified_args,
        key=lambda x: x.get('score') or 0,
        reverse=True,
    )
    highest_score_branches = sorted_data[:2]
    lowest_score_branches = sorted_data[-2:]
    highest_text = '\n'.join([
        f'- {x.get("requirement")}: {x.get("score")}/10 '
        f'(Feedback: {x.get("feedback")})'
        for x in highest_score_branches
    ])
    lowest_text = '\n'.join([
        f'- {x.get("requirement")}: {x.get("score")}/10 '
        f'(Feedback: {x.get("feedback")})'
        for x in lowest_score_branches
    ])
    return PROMPTS.DESCRIPTION.format(
        top_text=highest_text,
        bottom_text=lowest_text,
    )


def partition_synthesis_text(text: str) -> dict[str, str]:
    """
    Particiona o texto da síntese executiva em 4 blocos estruturados:
    saudação, pontos atendidos, pontos a aprimorar e orientação final.
    """
    if not text:
        return {
            'greeting': '',
            'fulfilled_points': '',
            'improvement_points': '',
            'final_guidance': '',
        }

    h_fulfilled = '# Pontos atendidos'
    h_improve = '# Pontos a aprimorar'
    h_final = '# Orientação final'

    lower_text = text.lower()
    idx_f = lower_text.find(h_fulfilled.lower())
    idx_i = lower_text.find(h_improve.lower())
    idx_g = lower_text.find(h_final.lower())

    greeting = ''
    fulfilled = ''
    improve = ''
    final = ''

    if idx_f != -1:
        greeting = text[:idx_f].strip()
        next_idx = (
            idx_i
            if idx_i != -1 and idx_i > idx_f
            else (idx_g if idx_g != -1 and idx_g > idx_f else len(text))
        )
        fulfilled = text[idx_f + len(h_fulfilled) : next_idx].strip()
    else:
        greeting = text.strip()

    if idx_i != -1:
        next_idx = idx_g if idx_g != -1 and idx_g > idx_i else len(text)
        improve = text[idx_i + len(h_improve) : next_idx].strip()

    if idx_g != -1:
        final = text[idx_g + len(h_final) :].strip()

    return {
        'greeting': greeting,
        'fulfilled_points': fulfilled,
        'improvement_points': improve,
        'final_guidance': final,
    }


async def record_synthesis_stage(
    run_logger: Any,
    db_release: DocumentRelease,
    simplified_args: list[dict],
    model: Model,
    session: AsyncSession,
) -> None:
    """
    Invoca o modelo para gerar a síntese, persiste no db_release e registra
    a macroetapa no RunLogger.
    """
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

        prompt = generate_synthesis_prompt(simplified_args)
        desc_response = model.invoke(prompt)
        desc_text = desc_response.content.strip()
        db_release.description = desc_text
        await session.commit()

        partitioned = partition_synthesis_text(desc_text)
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
