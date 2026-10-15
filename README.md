# Zprávy Moravskoslezské pobočky ČBS — digitisation

Harvest of the bulletin (ms-cbs.cz + Zenodo community `msp-cbs`), faithful Markdown transcription of every article,
and excerption of localities and occurrences.

## Outputs

| file | content |
|---|---|
| `manifest.csv` | one row per article listed on the website or Zenodo, with PDF URL, DOI, local path, sha256, status |
| `pdf/<issue>/`, `md/<issue>/` | downloaded PDFs and their Markdown transcriptions (`<!-- page N -->` = printed page) |
| `localities.csv`, `occurrences.csv` | the two linked tables (`occurrences.locality_id` → `localities.locality_id`) |
| `review_queue.csv` | every flagged row with its source line, parsed values and question |
| `extraction_log.md` | rules, deviations and per-article counts |
| `qa_report.md` | totals, referential integrity, accuracy checks, review-queue summary and proposed rule changes |
| `reference/checklist_aopk.csv` | AOPK taxon checklist used for name matching |
| `reference/synonyms_proposed.csv` | unmatched names with proposals — fill `decision` to approve |
| `manual/` | hand transcriptions of image tables (vision model) and the manual QA review |

Every CSV is also written as `*_cp1250.csv` (Windows-1250, semicolon-separated) for Czech Excel.

## Re-running (e.g. when a new issue is published)

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\01_crawl.py --refresh      # index, issue pages, Zenodo; downloads only new PDFs
.venv\Scripts\python scripts\02_transcribe.py           # PDF → Markdown (all, or --only <file-name part>)
.venv\Scripts\python scripts\qa_transcription.py        # word-level comparison of Markdown with the PDF text layer
.venv\Scripts\python scripts\03_excerpt.py --all        # localities / occurrences / review queue / extraction log
.venv\Scripts\python scripts\inventory_formats.py       # articles whose record signals exceed what was excerpted
.venv\Scripts\python scripts\04_qa.py                   # QA report and synonym proposal
```

`scripts/00_fetch_checklist.py` refreshes the AOPK checklist. A new issue may use a record format the rules do not
cover: check `inventory_formats.py` output (many coordinates/grid squares but few rows) before trusting the tables.

Pending: 10 articles of č. 15/2026 are embargoed on Zenodo until 2026-09-30 — re-run the pipeline after that date.
Image tables that carry data need a hand transcription in `manual/<folder>/<pdf stem>.p<page>.img<k>.md`.
