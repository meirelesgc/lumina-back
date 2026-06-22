from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentGroupSchema(BaseModel):
    name: str


class DocumentGroupCreate(DocumentGroupSchema):
    pass


class DocumentGroupUpdate(DocumentGroupSchema):
    id: UUID


class DocumentGroupItemSchema(BaseModel):
    name: str
    icon_path: Optional[str] = None


class DocumentGroupItemCreate(DocumentGroupItemSchema):
    group_id: UUID


class DocumentGroupItemUpdate(DocumentGroupItemSchema):
    id: UUID


class DocumentGroupItemPublic(DocumentGroupItemSchema):
    id: UUID
    group_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentGroupPublic(DocumentGroupSchema):
    id: UUID
    items: list[DocumentGroupItemPublic] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentGroupList(BaseModel):
    groups: list[DocumentGroupPublic]


class DocumentGroupFilter(BaseModel):
    q: Optional[str] = None
    offset: int = 0
    limit: int = 100
