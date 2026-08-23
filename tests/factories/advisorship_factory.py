from datetime import datetime
from uuid import uuid4

import factory

from lumina.models import Advisorship


class AdvisorshipFactory(factory.Factory):
    class Meta:
        model = Advisorship

    id = factory.LazyFunction(uuid4)
    advisor_id = factory.LazyFunction(uuid4)
    advisee_id = factory.LazyFunction(uuid4)
    project_id = None
    role_type = 'MAIN_ADVISOR'
    topic = factory.Sequence(lambda n: f'Tema de Pesquisa {n}')
    status = 'ACTIVE'

    @factory.post_generation
    def created_at(obj, create, extracted, **kwargs):
        if not getattr(obj, 'created_at', None):
            obj.created_at = datetime.utcnow()
