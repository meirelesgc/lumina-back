from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lumina.schemas.common import FilterPage


class PublicationTemplateSchema(BaseModel):
    name: str


class PublicationTemplateCreate(PublicationTemplateSchema):
    pass


class PublicationTemplateUpdate(BaseModel):
    id: UUID
    name: Optional[str] = None


class PublicationTemplatePublic(PublicationTemplateSchema):
    id: UUID
    original_filename: str
    file_path: str

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PublicationTemplateList(BaseModel):
    templates: list[PublicationTemplatePublic]


class PublicationTemplateFilter(FilterPage):
    q: Optional[str] = None
