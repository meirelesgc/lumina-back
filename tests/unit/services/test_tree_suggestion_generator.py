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
    ESTRUTURA,
    INTRODUCAO,
    METODOLOGIA,
    RESUMO,
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


async def _generate(pdf_path, responses, mode='create', existing=None):
    model = FakeStructuredModel(responses)
    return await generate_tree_suggestions(
        pdf_path,
        mode,
        existing or ExistingTree(),
        model=model,
        fast_model=model,
    )


@pytest.mark.asyncio
async def test_create_mode_builds_multiple_typifications(pdf_path):
    existing_tcc = uuid4()

    result = await _generate(
        pdf_path,
        default_create_responses(),
        existing=ExistingTree(
            typification_names=[
                (existing_tcc, 'Trabalho de conclusão de curso')
            ]
        ),
    )

    kinds = [n.kind for n in result.nodes]
    assert kinds[0] == 'source'
    assert kinds.count('source') == 1
    typifications = _by_kind(result.nodes, 'typification')
    assert [t.title for t in typifications] == [TCC, DISSERTATION]
    assert typifications[0].similar_to_id == existing_tcc
    assert result.page_count == 4  # noqa: PLR2004
    assert result.model_name == 'fake-model'

    keys = {n.key: n for n in result.nodes}
    for node in _by_kind(result.nodes, 'taxonomy'):
        assert keys[node.parent_key].kind == 'typification'
    for node in _by_kind(result.nodes, 'branch'):
        assert keys[node.parent_key].kind == 'taxonomy'


@pytest.mark.asyncio
async def test_create_mode_evidence_is_verified_with_pages(pdf_path):
    result = await _generate(pdf_path, default_create_responses())

    branches = {n.title: n for n in _by_kind(result.nodes, 'branch')}
    assert 'Aprovação pelo comitê de ética' not in branches
    assert branches[INTRODUCAO].evidence[0]['pages'] == [4]
    assert branches[RESUMO].evidence[0]['pages'] == [3]
    for node in result.nodes:
        if node.kind != 'source':
            assert node.evidence, node.title
    assert result.stats['evidence']['accepted'] == 3  # noqa: PLR2004
    assert result.stats['evidence']['dropped'] == 1


@pytest.mark.asyncio
async def test_formatting_rules_are_excluded_and_reported(pdf_path):
    result = await _generate(pdf_path, default_create_responses())

    titles = {n.title for n in result.nodes}
    assert not titles & {'Fonte Arial 12', 'Margens de 3 cm', 'Formatação'}
    assert result.excluded_rules == [
        {
            'title': 'Fonte Arial 12',
            'quote': 'O texto deve ser digitado em fonte Arial tamanho 12.',
            'pages': [2],
        },
        {
            'title': 'Margens de 3 cm',
            'quote': 'As margens superior e esquerda devem ter 3 cm.',
            'pages': [2],
        },
    ]
    assert result.stats['rules']['formatting'] == 4  # noqa: PLR2004
    assert result.stats['evidence']['excluded'] == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_formatting_rules_never_reach_consolidation(pdf_path):
    responses = default_create_responses()
    model = FakeStructuredModel(responses)

    await generate_tree_suggestions(
        pdf_path, 'create', ExistingTree(), model=model, fast_model=model
    )

    prompts = ' '.join(model.prompts[ConsolidationResult])
    assert 'Fonte Arial 12' not in prompts
    assert 'Margens' not in prompts


@pytest.mark.asyncio
async def test_same_passage_splits_content_and_formatting(pdf_path):
    quote = 'O resumo deve conter no máximo 500 palavras.'
    responses = default_create_responses()
    responses[RuleBatchResult] = RuleBatchResult(
        rules=[
            rule(TCC, 'Elementos pré-textuais', RESUMO, quote),
            rule(
                TCC,
                'Formatação',
                'Resumo em espaçamento simples',
                quote,
                rule_type='formatting',
            ),
        ]
    )
    responses[ConsolidationResult] = ConsolidationResult(
        taxonomies=[
            ConsolidatedTaxonomy(
                title='Elementos pré-textuais',
                description='Elementos antes do texto.',
                branches=[
                    ConsolidatedBranch(
                        title=RESUMO, description='Resumo.', candidate_ids=[1]
                    )
                ],
            )
        ]
    )

    result = await _generate(pdf_path, responses)

    assert [n.title for n in _by_kind(result.nodes, 'branch')] == [RESUMO]
    assert [r['title'] for r in result.excluded_rules] == [
        'Resumo em espaçamento simples'
    ]


