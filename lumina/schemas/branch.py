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


class ExpansionType(str, Enum):
    PARAPHRASE = 'paraphrase'
    SUB_QUESTION = 'sub_question'
    SECTION_HINT = 'section_hint'


class QueryExpansionItem(BaseModel):
    expansion_text: str = Field(
        description='Formulação alternativa da consulta do critério.'
    )
    expansion_type: ExpansionType = Field(
        description=(
            'Classificação da expansão: paraphrase, sub_question ou '
            'section_hint.'
        )
    )


class QueryExpansionList(BaseModel):
    expansions: list[QueryExpansionItem] = Field(
        default_factory=list,
        description='2 a 4 formulações alternativas geradas para o critério.',
    )
