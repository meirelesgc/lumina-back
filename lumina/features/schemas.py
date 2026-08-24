# Schemas do envelope de status usados pelos endpoints (routers/templates.py e routers/abnt.py). Os relatórios têm formatos diferentes entre si, por isso `report` é um dict livre.

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lumina.schemas.common import FilterPage

ProcessingStatus = Literal['processing', 'completed', 'error']


class ConformityFilter(FilterPage):
    doc_id: str | None = None
    status: ProcessingStatus | None = None


class ProcessingAccepted(BaseModel):
    id: UUID | str
    doc_id: str
    status: ProcessingStatus = 'processing'
    file_path: str
    created_at: datetime | str

    model_config = ConfigDict(from_attributes=True)


class ProcessingResult(BaseModel):
    id: UUID | str
    doc_id: str
    status: ProcessingStatus
    file_path: str
    created_at: datetime | str
    updated_at: datetime | str | None = None
    report: dict[str, Any] | None = None
    error: str | None = None
    created_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class ProcessingResultList(BaseModel):
    count: int
    results: list[ProcessingResult]
