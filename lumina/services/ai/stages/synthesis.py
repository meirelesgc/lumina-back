import random

from sqlalchemy.ext.asyncio import AsyncSession

from lumina import prompts as PROMPTS
from lumina.core.dependencies import Model
from lumina.models import DocumentRelease
from lumina.services.ai.stages.evaluation import with_low_verbosity


def select_synthesis_style() -> str:
    """
    Sorteia o bloco de estilo de resposta da síntese executiva.
    """
    return random.choice(list(PROMPTS.SYNTHESIS_STYLES.values()))


def format_synthesis_branch(branch: dict) -> str:
    """
    Formata um critério para o prompt da síntese, com o parecer em Markdown
    indentado como bloco sob o critério.
    """
    feedback = str(branch.get('feedback') or '').strip()
    indented = '\n'.join(f'  {line}' for line in feedback.splitlines())
    return (
        f'- Critério: {branch.get("requirement")} '
        f'(nota {branch.get("score")}/10)\n'
        f'  Parecer:\n{indented}'
    )


def generate_synthesis_prompt(simplified_args: list[dict]) -> str:
    """
    Gera o prompt para a síntese executiva OiacIA comparando os 2 critérios de
    maior nota com os 2 critérios de menor nota, com estilo sorteado.
    """
    sorted_data = sorted(
        simplified_args,
        key=lambda x: x.get('score') or 0,
        reverse=True,
    )
    highest_score_branches = sorted_data[:2]
    lowest_score_branches = sorted_data[-2:]
    highest_text = '\n'.join([
        format_synthesis_branch(x) for x in highest_score_branches
    ])
    lowest_text = '\n'.join([
        format_synthesis_branch(x) for x in lowest_score_branches
    ])
    return PROMPTS.DESCRIPTION.format(
        top_text=highest_text,
        bottom_text=lowest_text,
        style_instructions=select_synthesis_style(),
    )


async def generate_release_synthesis(
    db_release: DocumentRelease,
    simplified_args: list[dict],
    model: Model,
    session: AsyncSession,
) -> None:
    """
    Invoca o modelo para gerar a síntese executiva e a persiste no
    db_release.
    """
    prompt = generate_synthesis_prompt(simplified_args)
    desc_response = with_low_verbosity(model).invoke(prompt)
    db_release.description = desc_response.text.strip()
    await session.commit()
