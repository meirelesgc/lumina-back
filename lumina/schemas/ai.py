from pydantic import BaseModel, Field
from typing import List, Optional

class Citation(BaseModel):
    chunk_id: str = Field(description="Identificador único do chunk utilizado (ex: chunk_1_4, chunk_fallback_0)")
    text_snippet: Optional[str] = Field(None, description="Pequeno trecho exato do texto citado para facilitar o mapeamento visual")

class AnswerWithCitations(BaseModel):
    answer: str = Field(description="Sua resposta completa para a pergunta do usuário.")
    citations: List[Citation] = Field(default_factory=list, description="Lista de identificadores dos chunks que justificam e embasam a sua resposta.")
