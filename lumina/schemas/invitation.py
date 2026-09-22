from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from lumina.schemas.advisorship import AdvisorshipPublic, AdvisorshipRoleType
from lumina.schemas.common import FilterPage, Token
from lumina.schemas.project import ProjectPublic
from lumina.schemas.user import UserPublic


class InvitationStatus(str, Enum):
    PENDING = 'PENDING'
    ACCEPTED = 'ACCEPTED'
    REJECTED = 'REJECTED'
    CANCELLED = 'CANCELLED'


InvitationRoleType = AdvisorshipRoleType


class InvitationCreate(BaseModel):
    email: EmailStr
    project_id: Optional[UUID] = None
    role_type: AdvisorshipRoleType = AdvisorshipRoleType.MAIN_ADVISOR
    topic: Optional[str] = None


class InvitationPublic(BaseModel):
    id: UUID
    email: str
    inviter_id: UUID
    token: str
    project_id: Optional[UUID] = None
    role_type: str
    topic: Optional[str] = None
    status: str
    expires_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    inviter: Optional[UserPublic] = None
    project: Optional[ProjectPublic] = None

    model_config = ConfigDict(from_attributes=True)


class InvitationPublicCheck(BaseModel):
    token: str
    email: str
    status: str
    is_valid: bool
    is_expired: bool
    user_exists: bool
    inviter_name: str
    inviter_email: str
    project_title: Optional[str] = None
    topic: Optional[str] = None
    role_type: str
    expires_at: datetime


class InvitationRegisterAndAccept(BaseModel):
    username: str
    phone_number: str
    password: str


class InvitationAcceptResponse(BaseModel):
    message: str
    invitation: InvitationPublic
    advisorship: Optional[AdvisorshipPublic] = None


class InvitationRegisterResponse(BaseModel):
    message: str
    user: UserPublic
    token: Token
    invitation: InvitationPublic
    advisorship: Optional[AdvisorshipPublic] = None


class InvitationFilter(FilterPage):
    email: Optional[str] = None
    inviter_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    status: Optional[InvitationStatus] = None


class InvitationList(BaseModel):
    invitations: list[InvitationPublic]
