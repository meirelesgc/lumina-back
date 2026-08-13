import factory

from lumina.models import Source, Typification


class SourceFactory(factory.Factory):
    class Meta:
        model = Source

    name = factory.Sequence(lambda n: f'Source {n}')
    description = factory.Sequence(lambda n: f'Description {n}')


class TypificationFactory(factory.Factory):
    class Meta:
        model = Typification

    name = factory.Sequence(lambda n: f'Typification {n}')
