from langchain_core.documents import Document

from lumina.services.ai.stages.contextualization import (
    DocumentMetadata,
    generate_chunk_context,
)
from lumina.services.ai.stages.section_models import Heading, Section


def test_generate_chunk_context_is_a_no_op_mock():
    chunk = Document(page_content='Texto do chunk', metadata={})
    section = Section(
        heading=Heading(
            line_number=1, level=1, title='Objeto', raw='# Objeto', page=0
        ),
    )
    document_metadata = DocumentMetadata(source_name='doc.pdf')

    result = generate_chunk_context(chunk, section, document_metadata)

    assert result is None
