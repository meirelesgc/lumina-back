import factory
from lumina.models import Project
from datetime import datetime

class ProjectFactory(factory.Factory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: f"Project {n}")
    description = factory.Sequence(lambda n: f"Description for Project {n}")
    status = "INICIADO"
    
    @factory.post_generation
    def id(obj, create, extracted, **kwargs):
        if extracted:
            obj.id = extracted
            
    @factory.post_generation
    def created_at(obj, create, extracted, **kwargs):
        if not obj.created_at:
            obj.created_at = datetime.utcnow()
