# Test documents

Shared corpus of PDFs used by tests. Each file lives here once. Tests point
to it by its path relative to this folder, for example
`systematic_review/dengue_no_brasil.pdf`. Do not copy these files into test
folders.

| Folder | Document type |
| :--- | :--- |
| `article/` | Article |
| `systematic_review/` | Systematic review |
| `research_proposal/` | Research proposal (anteprojeto) |
| `technical_report/` | Technical report |

## Expected sections

Next to each PDF, a `<name>.sections.yaml` file lists the sections and
subsections the engine must index:

```
systematic_review/
├── dengue_no_brasil.pdf
└── dengue_no_brasil.sections.yaml
```

Start from `section_template.yaml`. The file describes the document, so any
test can reuse it.

## Adding a document

1. Add the PDF and its `<name>.sections.yaml` to the folder of its type.
2. Run `poetry run pytest tests/unit/services/test_ingestion_sections.py -s`.
   The test finds every answer key on its own; no new test code is needed.
3. Read the result:
   - **Text check fails:** the ingestion loses text. Open an OpenSpec change
     with this failing test as its acceptance criterion.
   - **Section score below the floor:** improve the heading detection in an
     OpenSpec change, or lower `MIN_SECTION_IDENTIFICATION_RATE` with the
     reason recorded in the change.
   - **All green:** the document now guards the ingestion against
     regressions.

The floor only goes up: whoever improves the heuristic raises it in the same
commit. See "Validação da Ingestão sobre Acervo Anotado" in
`docs/arquitetura-engenharia.md`.

## Expected retrieval

Next to a PDF that has its `<name>.sections.yaml`, a `<name>.retrieval.yaml`
file holds a check tree and, for each branch, the passages the retrieval must
return for it:

```
research_proposal/
├── estrategias_teste_software_llm_judge_hitl.pdf
├── estrategias_teste_software_llm_judge_hitl.sections.yaml
└── estrategias_teste_software_llm_judge_hitl.retrieval.yaml
```

Start from `retrieval_template.yaml`. Each passage names the page, a short
excerpt copied from the PDF and, when the passage belongs to an annotated
section, that section exactly as the `.sections.yaml` names it. Pick excerpts that tell a branch apart from its neighbours in the same
section, and leave personal names out: the retrieval only sees the
anonymized text.

Check the file without spending tokens:

```
poetry run pytest tests/unit/services/test_retrieval_answer_keys.py
```

Then measure the retrieval against it with real embeddings:

```
poetry run pytest tests/ai/evaluation/retrieval -s --run-ai -m ai
```

The second test prints the score per branch and fails below the floors kept
in the test. See "Validação da Recuperação sobre Acervo Anotado" in
`docs/arquitetura-engenharia.md`.
