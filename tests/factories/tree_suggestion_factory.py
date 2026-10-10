from pathlib import Path
from typing import Any, Callable, Dict, Union

import pymupdf

from lumina.services.ai.tree_suggestion.structures import (
    ConsolidatedBranch,
    ConsolidatedTaxonomy,
    ConsolidationResult,
    RuleBatchResult,
    RuleCandidate,
    ScopeDocumentType,
    ScopeResult,
)

NORMATIVE_PAGES = [
    (
        'Regulamento de Trabalhos Acadêmicos\n\n'
        'Art. 1 Este regulamento estabelece as normas para elaboração de '
        'Trabalhos de Conclusão de Curso e Dissertações de Mestrado.'
    ),
    (
        'Capítulo II Da Formatação\n\n'
        'Art. 2 O texto deve ser digitado em fonte Arial tamanho 12.\n'
        'Art. 3 As margens superior e esquerda devem ter 3 cm.'
    ),
    (
        'Capítulo III Dos Elementos Pré-Textuais\n\n'
        'Art. 4 O resumo deve conter no máximo 500 palavras.\n'
        'Art. 5 A dissertação deve apresentar abstract em língua inglesa.'
    ),
]


def build_normative_pdf(path: Path, pages=NORMATIVE_PAGES) -> Path:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=11)
    doc.save(str(path))
    doc.close()
    return path


Response = Union[Any, Callable[[str], Any], Exception]


class _Structured:
    def __init__(self, model: 'FakeStructuredModel', schema):
        self.model = model
        self.schema = schema

    async def ainvoke(self, prompt: str):
        self.model.prompts.setdefault(self.schema, []).append(prompt)
        response = self.model.responses[self.schema]
        if isinstance(response, Exception):
            raise response
        return response(prompt) if callable(response) else response


class FakeStructuredModel:
    """Modelo fake: responde por schema de saída estruturada."""

    model_name = 'fake-model'

    def __init__(self, responses: Dict[Any, Response]):
        self.responses = responses
        self.prompts: Dict[Any, list] = {}

    def with_structured_output(self, schema):
        return _Structured(self, schema)


def rule(  # noqa: PLR0913, PLR0917
    document_type: str,
    taxonomy: str,
    branch: str,
    quote: str,
    description: str = 'Verificar a regra.',
) -> RuleCandidate:
    return RuleCandidate(
        document_type=document_type,
        taxonomy_title=taxonomy,
        taxonomy_description=f'Regras de {taxonomy.lower()}.',
        branch_title=branch,
        branch_description=description,
        quote=quote,
        rationale='Trecho define a obrigação.',
    )


TCC = 'Trabalho de Conclusão de Curso'
DISSERTATION = 'Dissertação de Mestrado'


def default_create_responses() -> Dict[Any, Response]:
    """Respostas coerentes com NORMATIVE_PAGES para o modo 'create'."""
    scope = ScopeResult(
        source_name='Regulamento de Trabalhos Acadêmicos',
        source_description='Normas para elaboração de trabalhos acadêmicos.',
        document_types=[
            ScopeDocumentType(name=TCC, description='Trabalho de graduação.'),
            ScopeDocumentType(name=DISSERTATION, description='Mestrado.'),
        ],
    )
    rules = RuleBatchResult(
        rules=[
            rule(
                TCC,
                'Formatação',
                'Fonte Arial 12',
                'O texto deve ser digitado em fonte Arial tamanho 12.',
            ),
            rule(
                TCC,
                'Elementos pré-textuais',
                'Resumo com até 500 palavras',
                'O resumo deve conter no máximo 500 palavras.',
            ),
            rule(
                DISSERTATION,
                'Elementos pré-textuais',
                'Abstract em inglês',
                'A dissertação deve apresentar abstract em língua inglesa.',
            ),
            rule(
                TCC,
                'Formatação',
                'Espaçamento duplo',
                'O espaçamento entre linhas deve ser duplo.',
            ),
        ]
    )

    def consolidation(prompt: str) -> ConsolidationResult:
        if DISSERTATION in prompt.split('\n', 2)[0]:
            return ConsolidationResult(
                taxonomies=[
                    ConsolidatedTaxonomy(
                        title='Elementos pré-textuais',
                        description='Elementos antes do texto.',
                        branches=[
                            ConsolidatedBranch(
                                title='Abstract em inglês',
                                description='Verificar abstract.',
                                candidate_ids=[3],
                            )
                        ],
                    )
                ]
            )
        return ConsolidationResult(
            taxonomies=[
                ConsolidatedTaxonomy(
                    title='Formatação',
                    description='Regras de formatação.',
                    branches=[
                        ConsolidatedBranch(
                            title='Fonte Arial 12',
                            description='Verificar fonte.',
                            candidate_ids=[1],
                        ),
                        ConsolidatedBranch(
                            title='Espaçamento duplo',
                            description='Sem evidência válida.',
                            candidate_ids=[99],
                        ),
                    ],
                ),
                ConsolidatedTaxonomy(
                    title='Elementos pré-textuais',
                    description='Elementos antes do texto.',
                    branches=[
                        ConsolidatedBranch(
                            title='Resumo com até 500 palavras',
                            description='Verificar resumo.',
                            candidate_ids=[2],
                        )
                    ],
                ),
            ]
        )

    return {
        ScopeResult: scope,
        RuleBatchResult: rules,
        ConsolidationResult: consolidation,
    }
