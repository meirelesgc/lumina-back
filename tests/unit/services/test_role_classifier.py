from lumina.services.ai.stages.section_models import (
    Heading,
    Section,
    SectionRole,
)
from lumina.services.ai.stages.sections import (
    AliasRoleClassifier,
    PositionalAbstractFallbackClassifier,
    classify_section_roles,
)


def _make_sec(title: str, level: int = 1) -> Section:
    return Section(
        heading=Heading(
            line_number=1, level=level, title=title, raw=f'# {title}'
        )
    )


def test_alias_role_classifier_portuguese():
    sections = [
        _make_sec('Resumo'),
        _make_sec('1. Introdução'),
        _make_sec('Materiais e Métodos'),
        _make_sec('3. Resultados'),
        _make_sec('4. Discussão'),
        _make_sec('Conclusão'),
        _make_sec('Referências Bibliográficas'),
        _make_sec('Cronograma Financeiro'),
    ]
    classifier = AliasRoleClassifier()
    classifier.classify(sections)

    assert sections[0].role == SectionRole.ABSTRACT
    assert sections[1].role == SectionRole.INTRODUCTION
    assert sections[2].role == SectionRole.METHODOLOGY
    assert sections[3].role == SectionRole.RESULTS
    assert sections[4].role == SectionRole.DISCUSSION
    assert sections[5].role == SectionRole.CONCLUSION
    assert sections[6].role == SectionRole.REFERENCES
    assert sections[7].role == SectionRole.UNKNOWN


def test_alias_role_classifier_english():
    sections = [
        _make_sec('Abstract'),
        _make_sec('1. Introduction'),
        _make_sec('Methods'),
        _make_sec('Results and Discussion'),
        _make_sec('Conclusions'),
        _make_sec('References'),
    ]
    classifier = AliasRoleClassifier()
    classifier.classify(sections)

    assert sections[0].role == SectionRole.ABSTRACT
    assert sections[1].role == SectionRole.INTRODUCTION
    assert sections[2].role == SectionRole.METHODOLOGY
    assert sections[3].role == SectionRole.RESULTS
    assert sections[4].role == SectionRole.CONCLUSION
    assert sections[5].role == SectionRole.REFERENCES


def test_positional_abstract_fallback():
    # Artigo científico onde o abstract não tem heading explícito
    sections = [
        _make_sec('Título do Artigo com Autores'),
        _make_sec('Este é o texto implícito do resumo'),
        _make_sec('1. Introdução'),
        _make_sec('2. Métodos'),
    ]
    sections[2].role = SectionRole.INTRODUCTION

    fallback = PositionalAbstractFallbackClassifier()
    fallback.classify(sections)

    assert sections[1].role == SectionRole.ABSTRACT
    assert sections[1].role_confidence == 'positional_fallback'
    assert sections[0].role == SectionRole.TITLE_BLOCK


def test_classify_section_roles_pipeline():
    sections = [
        _make_sec('Título do Trabalho'),
        _make_sec('Resumo dos autores'),
        _make_sec('Introdução'),
    ]
    classify_section_roles(sections)

    assert sections[1].role == SectionRole.ABSTRACT
    assert sections[2].role == SectionRole.INTRODUCTION
