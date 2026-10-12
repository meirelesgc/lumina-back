# Retrieval evaluation

Cases that check what the engine retrieves from a document for a branch of
the check tree (`lumina/services/ai/stages/retrieval.py`).

The documents live in `tests/fixtures/documents/`. Each case points to a PDF
by its path relative to that folder and never copies it.

Tests in this folder call real models and use the `@pytest.mark.ai` marker.
Run them with `poetry run task test-ai`.
