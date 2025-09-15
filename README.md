# tobacco_researcher

Research tool to rapidly identify and summarize documents relevant to a given research question in the UCSF Truth Tobacco archives (UCSF Industry Documents Library).

## Overview
- Uses Solr search against the UCSF Industry Documents Library to retrieve document metadata.
- Lets you interactively add search filters (date ranges, document types, collections, brands) before running searches.
- Generates multiple search strategies (queries) for your research topic with Gemini and evaluates relevance with an LLM.
- Fetches OCR text per document for deeper analysis and summarizes the top‑scoring results.

## Setup
- Python: project uses a virtualenv in `myenv/`.
- API key: copy `.env.example` to `.env` and set `GEMINI_API_KEY=...`.
- Dependencies: install from `requirements.txt` into the venv if needed.
 - Optional endpoints (for IDL updates): set these in `.env` if needed
   - `SOLR_BASE_URL=https://metadata.idl.ucsf.edu/solr/ltdl3/query`
   - `OCR_BASE=https://download.industrydocuments.ucsf.edu/`

Example:
```
./myenv/bin/python -m pip install -r requirements.txt
```

## Run The Pipeline (v2 Primary)
```
./myenv/bin/python main.py
```
Flow:
- Enter research question (default: `youth women marketing tobacco`).
- Add filters via menu (no default date is preselected); press Enter to run.
- Choose parameters when prompted:
  - Rows per strategy (default 10)
  - How many to display (default 5)
  - How many to summarize (default 3)
- Under the hood:
  - Generates multiple search strategies for your query (LLM) — search terms only.
  - Runs Solr for each strategy with your selected filters.
  - Fetches OCR for each doc.
  - V2 analysis labels each doc: smoking_gun, strong, related, or irrelevant with confidence and facets.
  - Deduplicates by normalized title and OCR fingerprint (5‑gram Jaccard, threshold 0.92).
  - Ranks by label → confidence → facet boosts with frequency tie‑breaks.
  - Prints top N and summarizes the top M.

## How Filters Apply
- Availability: always enforced as `fq=availability:public`.
- Date: builds `fq` on `documentdateiso` with ISO datetimes; inputs like `[1980 TO 1990]` are normalized to `documentdateiso:[1980-01-01T00:00:00Z TO 1990-12-31T00:00:00Z]`. Multi‑select creates an OR group.
- Document type: builds `fq` on `dt`, quoting values; multi‑select ORs types.
- Collection: builds `fq` on `collection`, quoted; multi‑select ORs collections.
- Brand: builds `fq` on `brand`, quoted; multi‑select ORs brands.

Note: if your Solr schema uses different field names for collection/brand, adjust `build_solr_fqs` in `filter_ui.py`.

## Notes On Scoring
- Solr score: returned as `score` in each result; used for sorting within a query; not bounded.
- V2 labels: smoking_gun > strong > related > irrelevant, with confidence and facet boosts; final ranking uses tie‑break on frequency across strategies.
- V1 score (legacy): 0–10 relevance used only in the archived pipeline.

## OCR And Deduplication
- OCR: fetched from `https://download.industrydocuments.ucsf.edu/<a>/<b>/<c>/<d>/<id>/<id>.ocr` and truncated for prompts.
- Title normalization: punctuation removed, whitespace collapsed, adjacent single‑letter tokens merged (e.g., `R. J.` → `rj`).
- v2 Dedup:
  - Cache‑time: skip recache when normalized title already exists.
  - Rank‑time: collapse duplicates by normalized title, then by OCR fingerprint similarity (5‑gram Jaccard ≥ 0.92).
- v1 Dedup: cache‑time title dedup only; no OCR collapse.

## Useful Scripts
- `main.py`: primary pipeline entry (interactive parameters and filter UI).

## Legacy (v1) Pipeline
The previous 0–10 scoring pipeline is archived for reference.

- Run: `./myenv/bin/python legacy_v1/main_v1.py`
- Differences vs v2:
  - LLM returns a 0–10 relevance score (no labels).
  - No OCR fingerprint dedup at rank time.
  - Summaries pick top documents by the 0–10 score.

## Troubleshooting
- No strategies or analysis: check `GEMINI_API_KEY` in `.env` and network access to Google Generative AI.
- Empty results: loosen filters, try a broader date range, or verify field names (collection/brand) in `filter_ui.py`.
- Slow or few docs: increase per‑strategy rows in `main.py` (we use 10), or raise overall limits in a custom pull script.
