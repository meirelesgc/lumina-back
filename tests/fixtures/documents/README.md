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
