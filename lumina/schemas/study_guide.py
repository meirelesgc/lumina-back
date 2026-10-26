from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from lumina.schemas.study_attachment import StudyAttachmentPublic


class StudyGuideAttachment(StudyAttachmentPublic):
    studied: bool
    studied_at: Optional[datetime] = None


class StudyGuideItem(BaseModel):
    id: UUID
    name: str
    icon_path: Optional[str] = None
    position: int
    attachments: list[StudyGuideAttachment]


class StudyGuideGroup(BaseModel):
    id: UUID
    name: str


class StudyGuidePublic(BaseModel):
    project_id: UUID
    document_group: Optional[StudyGuideGroup] = None
    items: list[StudyGuideItem] = []
    total_attachments: int = 0
    studied_attachments: int = 0
