# ForkTheSource - AI Evidence

Provenance + reproducibility verification for academic papers, on ASU AIR.
CASI Team | ASU AIR Spark Challenge 2026

Drop in an academic PDF. The app pulls out every bibliography reference, normalizes
each one into JSON (authors, year, title, venue, volume, issue, pages, identifiers)
and shows them in a table.

## Setup
1. Get an AIR API key at https://voyager.rc.asu.edu (ASU VPN required)
2. `python3 -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. `cp .env.example .env` -> paste your OWN key into `.env`

Never commit `.env`. Keys are personal - each teammate creates their own.

## Run it

```
streamlit run app.py
```

That opens http://localhost:8501 in your browser. Drop a PDF on the upload box and
you get back the raw text the app could read out of it.

If nothing comes out, the PDF is probably a scan of a printed page rather than real
text. That needs OCR, which is out of scope.

## Run the tests

```
pytest
```

The intake test reads `tests/data/sample.pdf`, a tiny fixture built by
`python tests/data/make_sample_pdf.py`. Re-run that script if you want to change
what the fixture says.

## Where the code lives

```
app.py                    the web app - upload box, results
config.yaml               model names, temperatures, banned terms. Change settings HERE
.env.example              which environment variables you need (copy to .env)
src/
  config.py               the only code that reads config.yaml
  llm.py                  the shared client for the gateway (unused until M1)
  pipeline/               one module per stage, all with the same run() entry point
tests/                    one test module per stage, plus the fixture PDF
```

### The seven stages

| # | Stage | Kind | Does |
|---|-------|------|------|
| 1 | `intake` | plain code | read the PDF, find the bibliography |
| 2 | `extractor` | model | each raw reference -> JSON fields |
| 3 | `resolver` | plain code | look each reference up in public catalogues |
| 4 | `judge` | model | does the citation match what we found? |
| 5 | `repro_extractor` | model | pull the paper's reproducibility claims |
| 6 | `repro_judge` | model | are those claims backed by evidence? |
| 7 | `critic` | model | review the write-up before a human sees it |

Only stage 1 is implemented right now (M0). The rest raise `NotImplementedError`
and name the milestone they land in.

## Ground rules for the code

- Model names live in `config.yaml` and nowhere else. No stage hardcodes one.
- Credentials come from the environment (`AIR_BASE_URL`, `AIR_API_KEY`), never from
  code, and never from a file that git tracks.
- Every model reply is JSON validated against a schema. A bad reply is retried once,
  then the item is marked `extraction_failed` rather than guessed at.
- Stage 1 uses no model at all - it is `pdfplumber` and plain Python.
