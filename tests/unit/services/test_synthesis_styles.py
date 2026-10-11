import pytest

from lumina import prompts as PROMPTS
from lumina.services.ai.stages import synthesis as synthesis_module
from lumina.services.ai.stages.synthesis import (
    format_synthesis_branch,
    generate_synthesis_prompt,
    select_synthesis_style,
)

SECTION_TITLES = (
    '# Pontos atendidos',
    '# Pontos a aprimorar',
    '# Orientação final',
)


def _branches() -> list[dict]:
    return [
        {'requirement': 'Prazo', 'score': 9, 'feedback': '- Prazo ok'},
        {'requirement': 'Objeto', 'score': 8, 'feedback': 'Atende.'},
        {'requirement': 'Garantia', 'score': 2, 'feedback': 'Ausente.'},
        {'requirement': 'Sanções', 'score': 4, 'feedback': 'Parcial.'},
    ]


def test_synthesis_styles_available():
    assert set(PROMPTS.SYNTHESIS_STYLES) == {
        'bullets',
        'checklist',
        'summary_bullets',
    }


def test_select_synthesis_style_returns_known_style():
    for _ in range(20):
        assert select_synthesis_style() in PROMPTS.SYNTHESIS_STYLES.values()


@pytest.mark.parametrize('style_key', list(PROMPTS.SYNTHESIS_STYLES))
def test_synthesis_prompt_keeps_section_titles(monkeypatch, style_key):
    style = PROMPTS.SYNTHESIS_STYLES[style_key]
    monkeypatch.setattr(
        synthesis_module.random, 'choice', lambda _options: style
    )

    prompt = generate_synthesis_prompt(_branches())

    assert style in prompt
    for title in SECTION_TITLES:
        assert title in prompt
    assert 'Prazo (nota 9/10)' in prompt
    assert 'Garantia (nota 2/10)' in prompt


def test_format_synthesis_branch_indents_multiline_feedback():
    branch = {
        'requirement': 'Garantia',
        'score': 3,
        'feedback': (
            '**Situação:** Não atende\n\n**Lacunas**\n- Sem modalidade'
        ),
    }

    result = format_synthesis_branch(branch)

    assert result.startswith('- Critério: Garantia (nota 3/10)')
    assert '\n  **Situação:** Não atende' in result
    assert '\n  - Sem modalidade' in result
    assert 'Feedback:' not in result
