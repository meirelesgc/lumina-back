from iaEditais.repositories import release_repo


async def get_releases_by_document(session, doc_id):
    return await release_repo.get_releases_by_document(session, doc_id)


async def get_release_with_details(session, release_id):
    return await release_repo.get_release_with_details(session, release_id)
