from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from lumina.schemas.common import FilterPage


class BranchFilter(FilterPage):
    taxonomy_id: Optional[UUID] = None
    q: Optional[str] = None


class BranchSchema(BaseModel):
    title: str
    description: str


class BranchCreate(BranchSchema):
    taxonomy_id: UUID


class BranchUpdate(BranchSchema):
    id: UUID
    taxonomy_id: UUID


class BranchPublic(BranchSchema):
    id: UUID
    taxonomy_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BranchList(BaseModel):
    branches: list[BranchPublic]


class SectionRequirementScope(str, Enum):
    SPECIFIC_SECTION = 'SPECIFIC_SECTION'
    ENTIRE_DOCUMENT = 'ENTIRE_DOCUMENT'
    UNKNOWN = 'UNKNOWN'


class BranchSectionRequirement(BaseModel):
    scope: SectionRequirementScope = Field(
        description=(
            'Escopo de busca: SPECIFIC_SECTION, ENTIRE_DOCUMENT ou UNKNOWN.'
        )
    )
    expected_section: Optional[str] = Field(
        default=None,
        description=(
            'Nome sugerido da seção específica '
            '(se scope for SPECIFIC_SECTION).'
        ),
    )
    reasoning: Optional[str] = Field(
        default=None,
        description='Justificativa técnica concisa do modelo.',
    )
