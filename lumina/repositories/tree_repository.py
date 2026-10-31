from sqlalchemy import select

from lumina.core.dependencies import Session
from lumina.models import (
    Document,
    DocumentRelease,
    DocumentTypification,
    Typification,
)


async def get_tree_by_release(session: Session, release: DocumentRelease):
    query = await session.scalars(
        select(Typification)
        .join(
            DocumentTypification,
            Typification.id == DocumentTypification.typification_id,
        )
        .join(Document, Document.id == DocumentTypification.document_id)
        .join(DocumentRelease, DocumentRelease.document_id == Document.id)
        .where(
            DocumentRelease.id == release.id,
            Typification.deleted_at.is_(None),
        )
    )
    tree = query.all()
    return tree
