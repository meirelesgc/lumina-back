from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ProjectSchema(BaseModel):
    name: str
    description: Optional[str] = None
    document_group_id: Optional[UUID] = None

    @field_validator('document_group_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v


class ProjectCreate(ProjectSchema):
    pass


class ProjectUpdate(ProjectSchema):
    id: UUID
    status: Optional[str] = None


class ProjectPublic(ProjectSchema):
    id: UUID
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectList(BaseModel):
    projects: list[ProjectPublic]


class ProjectFilter(BaseModel):
    q: Optional[str] = None
    offset: int = 0
    limit: int = 100
