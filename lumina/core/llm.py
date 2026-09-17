from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from lumina.core.settings import Settings

settings = Settings()
model = ChatOpenAI(
    model='gpt-5-mini',
    api_key=settings.OPENAI_API_KEY,
    temperature=0.1,
)


@dataclass
class _ModelOverrides:
    fast: Optional[BaseChatModel] = None


_overrides = _ModelOverrides()


async def get_model():  # pragma: no cover
    return model


def get_fast_model(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> BaseChatModel:
    if _overrides.fast is not None:
        return _overrides.fast
    name = model_name or 'gpt-4o-mini'
    return ChatOpenAI(
        model=name,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )


def set_fast_model_override(mock_model: Optional[BaseChatModel]) -> None:
    _overrides.fast = mock_model
