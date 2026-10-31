from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from lumina.schemas.common import FilterPage


class BranchFilter(FilterPage):
    taxonomy_id: Optional[UUID] = None
    q: Optional[str] = None


class SectionRequirementScope(str, Enum):
    SPECIFIC_SECTION = 'SPECIFIC_SECTION'
    ENTIRE_DOCUMENT = 'ENTIRE_DOCUMENT'
    UNKNOWN = 'UNKNOWN'


class BranchSchema(BaseModel):
    title: str
    description: str


class BranchSectionMarking(BaseModel):
    """
    Marcação do escopo de seção feita pelo configurador. Só
    `SPECIFIC_SECTION` leva `expected_section`, e ela não pode ser vazia.
    """

    section_scope: Optional[SectionRequirementScope] = None
    expected_section: Optional[str] = None

    @model_validator(mode='after')
    def check_marking(self):
        if self.expected_section is not None:
            self.expected_section = self.expected_section.strip() or None
        if 'section_scope' not in self.model_fields_set:
            if 'expected_section' in self.model_fields_set:
                raise ValueError('expected_section exige section_scope')
            return self
        specific = (
            self.section_scope == SectionRequirementScope.SPECIFIC_SECTION
        )
        if specific and not self.expected_section:
            raise ValueError('SPECIFIC_SECTION exige expected_section')
        if not specific and self.expected_section:
            raise ValueError(
                'expected_section só vale com SPECIFIC_SECTION'
            )
        return self


class BranchCreate(BranchSchema, BranchSectionMarking):
    taxonomy_id: UUID
    section_scope: SectionRequirementScope = SectionRequirementScope.UNKNOWN


class BranchUpdate(BranchSchema, BranchSectionMarking):
    """Omitir `section_scope` mantém a marcação atual do ramo."""

    id: UUID
    taxonomy_id: UUID


class BranchPublic(BranchSchema):
    id: UUID
    taxonomy_id: UUID
    section_scope: SectionRequirementScope = SectionRequirementScope.UNKNOWN
    expected_section: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BranchList(BaseModel):
    branches: list[BranchPublic]
