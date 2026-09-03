# ForkTheSource - AI Evidence

Citation provenance verification for academic papers, on ASU AIR.
CASI Team | ASU AIR Spark Challenge 2026

> Reproducibility-claim verification is out of scope for this build - see
> [docs/descoped.md](docs/descoped.md). Final wording of this section belongs to R4.

Drop in an academic PDF. The app pulls out every bibliography reference, normalizes
each one into JSON (authors, year, title, venue, volume, issue, pages, identifiers)
and shows them in a table.

## Docs

| Read this | When |
|-----------|------|
| [docs/setup.md](docs/setup.md) | Fresh machine. VPN, key, install, run. Start here. |
| [docs/module_status.md](docs/module_status.md) | Before you branch anything. What is actually built, and what is safe to start. |
| [docs/config_reference.md](docs/config_reference.md) | Every key in `config.yaml`, what reads it, what breaks without it. |
| [docs/architecture_map.md](docs/architecture_map.md) | The real flow, the three lanes, the merge queue, and the two injection seams. |
| [docs/module_implementation_plan.pdf](docs/module_implementation_plan.pdf) | **Ground truth.** The full plan. When a doc and the plan disagree, the plan wins. |
| [docs/decisions.md](docs/decisions.md) | **Before you argue with a rule.** Every decision that constrains someone else's module, with stable D-numbers. The "Open at Sync 1" section at the top is the agenda. |
| [docs/worklog.md](docs/worklog.md) | What actually happened, session by session — including what went wrong and what it cost. |
| [docs/defect_catalog.md](docs/defect_catalog.md) | The 21 injected defects, their `defect_id`s, and the expected outcome of each. Roy's, for R1. |
| [eval/golden/FORMAT.md](eval/golden/FORMAT.md) | The golden-label file specification, the recall definition, and the release gate R2 implements. |
| [docs/descoped.md](docs/descoped.md) | What was cut and why, so nobody re-derives it. |

## Setup
1. Get an AIR API key at https://voyager.rc.asu.edu (ASU VPN required)
2. `python3 -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements-dev.txt`  (app deps + pytest; `requirements.txt` alone is app-only)
4. `cp .env.example .env` -> paste your OWN key into `.env`

Never commit `.env`. Keys are personal - each teammate creates their own.
Run `./scripts/check_secrets.sh` before every push (pytest runs it too).

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
scripts/check_secrets.sh  run before every push
src/
  settings.py             the only code that reads config.yaml
  llm.py                  the shared client for the gateway (no caller yet)
  ingest/                 P1 PDF intake, P2 reference extractor      (Ritik)
  resolvers/              P3 cache, P4 scholarly resolvers           (Ritik)
  matching/               P5 evidence builder + rule classifier      (Ritik)
tests/                    one test module per concern, plus the fixture PDF
```

Not yet created, and deliberately so: `src/contract.py` (B1) and `src/judge/` and
`dashboard/` are Arsha's, and `src/pipeline.py` is reserved for the P6 orchestrator.
`tests/test_layout.py` asserts they stay absent until their owner creates them.

### The flow

| # | Step | Module | Owner | Kind |
|---|------|--------|-------|------|
| 1 | intake | P1 | Ritik | plain code |
| 2 | extract | P2 | Ritik | **LLM** |
| 3 | resolve | P4 on P3's cache | Ritik | plain code + HTTP |
| 4 | evidence | P5 | Ritik | plain code |
| 5 | verdict | A1, or P5's rules as default | Arsha / Ritik | **LLM**, or pure code |
| 6 | priority | P6 / A1 | Ritik / Arsha | plain code |
| 7 | ledger | P6 | Ritik | plain code |

Only two steps call a model, which is why the whole pipeline runs end-to-end with no AIR
key on the rule-based path. Detail, plus the merge queue and the two injection seams, in
[docs/architecture_map.md](docs/architecture_map.md).

Right now only step 1 is half built. Everything else is unwritten - see
[docs/module_status.md](docs/module_status.md).

## Where everything is right now

[STATUS.md](STATUS.md) is the single answer to "is P2 merged yet and what does it
export". It lists open requests and blockers first, then what is on `main`, the remote
branches in flight, a table of every agreed public symbol marked importable or not, and
the latest block from each lane. **It is generated by
[scripts/update_status.py](scripts/update_status.py) - never hand-edit it**, your edit is
gone on the next commit; report your own progress by appending a block to
`progress/<you>.md` instead (format: [progress/_FORMAT.md](progress/_FORMAT.md)). Run
`bash scripts/install_hooks.sh` once per clone to point git at `.githooks/`, after which
every commit and every merge refreshes STATUS.md locally, and a GitHub Action refreshes
the copy on `main`. **Before you branch anything, `git pull && cat STATUS.md`** - that is
the whole protocol, and it is cheaper than asking in chat. Since the hooks rewrite a
tracked file, git will occasionally refuse a pull because STATUS.md is dirty; the fix is
always `git checkout -- STATUS.md` and pull again, never a manual merge.

## Ground rules for the code

- Model names live in `config.yaml` and nowhere else. No module hardcodes one.
- Credentials come from the environment (`AIR_BASE_URL`, `AIR_API_KEY`), never from
  code, and never from a file that git tracks.
- Every model reply is JSON validated against a schema. A bad reply is retried once, then
  the entry keeps its `raw_text` and gets the `malformed` indicator - extraction never
  drops an entry.
- Only steps 2 and 5 use a model. Everything else is plain Python, which is what makes the
  evaluation meaningful.
