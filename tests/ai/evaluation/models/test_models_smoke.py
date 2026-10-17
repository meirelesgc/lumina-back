"""
Cada uso de modelo do Lumina responde com a configuração de produção:
texto, saída estruturada, parecer pela cadeia de avaliação, comparação
visual por imagem e verificação ABNT por PDF (OpenSpec: swap-llm-models).

As entradas de imagem e PDF são geradas no teste, com uma página.
"""

from pathlib import Path

import pymupdf
import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel

from lumina.core.llm import get_fast_model, get_model
from lumina.core.settings import Settings
from lumina.features.abnt_check.abnt import request_criteria
from lumina.features.abnt_check.schemas import EXPECTED_BRANCH_COUNT
from lumina.features.template_check.visual_check import visual_compare
from lumina.services.ai.stages.evaluation import (
    evaluate_criteria_batch,
    get_evaluation_chain,
)

pytestmark = pytest.mark.ai

SCHEMA_ERROR = 'Erro na validação de schema'


class Answer(BaseModel):
    answer: str


@pytest.fixture
def one_page_pdf(tmp_path: Path) -> Path:
    path = tmp_path / 'pagina.pdf'
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), 'Introdução', fontsize=16)
    page.insert_text((72, 110), 'O objetivo geral é propor uma estratégia.')
    doc.save(path)
    return path


@pytest.fixture
def page_png(one_page_pdf: Path) -> bytes:
    return pymupdf.open(one_page_pdf)[0].get_pixmap(dpi=72).tobytes('png')


@pytest.mark.asyncio
async def test_modelo_principal_responde_texto():
    model = await get_model()

    response = await model.ainvoke('Responda apenas a palavra: ok')

    assert 'ok' in response.text.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize('use', ['principal', 'rápido'])
async def test_modelo_responde_saida_estruturada(use):
    model = await get_model() if use == 'principal' else get_fast_model()

    result = await model.with_structured_output(Answer).ainvoke(
        'Preencha answer com a palavra ok.'
    )

    assert isinstance(result, Answer)
    assert 'ok' in result.answer.lower()


@pytest.mark.asyncio
async def test_cadeia_de_avaliacao_registra_o_parecer():
    item = {
        'id': 'objetivo-geral',
        'document': (
            '[FONTE] chunk_id: chunk_0_0\n'
            'O objetivo geral é propor e avaliar uma estratégia de avaliação '
            'de sistemas de inteligência artificial especializados.'
        ),
        'source': 'Normas do anteprojeto',
        'requirement': 'Objetivo geral: o objetivo geral está definido.',
        'expected_section': 'Objetivo',
        'query': "Analise o item 'Objetivo geral' na seção 'Objetivo'.",
        '_chunks': [],
    }

    await evaluate_criteria_batch(
        get_evaluation_chain(await get_model()), [item]
    )

    assert SCHEMA_ERROR not in item['feedback']
    assert isinstance(item['fulfilled'], bool)


@pytest.mark.asyncio
async def test_comparacao_visual_le_imagem(page_png):
    client = AsyncOpenAI(api_key=Settings().OPENAI_API_KEY)

    result = await visual_compare(client, page_png, page_png, 'Página 1')

    assert result is not None


def test_verificacao_abnt_le_pdf(one_page_pdf, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', Settings().OPENAI_API_KEY)

    criteria = request_criteria(str(one_page_pdf))

    assert len(criteria) == EXPECTED_BRANCH_COUNT
