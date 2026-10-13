# Retrieval evaluation

Cases that check what the engine retrieves from a document for a branch of
the check tree (`lumina/services/ai/stages/retrieval.py`).

The documents live in `tests/fixtures/documents/`. Each case points to a PDF
by its path relative to that folder and never copies it.

Tests in this folder call real models and use the `@pytest.mark.ai` marker.
Run them with `poetry run task test-ai`.

Each case comes from a `<name>.retrieval.yaml` answer key next to the PDF and
a branch from `tests/fixtures/documents/retrieval_branches.yaml`. See
"Expected retrieval" in `tests/fixtures/documents/README.md` for how to
annotate them.
