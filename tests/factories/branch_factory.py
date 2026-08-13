import factory

from lumina.models import Branch, Taxonomy, Typification


class TypificationFactory(factory.Factory):
    class Meta:
        model = Typification

    name = factory.Sequence(lambda n: f'Typification {n}')


class TaxonomyFactory(factory.Factory):
    class Meta:
        model = Taxonomy

    title = factory.Sequence(lambda n: f'Taxonomy {n}')
    description = factory.Sequence(lambda n: f'Description {n}')


class BranchFactory(factory.Factory):
    class Meta:
        model = Branch

    title = factory.Sequence(lambda n: f'Branch {n}')
    description = factory.Sequence(lambda n: f'Branch Description {n}')
