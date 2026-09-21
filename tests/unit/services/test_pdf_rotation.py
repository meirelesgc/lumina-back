# ruff: noqa: PLR2004
import fitz

from lumina.services.ai.stages.extraction import extract_pdf_chunks


def test_extract_pdf_with_rotated_page(tmp_path):
    """
    Garante que páginas rotacionadas (ex: 90 graus) são processadas
    corretamente sem quebras de coordenadas ou layout.
    """
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.set_rotation(90)
    page.insert_text(
        (100, 200), '# Título em Página Rotacionada\n\nConteúdo.', rotate=90
    )

    pdf_path = tmp_path / 'rotated.pdf'
    doc.save(str(pdf_path))
    doc.close()

    chunks, pages_count, null_bytes, ws_ops = extract_pdf_chunks(
        str(pdf_path), 'rotated.pdf'
    )

    assert pages_count == 1
    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert first_chunk.metadata['page'] == 0
    assert 'rects' in first_chunk.metadata
    assert len(first_chunk.metadata['rects']) > 0
    # Valida formato [x0, y0, x1, y1]
    r = first_chunk.metadata['rects'][0]
    assert len(r) == 4
    assert all(isinstance(v, float) for v in r)
