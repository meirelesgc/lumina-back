import asyncio
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from lumina import prompts as PROMPTS
from lumina.core.llm import get_fast_model
from lumina.models import Typification
from lumina.schemas.branch import SectionRequirementScope
from lumina.services.ai.stages.criteria import (
    criteria_fields,
    iter_tree_branches,
    merge_presidio_mappings,
)
from lumina.services.ai.stages.outline import OutlineSection, outline_markdown
from lumina.services.ai.stages.retrieval import format_context

MAX_ROUNDS = 3
MAX_OUTPUT_RETRIES = 2
SELECTION_CONCURRENCY = 8


class SelectionStep(BaseModel):
    """Saída estruturada de uma rodada do seletor de seções."""

    section_ids: List[str] = Field(
        description='Ids do sumário que faltam ler para julgar o critério.'
    )
    reason: str = Field(description='Uma frase com o motivo da escolha.')
    enough: bool = Field(
        description='As seções já lidas bastam para julgar o critério.'
    )
    not_found: bool = Field(
        description=(
            'As seções mais prováveis já foram lidas e o conteúdo exigido não '
            'está no documento.'
        )
    )


class SelectionOutcome(str, Enum):
    SELECTED = 'selected'
    ENTIRE_DOCUMENT = 'entire_document'
    NOT_FOUND = 'not_found'
    FALLBACK = 'fallback'


@dataclass
class SectionSelection:
    """Registro da seleção que gerou o contexto de um critério."""

    scope: str
    outcome: SelectionOutcome
    section_ids: List[str]
    tokens: int
    model: Optional[str]
    rounds: List[dict] = field(default_factory=list)
    error: Optional[str] = None
    expected_section: Optional[str] = None

    def to_dict(self) -> dict:
        return {**asdict(self), 'outcome': self.outcome.value}


def get_selector_model() -> BaseChatModel:
    """Modelo do seletor: o uso rápido."""
    return get_fast_model()


def read_sections_text(sections: List[OutlineSection]) -> str:
    if not sections:
        return 'Nenhuma.'
    return '\n\n'.join(
        f'### [{section.id}] {section.title}\n{section.text}'
        for section in sections
    )


def selection_prompt(  # noqa: PLR0913, PLR0917
    outline_md: str,
    taxonomy: dict,
    branch: dict,
    expected_section: Optional[str],
    read: List[OutlineSection],
    round_number: int,
) -> str:
    hint = (
        f'- Seção esperada pelo analista: {expected_section}\n'
        if expected_section
        else ''
    )
    return PROMPTS.SECTION_SELECTION_PROMPT.format(
        outline=outline_md,
        taxonomy=(taxonomy.get('title') or '').strip(),
        requirement=criteria_fields(taxonomy, branch)['requirement'],
        hint=hint,
        read_sections=read_sections_text(read),
        round_number=round_number,
        max_rounds=MAX_ROUNDS,
    )


async def ask_selector(structured, prompt: str) -> SelectionStep:
    """Uma rodada do seletor, repetida quando a saída sai do schema."""
    last_error: Optional[Exception] = None
    for _ in range(1 + MAX_OUTPUT_RETRIES):
        try:
            return await structured.ainvoke(prompt)
        except Exception as error:  # noqa: BLE001
            last_error = error
    raise last_error


def scope_of(section_requirement: Optional[dict]) -> str:
    scope = (section_requirement or {}).get('scope')
    return scope or SectionRequirementScope.UNKNOWN.value


