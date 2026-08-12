from lumina.core.dependencies import Session
from lumina.models import DocumentRelease
from lumina.repositories import tree_repository


async def get_tree_by_release(session: Session, release: DocumentRelease):
    return await tree_repository.get_tree_by_release(session, release)
