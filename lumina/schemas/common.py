from typing import Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class Message(BaseModel):
    message: str


class FilterPage(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1)


class WSMessage(BaseModel):
    event: str
    message: str
    payload: Optional[dict]


class DocumentRect(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DocumentReference(BaseModel):
    chunk_id: Optional[str] = None
    page: int
    text_snippet: Optional[str] = None
    rects: list[DocumentRect] = Field(default_factory=list)
