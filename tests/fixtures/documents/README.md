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

The same file lists in `person_names` the people who sign the document
(authors, advisors, editors). No anonymized chunk may contain them.

## Adding a document

1. Add the PDF, its `<name>.sections.yaml` and its `<name>.running.yaml` to
   the folder of its type.
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
section, that section exactly as the `.sections.yaml` names it. Straight and
curly quotes compare as equal, and so do hyphens and dashes. Inside tables
the extractor keeps words broken by a hyphen (`net-‖works`): pick the part of
the excerpt that does not break. Pick excerpts that tell a branch apart from its neighbours in the same
section, and leave personal names out: the retrieval only sees the
anonymized text.

Each branch with evidence also carries `fulfilled`, the expected verdict:
`true` only when the document meets the branch in full. A partial answer is
`false`, and a branch with `evidence: []` is `false`.

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

## Expected running headers and footers

Next to each PDF, a `<name>.running.yaml` file lists the lines that repeat
at the top or bottom of the pages and must not reach the chunks, such as the
running title, the authors line and the journal footer. It also lists the
text near the top or bottom of a page that must stay, such as a figure
caption the layout model marks as a footer:

```
systematic_review/
├── dengue_no_brasil.pdf
├── dengue_no_brasil.sections.yaml
└── dengue_no_brasil.running.yaml
```

Start from `running_template.yaml`. Copy each line from the PDF; the test
compares only letters and digits, so markup, punctuation and spacing do not
matter. Leave page numbers out. Use `keep_on_pages` for the pages where a
running line stays, such as its first occurrence. A document without running
lines gets a file with `running_lines: []`.

```
poetry run pytest tests/unit/services/test_ingestion_running_lines.py
```

The test joins the chunks of each page and fails on any listed line found
outside `keep_on_pages`, or on any `keep_lines` entry missing from its page.
