# Padrões de Testes para IA (AI Testing Standards)

## Contexto e Objetivo
O Lumina-Back possui uma camada metodológica rigorosa para testes de Inteligência Artificial, tratando-os como uma disciplina de engenharia de software separada. Nós separamos **testar o software que usa IA** de **testar a qualidade das respostas geradas pela IA**.

Esse documento normatiza como construir Mocks Determinísticos (Fake Models) para testes da API, e como definir *Golden Datasets* para medição de qualidade.

---

## 1. As Três Categorias de Testes de IA

A estrutura de testes baseada em modelos de linguagem no Lumina é dividida em três pilares:

### A. AI Integration Tests (Integração Rápida e Determinística)
Validam o fluxo de aplicação e sua tolerância ao comportamento estrutural do LLM.
- **Foco:** O roteador funciona de ponta a ponta? O banco salva o estado? O background task não quebra? Trata exceções da API da OpenAI?
- **Restrição de Custo:** **NENHUM TOKEN DEVE SER GASTO AQUI.**
- **Como Testar:** Utilize `app.dependency_overrides[get_model]` injetando o `FakeListChatModel` do Langchain.

### B. AI Contract Tests (Contratos Estruturados)
Validam se o parsing do output (JSON) não quebra a aplicação.
- **Foco:** Verificar se a estrutura de Pydantic Models (ex: `DocumentReleaseFeedback`) sobrevive a respostas que falham campos, possuem tipos errados, ou estão corrompidas.

### C. AI Evaluation (Golden Datasets e Qualidade Real)
Valida a factualidade, alucinação, "groundedness" e utilidade das respostas reais usando chamadas reais para provedores (OpenAI/Gemini).
- **Foco:** Qualidade semântica (Groundedness, Retrieval Relevance, Instruction Following).
- **Onde mora:** Apenas diretórios dedicados a evaluation (`tests/ai/evaluation/`). 
- **Marcação:** Requer o decorador `@pytest.mark.ai_eval` e/ou `@pytest.mark.llm` para isolamento de execução.

---

## 2. A Estrutura dos Golden Datasets

Qualquer teste qualitativo de IA no projeto exige um Golden Dataset (uma Base Assinada de Casos de Uso).
Eles residem em `tests/ai/evaluation/datasets/`.

### O Que É um Golden Dataset?
Um arquivo JSON versionado (ex: `release_tree_golden.json`) que estipula o caso esperado:
1. `id` e `category` (ex: `happy_path`, `missing_information`, `prompt_injection`).
2. `input` (O dicionário exato enviado na cadeia de prompt, contendo contexto de RAG e a query).
3. `expected` (Regras de assertions, tais como `expected_behavior`, `score_min`, `forbidden_facts`, `grounded`).

#### O Caso Crítico do RAG (Missing Information)
Sempre adicione casos no Golden Dataset onde a informação **NÃO EXISTE** no contexto (documento). O modelo deve obrigatoriamente se recusar a preencher a informação e reduzir o *score* ou admitir que a requisição não foi satisfeita (`fulfilled = false`). Isso valida o "Groundedness".

---

## 3. Thresholds de Qualidade e Critical Failures

Ao avaliar a qualidade de uma suíte inteira de IA:
- `Quality Score >= threshold AND Critical Failures == 0`
- **Falha Crítica (Critical AI Behavior):** Inventar informações forjadas (Alucinação grave), produzir Output JSON inválido (quando estruturado), expor dados errados. Um teste `ai_eval` deve falhar imediatamente a suíte se uma Critical Failure acontecer.

---

## 4. Práticas de Fixtures e Overrides (FastAPI + LangChain)

Para testes da API (Integration / Contract), onde injetamos os fakes:

```python
import pytest
from langchain_community.chat_models.fake import FakeListChatModel

@pytest.fixture
def fake_release_pipeline_llm():
    """
    Simula um pipeline de duas etapas:
    1. LangChain JSON Output (ex: abatch)
    2. Geração de texto livre (descrição final)
    """
    responses = [
        '{"fulfilled": true, "score": 1.0, "feedback": "Atende o requisito."}',
        "Resumo gerado da release: 1 item contemplado."
    ]
    return FakeListChatModel(responses=responses)
```

No FastAPI Test:
```python
def test_create_release(client, doc, fake_release_pipeline_llm):
    app.dependency_overrides[get_model] = lambda: fake_release_pipeline_llm
    response = client.post(f"/doc/{doc.id}/releases", ...)
    assert response.status_code == 201
```

*(Lembre-se: o FastAPI `TestClient` executará as BackgroundTasks bloqueando a thread de forma síncrona logo antes de retornar o objeto `Response`, o que significa que o `release_pipeline` e a injeção do mock vão rodar e concluir dentro da chamada `client.post()`).*
