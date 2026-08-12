import factory
from lumina.models import Taxonomy, Typification

class TypificationFactory(factory.Factory):
    class Meta:
        model = Typification

    name = factory.Sequence(lambda n: f'Typification {n}')

class TaxonomyFactory(factory.Factory):
    class Meta:
        model = Taxonomy

    title = factory.Sequence(lambda n: f'Taxonomy {n}')
    description = factory.Sequence(lambda n: f'Description {n}')
    # Note: typification_id should be provided when creating the instance