async def select_sections(  # noqa: PLR0913, PLR0917
    model: BaseChatModel,
    outline: List[OutlineSection],
    taxonomy: dict,
    branch: dict,
    section_requirement: Optional[dict] = None,
    outline_md: Optional[str] = None,
) -> SectionSelection:
    """
    Escolhe as seções que o avaliador recebe para um critério. Escopo de
    documento inteiro recebe todas as seções sem chamar o seletor. Nos
    demais, o seletor pede seções pelo id, lê o texto integral e decide se
    basta, pede outras ou conclui que o conteúdo não existe, em até
    `MAX_ROUNDS` rodadas.
    """
    scope = scope_of(section_requirement)
    expected = (section_requirement or {}).get('expected_section')
    by_id = {section.id: section for section in outline}
    model_name = getattr(model, 'model_name', None)

    def result(outcome, read, rounds, error=None) -> SectionSelection:
        ordered = sorted(read, key=lambda s: s.index)
        return SectionSelection(
            scope=scope,
            outcome=outcome,
            section_ids=[s.id for s in ordered],
            tokens=sum(s.tokens for s in ordered),
            model=model_name,
            rounds=rounds,
            error=error,
            expected_section=expected,
        )

    if scope == SectionRequirementScope.ENTIRE_DOCUMENT.value:
        return result(SelectionOutcome.ENTIRE_DOCUMENT, outline, [])

    structured = model.with_structured_output(SelectionStep)
    outline_md = outline_md or outline_markdown(outline)
    read: List[OutlineSection] = []
    rounds: List[dict] = []
    outcome, error = SelectionOutcome.SELECTED, None

    for round_number in range(1, MAX_ROUNDS + 1):
        prompt = selection_prompt(
            outline_md, taxonomy, branch, expected, read, round_number
        )
        try:
            step = await ask_selector(structured, prompt)
        except Exception as exc:  # noqa: BLE001
            outcome, error = SelectionOutcome.FALLBACK, str(exc)
            break

        read_ids = {s.id for s in read}
        new = [
            by_id[i]
            for i in dict.fromkeys(step.section_ids)
            if i in by_id and i not in read_ids
        ]
        rounds.append({
            'requested': step.section_ids,
            'invalid': [i for i in step.section_ids if i not in by_id],
            'reason': step.reason,
            'enough': step.enough,
            'not_found': step.not_found,
        })

        # "Não existe" e "basta" só valem depois de ao menos uma leitura.
        if read and step.not_found:
            outcome = SelectionOutcome.NOT_FOUND
            break
        if read and step.enough:
            break
        if not new:
            if not read:
                outcome = SelectionOutcome.FALLBACK
                error = 'primeira rodada sem seção válida'
            break
        read.extend(new)

    sections = outline if outcome == SelectionOutcome.FALLBACK else read
    return result(outcome, sections, rounds, error)


def build_selection_payload(
    taxonomy: dict,
    branch: dict,
    outline: List[OutlineSection],
    selection: SectionSelection,
) -> dict:
    """
    Payload de avaliação de um critério com as seções escolhidas, nas mesmas
    chaves que a avaliação e o snapshot leem. Conteúdo inexistente sai com o
    veredito pronto e não passa pelo avaliador.
    """
    selected = [s for s in outline if s.id in set(selection.section_ids)]
    chunks = [chunk for section in selected for chunk in section.chunks]
    payload = {
        **criteria_fields(taxonomy, branch),
        'document': format_context(chunks),
        'presidio_mapping': merge_presidio_mappings(chunks),
        '_chunks': chunks,
        'context_selection': selection.to_dict(),
    }
    if selection.outcome != SelectionOutcome.NOT_FOUND:
        return payload

    inspected = '; '.join(f'{s.id} {s.title}' for s in selected)
    return {
        **payload,
        'document': '',
        '_chunks': [],
        'fulfilled': False,
        'score': 0,
        'feedback': PROMPTS.NOT_FOUND_FEEDBACK.format(sections=inspected),
        'citations': [],
        'references': [],
        'skip_evaluation': True,
    }


async def select_payload(  # noqa: PLR0913, PLR0917
    model: BaseChatModel,
    outline: List[OutlineSection],
    taxonomy: dict,
    branch: dict,
    section_requirement: Optional[dict] = None,
    outline_md: Optional[str] = None,
) -> dict:
    """Seleção e payload de avaliação de um critério."""
    selection = await select_sections(
        model, outline, taxonomy, branch, section_requirement, outline_md
    )
    return build_selection_payload(taxonomy, branch, outline, selection)


def section_requirement_of(branch: dict) -> dict:
    """Marcação de escopo do ramo na forma que `select_sections` recebe."""
    return {
        'scope': branch.get('section_scope'),
        'expected_section': branch.get('expected_section'),
    }


async def select_evaluation_payloads(
    tree: List[Typification] | List[dict],
    outline: List[OutlineSection],
    model: BaseChatModel,
) -> List[dict]:
    """
    Monta o payload de avaliação de todos os critérios da árvore, com a
    seleção de cada critério em paralelo, limitada por
    `SELECTION_CONCURRENCY`. O escopo de cada critério vem da marcação do
    ramo.
    """
    outline_md = outline_markdown(outline)
    semaphore = asyncio.Semaphore(SELECTION_CONCURRENCY)

    async def run(taxonomy: dict, branch: dict) -> dict:
        async with semaphore:
            payload = await select_payload(
                model,
                outline,
                taxonomy,
                branch,
                section_requirement_of(branch),
                outline_md,
            )
        payload['expansion_generation_version'] = None
        return payload

    return list(
        await asyncio.gather(*[
            run(taxonomy, branch)
            for taxonomy, branch in iter_tree_branches(tree)
        ])
    )
