# Schemas do envelope de status usados pelos endpoints (routers/templates.py e routers/abnt.py). Os relatórios têm formatos diferentes entre si, por isso `report` é um dict livre.

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

ProcessingStatus = Literal['processing', 'completed', 'error']


class ProcessingAccepted(BaseModel):
    id: str
    doc_id: str
    status: ProcessingStatus = 'processing'
    file_path: str
    created_at: str


class ProcessingResult(BaseModel):
    id: str
    doc_id: str
    status: ProcessingStatus
    file_path: str
    created_at: str
    updated_at: str
    report: dict[str, Any] | None = None
    error: str | None = None


class ProcessingResultList(BaseModel):
    count: int
    results: list[ProcessingResult]
