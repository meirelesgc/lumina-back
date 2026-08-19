from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lumina.schemas.common import FilterPage
from lumina.schemas.project import ProjectPublic
from lumina.schemas.user import UserPublic


class AdvisorshipRoleType(str, Enum):
    MAIN_ADVISOR = 'MAIN_ADVISOR'
    CO_ADVISOR = 'CO_ADVISOR'
    EVALUATOR = 'EVALUATOR'


class AdvisorshipStatus(str, Enum):
    ACTIVE = 'ACTIVE'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class AdvisorshipSchema(BaseModel):
    advisor_id: UUID
    advisee_id: UUID
    project_id: Optional[UUID] = None
    role_type: AdvisorshipRoleType = AdvisorshipRoleType.MAIN_ADVISOR
    topic: Optional[str] = None
    status: AdvisorshipStatus = AdvisorshipStatus.ACTIVE


class AdvisorshipCreate(BaseModel):
    advisor_id: UUID
    advisee_id: UUID
    project_id: Optional[UUID] = None
    role_type: AdvisorshipRoleType = AdvisorshipRoleType.MAIN_ADVISOR
    topic: Optional[str] = None


class AdvisorshipUpdate(BaseModel):
    project_id: Optional[UUID] = None
    role_type: Optional[AdvisorshipRoleType] = None
    topic: Optional[str] = None
    status: Optional[AdvisorshipStatus] = None


class AdvisorshipPublic(BaseModel):
    id: UUID
    advisor_id: UUID
    advisee_id: UUID
    project_id: Optional[UUID] = None
    role_type: str
    topic: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    advisor: Optional[UserPublic] = None
    advisee: Optional[UserPublic] = None
    project: Optional[ProjectPublic] = None

    model_config = ConfigDict(from_attributes=True)


class AdvisorshipList(BaseModel):
    advisorships: list[AdvisorshipPublic]


class AdvisorshipFilter(FilterPage):
    advisor_id: Optional[UUID] = None
    advisee_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    role_type: Optional[AdvisorshipRoleType] = None
    status: Optional[AdvisorshipStatus] = None
    q: Optional[str] = None


class AdviseeCardPublic(BaseModel):
    advisee: UserPublic
    advisorship_id: UUID
    role_type: str
    topic: Optional[str] = None
    status: str
    project: Optional[ProjectPublic] = None
    total_documents: int = 0
    pending_reviews: int = 0

    model_config = ConfigDict(from_attributes=True)


class AdviseeListPublic(BaseModel):
    advisees: list[AdviseeCardPublic]


class AdvisorCardPublic(BaseModel):
    advisor: UserPublic
    advisorship_id: UUID
    role_type: str
    topic: Optional[str] = None
    status: str
    project: Optional[ProjectPublic] = None

    model_config = ConfigDict(from_attributes=True)


class AdvisorListPublic(BaseModel):
    advisors: list[AdvisorCardPublic]


class DocumentAcademicContextPublic(BaseModel):
    document_id: UUID
    document_name: str
    author: Optional[UserPublic] = None
    advisors: list[UserPublic] = []
    project: Optional[ProjectPublic] = None
    advisorship: Optional[AdvisorshipPublic] = None

    model_config = ConfigDict(from_attributes=True)