@pytest.mark.asyncio
async def test_enrich_mode_proposes_creates_and_updates_only(pdf_path):
    typification_id = uuid4()
    structure = ExistingTaxonomy(
        id=uuid4(),
        title=ESTRUTURA,
        description='Seções obrigatórias do trabalho.',
        branches=[
            ExistingBranch(
                id=uuid4(), title='Introdução', description='Introdução.'
            )
        ],
    )
    untouched = ExistingTaxonomy(
        id=uuid4(), title='Referências', description='ABNT.'
    )
    existing = ExistingTree(
        typification_id=typification_id,
        typification_name=TCC,
        taxonomies=[structure, untouched],
    )
    responses = default_create_responses()
    responses[RuleBatchResult] = RuleBatchResult(
        rules=[
            rule(
                TCC,
                ESTRUTURA,
                INTRODUCAO,
                'A introdução deve apresentar o objetivo geral do trabalho.',
            ),
            rule(
                TCC,
                ESTRUTURA,
                METODOLOGIA,
                'A metodologia deve descrever os procedimentos de coleta de '
                'dados.',
            ),
            rule(
                TCC,
                'Elementos pré-textuais',
                RESUMO,
                'O resumo deve conter no máximo 500 palavras.',
            ),
        ]
    )
    responses[ConsolidationResult] = ConsolidationResult(
        taxonomies=[
            ConsolidatedTaxonomy(
                title=ESTRUTURA,
                description='Seções obrigatórias do trabalho.',
                decision='same',
                existing_id='T1',
                branches=[
                    ConsolidatedBranch(
                        title=INTRODUCAO,
                        description='Verificar o objetivo geral.',
                        candidate_ids=[1],
                        decision='update',
                        existing_id='B1',
                    ),
                    ConsolidatedBranch(
                        title=METODOLOGIA,
                        description='Verificar procedimentos.',
                        candidate_ids=[2],
                    ),
                ],
            ),
            ConsolidatedTaxonomy(
                title='Elementos pré-textuais',
                description='Elementos antes do texto.',
                branches=[
                    ConsolidatedBranch(
                        title=RESUMO,
                        description='Verificar resumo.',
                        candidate_ids=[3],
                    )
                ],
            ),
        ]
    )

    result = await _generate(pdf_path, responses, 'enrich', existing)

    assert _by_kind(result.nodes, 'typification') == []
    assert {n.operation for n in result.nodes} <= {'create', 'update'}
    assert untouched.id not in {n.target_entity_id for n in result.nodes}

    branches = {n.title: n for n in _by_kind(result.nodes, 'branch')}
    update = branches[INTRODUCAO]
    assert update.operation == 'update'
    assert update.target_entity_id == structure.branches[0].id
    assert branches[METODOLOGIA].parent_entity_id == structure.id

    (new_taxonomy,) = _by_kind(result.nodes, 'taxonomy')
    assert new_taxonomy.parent_entity_id == typification_id
    assert branches[RESUMO].parent_key == new_taxonomy.key


@pytest.mark.asyncio
async def test_invalid_existing_reference_becomes_new(pdf_path):
    responses = default_create_responses()
    responses[ConsolidationResult] = ConsolidationResult(
        taxonomies=[
            ConsolidatedTaxonomy(
                title=ESTRUTURA,
                description='Seções.',
                decision='update',
                existing_id='T42',
                branches=[
                    ConsolidatedBranch(
                        title=INTRODUCAO,
                        description='Objetivo.',
                        candidate_ids=[3],
                    )
                ],
            )
        ]
    )
    existing = ExistingTree(typification_id=uuid4(), typification_name=TCC)

    result = await _generate(pdf_path, responses, 'enrich', existing)

    (taxonomy,) = _by_kind(result.nodes, 'taxonomy')
    assert taxonomy.operation == 'create'
    assert taxonomy.target_entity_id is None


@pytest.mark.asyncio
async def test_all_rule_batches_failing_raises(pdf_path):
    responses = default_create_responses()
    responses[RuleBatchResult] = RuntimeError('LLM indisponível')

    with pytest.raises(TreeSuggestionGenerationError):
        await _generate(pdf_path, responses)
