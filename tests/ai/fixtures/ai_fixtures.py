import pytest
from langchain_community.chat_models.fake import FakeListChatModel


@pytest.fixture
def fake_release_pipeline_llm():
    """
    Mock determinístico para a rota de criação de release.
    O pipeline `release_orchestrator` faz N chamadas de `abatch` e 1 chamada de sumário.
    Nós injetamos as respostas sequenciais que o Mock deve retornar.
    """
    responses = [
        # Resposta mockada para `chain.abatch(eval_args)` onde a chain tem um JsonOutputParser
        '{"fulfilled": true, "score": 1.0, "feedback": "Atende totalmente aos requisitos."}',
        # Resposta mockada para a geração do sumário
        'Resumo da Avaliação da IA gerada automaticamente com sucesso.',
    ]
    return FakeListChatModel(responses=responses)


@pytest.fixture
def fake_release_pipeline_llm_failure():
    """
    Exemplo de Contract Test onde a IA quebra a estrutura de resposta (JSON inválido).
    """
    responses = [
        # Resposta sem estrutura JSON
        'Desculpe, não consigo responder a isso.',
        'Resumo falho.',
    ]
    return FakeListChatModel(responses=responses)
