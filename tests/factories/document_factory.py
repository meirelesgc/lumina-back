import factory
from lumina.models import DocumentGroup, DocumentGroupItem, Project, ProjectDocument

class DocumentGroupFactory(factory.Factory):
    class Meta:
        model = DocumentGroup

    name = factory.Sequence(lambda n: f'Group {n}')

class DocumentGroupItemFactory(factory.Factory):
    class Meta:
        model = DocumentGroupItem

    name = factory.Sequence(lambda n: f'Item {n}')
    group_id = None

class ProjectFactory(factory.Factory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: f'Project {n}')
    description = factory.Sequence(lambda n: f'Description {n}')
    status = 'INICIADO'

class ProjectDocumentFactory(factory.Factory):
    class Meta:
        model = ProjectDocument

    name = factory.Sequence(lambda n: f'Doc {n}')
    status = 'PENDING'
    type = 'PDF'
    project_id = None
