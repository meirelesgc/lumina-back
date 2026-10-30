import re
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    chunk_id: str = Field(
        description='Identificador único do chunk utilizado (ex: chunk_1_4, chunk_fallback_0)'
    )
    sentences: List[int] = Field(
        default_factory=list,
        description='Números das frases citadas, sem o prefixo: [s2] vira 2. Frases vizinhas vão na mesma citação.',
    )
    text_snippet: Optional[str] = Field(
        None,
        description='Pequeno trecho exato do texto citado, usado só em trechos sem frases marcadas',
    )

    @field_validator('sentences', mode='before')
    @classmethod
    def sentence_numbers(cls, value: Any) -> List[int]:
        """Aceita os números também na forma do marcador, como `s2`."""
        digits = [re.sub(r'\D', '', str(item)) for item in value or []]
        return [int(number) for number in digits if number]


class AnswerWithCitations(BaseModel):
    answer: str = Field(
        description='Sua resposta completa para a pergunta do usuário.'
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description='Lista de identificadores dos chunks que justificam e embasam a sua resposta.',
    )
