from uuid import uuid4

import pytest

from lumina.services.ai.tree_suggestion import (
    ExistingBranch,
    ExistingTaxonomy,
    ExistingTree,
    TreeSuggestionGenerationError,
    generate_tree_suggestions,
)
from lumina.services.ai.tree_suggestion.structures import (
    ConsolidatedBranch,
    ConsolidatedTaxonomy,
    ConsolidationResult,
    RuleBatchResult,
)
from tests.factories.tree_suggestion_factory import (
    DISSERTATION,
    TCC,
    FakeStructuredModel,
    build_normative_pdf,
    default_create_responses,
    rule,
)


@pytest.fixture
def pdf_path(tmp_path):
    return str(build_normative_pdf(tmp_path / 'regulamento.pdf'))


def _by_kind(nodes, kind):
    return [n for n in nodes if n.kind == kind]


@pytest.mark.asyncio
async def test_create_mode_builds_multiple_typifications(pdf_path):
    existing_tcc = uuid4()
    model = FakeStructuredModel(default_create_responses())

    result = await generate_tree_suggestions(
        pdf_path,
        'create',
        ExistingTree(
            typification_names=[
                (existing_tcc, 'Trabalho de conclusão de curso')
            ]
        ),
        model=model,
        fast_model=model,
    )

    kinds = [n.kind for n in result.nodes]
    assert kinds[0] == 'source'
    assert kinds.count('source') == 1
    typifications = _by_kind(result.nodes, 'typification')
    assert [t.title for t in typifications] == [TCC, DISSERTATION]
    assert typifications[0].similar_to_id == existing_tcc
    assert result.page_count == 3  # noqa: PLR2004
    assert result.model_name == 'fake-model'

    keys = {n.key: n for n in result.nodes}
    for node in _by_kind(result.nodes, 'taxonomy'):
        assert keys[node.parent_key].kind == 'typification'
    for node in _by_kind(result.nodes, 'branch'):
        assert keys[node.parent_key].kind == 'taxonomy'


@pytest.mark.asyncio
async def test_create_mode_evidence_is_verified_with_pages(pdf_path):
    model = FakeStructuredModel(default_create_responses())

    result = await generate_tree_suggestions(
        pdf_path, 'create', ExistingTree(), model=model, fast_model=model
    )

    branches = {n.title: n for n in _by_kind(result.nodes, 'branch')}
    assert 'Espaçamento duplo' not in branches
    assert branches['Fonte Arial 12'].evidence[0]['pages'] == [2]
    assert branches['Resumo com até 500 palavras'].evidence[0]['pages'] == [3]
    for node in result.nodes:
        if node.kind != 'source':
            assert node.evidence, node.title
    assert result.stats['evidence'] == {'accepted': 3, 'dropped': 1}


@pytest.mark.asyncio
async def test_enrich_mode_proposes_creates_and_updates_only(pdf_path):
    typification_id = uuid4()
    formatting = ExistingTaxonomy(
        id=uuid4(),
        title='Formatação',
        description='Regras de formatação.',
        branches=[
            ExistingBranch(id=uuid4(), title='Fonte', description='Fonte.')
        ],
    )
    untouched = ExistingTaxonomy(
        id=uuid4(), title='Referências', description='ABNT.'
    )
    existing = ExistingTree(
        typification_id=typification_id,
        typification_name=TCC,
        taxonomies=[formatting, untouched],
    )
    responses = default_create_responses()
    responses[RuleBatchResult] = RuleBatchResult(
        rules=[
            rule(
                TCC,
                'Formatação',
                'Fonte Arial 12',
                'O texto deve ser digitado em fonte Arial tamanho 12.',
            ),
            rule(
                TCC,
                'Formatação',
                'Margens',
                'As margens superior e esquerda devem ter 3 cm.',
            ),
            rule(
                TCC,
                'Elementos pré-textuais',
                'Resumo com até 500 palavras',
                'O resumo deve conter no máximo 500 palavras.',
            ),
        ]
    )
    responses[ConsolidationResult] = ConsolidationResult(
        taxonomies=[
            ConsolidatedTaxonomy(
                title='Formatação',
                description='Regras de formatação.',
                decision='same',
                existing_id='T1',
                branches=[
                    ConsolidatedBranch(
                        title='Fonte Arial 12',
                        description='Fonte Arial tamanho 12.',
                        candidate_ids=[1],
                        decision='update',
                        existing_id='B1',
                    ),
                    ConsolidatedBranch(
                        title='Margens de 3 cm',
                        description='Superior e esquerda.',
                        candidate_ids=[2],
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
                        candidate_ids=[3],
                    )
                ],
            ),
        ]
    )
    model = FakeStructuredModel(responses)

    result = await generate_tree_suggestions(
        pdf_path, 'enrich', existing, model=model, fast_model=model
    )

    assert _by_kind(result.nodes, 'typification') == []
    assert {n.operation for n in result.nodes} <= {'create', 'update'}
    assert untouched.id not in {n.target_entity_id for n in result.nodes}

    branches = {n.title: n for n in _by_kind(result.nodes, 'branch')}
    update = branches['Fonte Arial 12']
    assert update.operation == 'update'
    assert update.target_entity_id == formatting.branches[0].id
    assert branches['Margens de 3 cm'].parent_entity_id == formatting.id

    (new_taxonomy,) = _by_kind(result.nodes, 'taxonomy')
    assert new_taxonomy.parent_entity_id == typification_id
    assert branches['Resumo com até 500 palavras'].parent_key == (
        new_taxonomy.key
    )


@pytest.mark.asyncio
async def test_invalid_existing_reference_becomes_new(pdf_path):
    responses = default_create_responses()
    responses[ConsolidationResult] = ConsolidationResult(
        taxonomies=[
            ConsolidatedTaxonomy(
                title='Formatação',
                description='Regras.',
                decision='update',
                existing_id='T42',
                branches=[
                    ConsolidatedBranch(
                        title='Fonte Arial 12',
                        description='Fonte.',
                        candidate_ids=[1],
                    )
                ],
            )
        ]
    )
    model = FakeStructuredModel(responses)
    existing = ExistingTree(typification_id=uuid4(), typification_name=TCC)

    result = await generate_tree_suggestions(
        pdf_path, 'enrich', existing, model=model, fast_model=model
    )

    (taxonomy,) = _by_kind(result.nodes, 'taxonomy')
    assert taxonomy.operation == 'create'
    assert taxonomy.target_entity_id is None


@pytest.mark.asyncio
async def test_all_rule_batches_failing_raises(pdf_path):
    responses = default_create_responses()
    responses[RuleBatchResult] = RuntimeError('LLM indisponível')
    model = FakeStructuredModel(responses)

    with pytest.raises(TreeSuggestionGenerationError):
        await generate_tree_suggestions(
            pdf_path, 'create', ExistingTree(), model=model, fast_model=model
        )
