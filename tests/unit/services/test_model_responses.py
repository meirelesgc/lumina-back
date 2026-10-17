"""
Jornada: o analista envia um documento, recebe os pareceres de cada critério
e a síntese, e conversa com o documento no chat. Os modelos com raciocínio
respondem pela Responses API, e o LangChain entrega o conteúdo como lista de
blocos. A troca de modelo não pode transformar pareceres válidos em "não
contempla" nem mostrar a estrutura dos blocos na tela
(OpenSpec: swap-llm-models).
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.language_models.fake_chat_models import (
    GenericFakeChatModel,
)
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser

from lumina.schemas import DocumentReleaseFeedback
from lumina.services import assistant_service
from lumina.services.ai import chat
from lumina.services.ai.stages.evaluation import (
    _process_eval_item,  # noqa: PLC2701
)
from lumina.services.ai.stages.synthesis import generate_release_synthesis

VERDICT = {
    'feedback': '**Veredito:** Atende.',
    'fulfilled': True,
    'score': 9,
    'citations': [],
}


def blocks(text: str) -> AIMessage:
    return AIMessage(
        content=[{'type': 'text', 'text': text, 'annotations': []}]
    )


def fake_model(message: AIMessage) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter([message]))


@pytest.mark.parametrize(
    'raw_resp',
    [blocks(json.dumps(VERDICT)), AIMessage(content=json.dumps(VERDICT))],
    ids=['blocos', 'texto'],
)
def test_parecer_registra_o_veredito_do_json(raw_resp):
    item = {'id': 'ramo', '_chunks': []}
    parser = JsonOutputParser(pydantic_object=DocumentReleaseFeedback)

    _process_eval_item(item, raw_resp, parser)

    assert item['fulfilled'] is True
    assert item['score'] == VERDICT['score']
    assert item['feedback'] == VERDICT['feedback']


@pytest.mark.asyncio
async def test_sintese_grava_so_o_texto():
    db_release = SimpleNamespace(description=None)
    session = MagicMock(commit=AsyncMock())

    await generate_release_synthesis(
        db_release,
        [{'requirement': 'Critério', 'score': 5, 'feedback': 'Parecer.'}],
        fake_model(blocks('  Síntese executiva.  ')),
        session,
    )

    assert db_release.description == 'Síntese executiva.'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'module',
    [chat, assistant_service],
    ids=['chat', 'assistente'],
)
async def test_chat_devolve_so_o_texto(module, monkeypatch):
    monkeypatch.setattr(
        module.doc_repo,
        'get_by_id',
        AsyncMock(return_value=SimpleNamespace(deleted_at=None)),
    )
    monkeypatch.setattr(
        module.chat_repo,
        'get_conversation_by_id',
        AsyncMock(return_value=SimpleNamespace(context_text='Texto.')),
    )

    result = await module.chat_with_document(
        doc_id='doc',
        message='Qual o objetivo?',
        history=[],
        model=fake_model(blocks('Resposta do chat.')),
        session=MagicMock(),
        conversation_id='conversa',
    )

    assert result == {'response': 'Resposta do chat.'}
