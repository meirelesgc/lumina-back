from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from lumina.core.settings import Settings

settings = Settings()

# Uso rápido e simples: seletor, classificação de ramos, expansões, sugestão
# de árvore e comparação visual de template.
FAST_MODEL = 'gpt-6-luna'
FAST_REASONING_EFFORT = 'none'
FAST_TEMPERATURE = 0

# Uso médio e equilibrado: avaliação, síntese, chat e verificação ABNT. Com
# reasoning.effort='medium' o modelo recusa "temperature" (erro 400), então
# o parâmetro não é enviado.
MAIN_MODEL = 'gpt-6-luna'
MAIN_REASONING_EFFORT = 'medium'

model = ChatOpenAI(
    model=MAIN_MODEL,
    api_key=settings.OPENAI_API_KEY,
    reasoning={'effort': MAIN_REASONING_EFFORT},
)


@dataclass
class _ModelOverrides:
    fast: Optional[BaseChatModel] = None


_overrides = _ModelOverrides()


async def get_model():  # pragma: no cover
    return model


def get_fast_model(
    model_name: Optional[str] = None,
    temperature: float = FAST_TEMPERATURE,
) -> BaseChatModel:
    if _overrides.fast is not None:
        return _overrides.fast
    return ChatOpenAI(
        model=model_name or FAST_MODEL,
        api_key=settings.OPENAI_API_KEY,
        reasoning={'effort': FAST_REASONING_EFFORT},
        temperature=temperature,
    )


def set_fast_model_override(mock_model: Optional[BaseChatModel]) -> None:
    _overrides.fast = mock_model
