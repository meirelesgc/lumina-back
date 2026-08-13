import factory

from lumina.models import Source


class SourceFactory(factory.Factory):
    class Meta:
        model = Source

    name = factory.Sequence(lambda n: f'Source {n}')
    description = factory.Sequence(lambda n: f'Description {n}')
