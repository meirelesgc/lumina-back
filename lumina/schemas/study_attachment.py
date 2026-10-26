from datetime import datetime
from enum import Enum
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, model_validator

from lumina.services.crossref_client import normalize_doi


class StudyAttachmentKind(str, Enum):
    TYPIFICATION = 'TYPIFICATION'
    DOI = 'DOI'
    LINK = 'LINK'


class StudyAttachmentSchema(BaseModel):
    kind: StudyAttachmentKind
    description: Optional[str] = None
    title: Optional[str] = None
    typification_id: Optional[UUID] = None
    doi: Optional[str] = None
    url: Optional[str] = None

    @model_validator(mode='after')
    def check_kind_fields(self):
        if self.kind == StudyAttachmentKind.DOI:
            doi = normalize_doi(self.doi or '')
            if not doi:
                raise ValueError('doi must look like 10.1234/suffix')
            self.doi = doi
        if self.kind == StudyAttachmentKind.LINK:
            if not (self.title or '').strip():
                raise ValueError('title is required for a link')
            parsed = urlparse(self.url or '')
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                raise ValueError('url must use http or https')
        return self


class StudyAttachmentCreate(StudyAttachmentSchema):
    pass


class StudyAttachmentUpdate(StudyAttachmentSchema):
    id: UUID


class StudyAttachmentOrder(BaseModel):
    attachment_ids: list[UUID]


class TypificationRef(BaseModel):
    id: UUID
    name: str


class StudyAttachmentPublic(BaseModel):
    id: UUID
    document_group_item_id: UUID
    kind: StudyAttachmentKind
    position: int
    description: Optional[str] = None
    title: Optional[str] = None
    typification: Optional[TypificationRef] = None
    doi: Optional[str] = None
    doi_url: Optional[str] = None
    authors: list[str] = []
    year: Optional[int] = None
    container_title: Optional[str] = None
    metadata_source: Optional[str] = None
    url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
