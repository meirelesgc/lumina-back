from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_community.chat_models.fake import FakeListChatModel
from langchain_openai import ChatOpenAI

from lumina import prompts as PROMPTS
from lumina.services.ai.stages import evaluation as evaluation_module
from lumina.services.ai.stages.evaluation import (
    evaluate_criteria_batch,
    get_evaluation_chain,
    select_evaluation_style,
    with_low_verbosity,
)

EXPECTED_STYLE_COUNT = 4
EXPECTED_ATTEMPTS = 2


def _eval_item(branch_id: str) -> dict:
    return {
        'id': branch_id,
        'document': 'trecho',
        'source': 'fonte',
        'requirement': 'requisito',
        'expected_section': 'Seção',
        'query': 'consulta',
        '_chunks': [],
    }


def test_evaluation_styles_available():
    assert set(PROMPTS.EVALUATION_STYLES) == {
        'verdict_lists',
        'checklist',
        'table',
        'summary_bullets',
    }
    assert len(PROMPTS.EVALUATION_STYLES) == EXPECTED_STYLE_COUNT


def test_select_evaluation_style_returns_known_style():
    for _ in range(20):
        assert select_evaluation_style() in PROMPTS.EVALUATION_STYLES.values()


@pytest.mark.asyncio
async def test_evaluate_criteria_batch_draws_style_per_criterion(monkeypatch):
    styles = list(PROMPTS.EVALUATION_STYLES.values())
    draws = iter(styles)
    monkeypatch.setattr(
        evaluation_module.random, 'choice', lambda _options: next(draws)
    )
    chain = MagicMock()
    chain.abatch = AsyncMock(
        return_value=[
            {'score': 8, 'fulfilled': True, 'feedback': 'ok'},
            {'score': 3, 'fulfilled': False, 'feedback': 'lacuna'},
        ]
    )
    eval_args = [_eval_item('a'), _eval_item('b')]

    result = await evaluate_criteria_batch(chain, eval_args)

    assert result[0]['style_instructions'] == styles[0]
    assert result[1]['style_instructions'] == styles[1]
    assert styles[0] in result[0]['prompt']
    assert styles[1] in result[1]['prompt']


@pytest.mark.asyncio
async def test_evaluate_criteria_batch_keeps_style_on_retry(monkeypatch):
    calls = []

    def fake_choice(options):
        calls.append(options)
        return options[len(calls) % len(options)]

    monkeypatch.setattr(evaluation_module.random, 'choice', fake_choice)
    chain = MagicMock()
    chain.abatch = AsyncMock(
        side_effect=[
            RuntimeError('falha transitória'),
            [{'score': 8, 'fulfilled': True, 'feedback': 'ok'}],
        ]
    )
    eval_args = [_eval_item('a')]

    result = await evaluate_criteria_batch(chain, eval_args)

    assert chain.abatch.await_count == EXPECTED_ATTEMPTS
    assert len(calls) == 1
    assert result[0]['style_instructions'] in (
        PROMPTS.EVALUATION_STYLES.values()
    )


def test_evaluation_chain_renders_style_block():
    chain = get_evaluation_chain(FakeListChatModel(responses=['{}']))
    style = PROMPTS.EVALUATION_STYLES['table']

    rendered = chain.steps[0].format(
        **_eval_item('a'), style_instructions=style
    )

    assert style in rendered
    assert 'no máximo uma ação curta por lacuna' in rendered


def test_with_low_verbosity_copies_openai_model():
    model = ChatOpenAI(model='gpt-5-mini', api_key='teste')

    result = with_low_verbosity(model)

    assert result is not model
    assert result.verbosity == 'low'
    assert result.model_name == model.model_name
    assert model.verbosity is None


def test_with_low_verbosity_keeps_model_without_field():
    model = FakeListChatModel(responses=['ok'])

    assert with_low_verbosity(model) is model
