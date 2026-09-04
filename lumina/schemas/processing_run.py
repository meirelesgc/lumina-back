from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'


class ProcessingEventType(str, Enum):
    RUN_STARTED = 'run_started'
    STAGE_STARTED = 'stage_started'
    STAGE_PROGRESS = 'stage_progress'
    CRITERION_EVALUATED = 'criterion_evaluated'
    STAGE_COMPLETED = 'stage_completed'
    STAGE_FAILED = 'stage_failed'
    RUN_COMPLETED = 'run_completed'
    RUN_FAILED = 'run_failed'


class ProcessingEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    event: str
    stage: Optional[str] = None
    status: ProcessingStatus
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    duration_ms: Optional[int] = None
    item_count: Optional[int] = None
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class CriterionEvaluationRecord(BaseModel):
    criterion_id: str
    title: str
    status: ProcessingStatus
    duration_ms: int
    score: Optional[float] = None
    citations_count: int = 0
    feedback: Optional[str] = None
    error_message: Optional[str] = None
    retrieval: Optional[Dict[str, Any]] = None
    llm_interaction: Optional[Dict[str, Any]] = None
    llm_output: Optional[Dict[str, Any]] = None


class ProcessingStageDetail(BaseModel):
    name: str
    status: ProcessingStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    item_count: Optional[int] = None
    error_details: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessingRunSummary(BaseModel):
    id: UUID
    release_id: UUID
    document_id: UUID
    document_name: Optional[str] = None
    status: ProcessingStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    stages_count: int = 0
    error_summary: Optional[str] = None


class ProcessingRunListResponse(BaseModel):
    items: List[ProcessingRunSummary]
    total: int
    limit: int
    offset: int


class ProcessingRunDetail(BaseModel):
    id: UUID
    release_id: UUID
    document_id: UUID
    document_name: Optional[str] = None
    status: ProcessingStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_summary: Optional[str] = None
    stages: List[ProcessingStageDetail] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
