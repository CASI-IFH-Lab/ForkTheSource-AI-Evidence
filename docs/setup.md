# Setup — fresh machine to running app

Target: **under 10 minutes** from a clean clone, on a machine with Python and git
already installed. If it takes you longer than that, the extra time is a bug in this
document — say so and it gets fixed, because R4 will test this file as an acceptance
criterion.

Verified end to end on macOS 15 (Darwin 25.5.0) with **Python 3.13.7** on 2026-09-02.
Nothing here needs a GPU, and nothing here makes a model call.

## Step 0 — get on the ASU VPN

The AIR gateway is not reachable from the open internet. Connect the ASU VPN first.
Everything in steps 1 and 4-7 works offline; only step 3 and any later model call need
the VPN.

## Step 1 — clone and enter

```bash
git clone https://github.com/CASI-IFH-Lab/ForkTheSource-AI-Evidence.git
cd ForkTheSource-AI-Evidence
```

## Step 2 — create the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Expected: your prompt gains a `(.venv)` prefix. Confirm you are on a supported
interpreter:

```bash
python --version
```

Expected: `Python 3.13.7`. Only 3.13.7 has been verified end to end; **3.10 is the
floor**, because `src/ingest/pdf_parser.py` evaluates a `str | Path | bytes | IO[bytes]`
union at runtime (PEP 604) and that syntax does not exist before 3.10. If you are on 3.9
or older, the very first import fails with a `TypeError`. If you are on 3.10-3.12 it
should work, but you are the first to try it — say so if anything breaks.

## Step 3 — get your own API key

1. Go to https://voyager.rc.asu.edu (ASU VPN required).
2. Under **LLM API Access → API keys**, press **Create Key**. Name it something you will
   recognize later, e.g. `ForkTheSource`.
3. Copy the key **immediately**. The dashboard masks it after you leave the page, and a
   masked key pasted into `.env` will fail with a confusing 401 rather than an obvious
   error.

Keys are personal. Do not share yours, do not paste it into chat or a ticket, and do not
ask a teammate for theirs — creating a new one takes fifteen seconds.

## Step 4 — create your `.env`

```bash
cp .env.example .env
```

**Copy, do not move.** `.env.example` is a tracked file the whole team needs; `mv` deletes
it and shows up as a spurious deletion in your next `git status`. (This has already
happened once in this repo.)

Now open `.env` and set **all three** values:

```
AIR_API_KEY=<paste your own key from Voyager here>
AIR_BASE_URL=<leave this as the value already in .env.example>
CROSSREF_MAILTO=<your own ASU address, e.g. yourasurite@asu.edu>
```

`AIR_BASE_URL` ships in the template with the correct gateway URL already filled in, so
you only need to replace the other two. **All three names must be present.**

- **`AIR_API_KEY`** — your own key from Voyager. `src/llm.py` raises without it.
- **`AIR_BASE_URL`** — the gateway. Leave the template's value alone.
- **`CROSSREF_MAILTO`** — your own ASU address, sent to Crossref as the polite-pool
  contact. `src/settings.py: crossref_mailto()` raises without it, and P4 refuses to start.
  It is in `.env` rather than `config.yaml` because it differs per teammate, and because a
  real mailbox in a tracked file is the same shape of mistake as a pasted key — see
  **D-007** in [decisions.md](decisions.md). Nothing calls it yet; P4 will be the first.

`.env` is in `.gitignore` and must never be committed; verify with:

```bash
git check-ignore -v .env
```

Expected: `.gitignore:1:.env	.env`. If that prints nothing, stop — your `.env` is not
being ignored and you are one `git add -A` away from publishing a live key.

## Step 5 — install dependencies

```bash
pip install -r requirements.txt
```

Expected: a few minutes of downloading (Streamlit pulls a large dependency tree — about
80 seconds on a warm cache, longer on a cold one), ending with a `Successfully
installed ...` line and no `ERROR`. Versions this was verified against:

| Package | Verified version |
|---------|------------------|
| streamlit | 1.63.0 |
| pdfplumber | 0.11.10 |
| openai | 3.7.0 |
| python-dotenv | 1.2.3 |
| PyYAML | 6.0.3 |
| pytest | 9.1.1 |

## Step 6 — run the tests

```bash
pytest
```

Expected, and this is the real check that your install is sound:

```
============================= test session starts ==============================
platform darwin -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
collected 39 items

tests/test_app.py ...                                                    [  7%]
tests/test_config.py ............                                        [ 38%]
tests/test_intake.py ......                                              [ 53%]
tests/test_layout.py ...........                                         [ 82%]
tests/test_no_secrets.py .......                                         [100%]

============================== 39 passed in 0.67s ==============================
```

**39 passed** is the number as of commit `c83f17f`. If you see fewer tests collected than
files, your `pytest` is probably the system one rather than the venv's — check with
`which pytest`.

These tests need no VPN, no key and no network — `tests/test_no_secrets.py` shells out to
`scripts/check_secrets.sh` but only reads local files. If they pass, the app will start.

## Step 7 — run the app

```bash
streamlit run app.py
```

Expected:

```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Open http://localhost:8501, drag a PDF onto the drop zone, and you should see three
metrics (Pages, Characters, Pages with no text) and the raw extracted text below them.
That is the whole of M0 — no model is called, and nothing leaves your machine.

Stop the app with `Ctrl+C`.

## Step 8 (optional) — check your key actually works

M0 makes no model calls, so a bad key will not show up until the first real stage lands.
To find out now, with the VPN on:

```bash
python -c "from src.llm import get_client; print(sorted(m.id for m in get_client().models.list())[:5])"
```

Expected: a list of five model names from the gateway catalogue. This is a read-only
listing — it consumes no tokens and calls no model. Verified working on 2026-09-03.

## Step 9 — before every push: the secrets check

```bash
./scripts/check_secrets.sh
```

Expected:

```
[1/2] scanning tracked files for key-shaped literals...
      ok - no key-shaped literal in any tracked file.
[2/2] scanning for the gateway host outside .env.example...
      ok - gateway host appears only in .env.example.

check_secrets: PASS
```

It scans **tracked files only** — untracked scratch files cannot reach GitHub — for two
things: any `sk-`-shaped literal, and the AIR gateway host appearing anywhere other than
`.env.example`. Non-zero exit means stop and fix before pushing.

`pytest` runs it too, via `tests/test_no_secrets.py`, so a green suite already covers you.
Run it directly when you have been editing docs and want the answer in one second.

**This exists because of a real near-miss.** During the B0 docs pass, the first 16
characters of a live key were drafted into `docs/setup.md` as an example of what *not* to
paste. It was caught by hand before the commit. Hand-catching is not a control.

If it ever fires on a real key: **rotate the key in Voyager immediately.** Per Section 8
of the plan, rotation is the fix — deleting the commit is not. Assume anything pushed is
already harvested.

---

# Troubleshooting

## `RuntimeError: AIR_BASE_URL is not set`

`src/llm.py` raises this deliberately rather than falling back to a default URL, because
a silent default is how you end up pointing at the wrong gateway without noticing.

Causes, in the order they actually happen:

1. **No `.env` file at all.** Run `ls -la .env`. If it is missing, redo step 4.
2. **`.env` is not in the directory you are running from.** `python-dotenv` looks up from
   the current working directory. Run commands from the repo root, not from `src/`.
3. **`.env` has the key name misspelled** — `AIR_BASEURL`, `AIR_BASE_URI`, a stray space
   before the `=`. Check the names without revealing values:
   ```bash
   grep -oE '^[A-Za-z_][A-Za-z0-9_]*' .env
   ```
   Expected exactly: `AIR_API_KEY`, `AIR_BASE_URL` and `CROSSREF_MAILTO`.
4. **You edited `.env.example` instead of `.env`.** Common, and the app cannot tell.

The same applies verbatim to `AIR_API_KEY is not set` and to
`CROSSREF_MAILTO is not set` — the last of which comes from `src/settings.py` rather than
`src/llm.py`, and is raised for the reason in **D-007**: without a contact address Crossref
demotes you out of the polite pool *silently*, so the missing value has to be loud.

## The key authenticates but the gateway rejects the request

These look alike from the app and are three different problems. Read the error class,
not just the message:

- **`AuthenticationError` / HTTP 401** — the key itself is wrong. The most common cause
  is pasting the *masked* form off the dashboard (the dashboard shows the first few characters followed by bullets, and those bullets are not characters you can type) instead
  of the real one. A masked paste is short and structurally plausible, so nothing catches
  it until the first call. Rotate the key in Voyager and paste the fresh one.
- **`PermissionDeniedError` / HTTP 403** — the key is valid but not entitled to that
  model. Check the model name in `config.yaml` against the catalogue listing from step 8.
- **`NotFoundError` / HTTP 404 on a model name** — the model was renamed or retired
  upstream. `config.yaml` is the only place model names live, so this is a one-line fix
  in that file; do not patch it in a stage. Confirm the new name against step 8's listing.
- **A hang, then a timeout** — you have dropped off the VPN. `curl -s -o /dev/null -w
  '%{http_code}' $AIR_BASE_URL/models` returns nothing at all when the VPN is down,
  versus `401` when it is up and your key is bad. That is the fastest way to tell the two
  apart.

## Port 8501 is already bound

Symptom: `Port 8501 is already in use`, or the app starts but shows an older version of
the page, because you are looking at a Streamlit process from a previous session.

Find and stop the old one:

```bash
lsof -i :8501
kill <the PID from that output>
```

Or just use a different port:

```bash
streamlit run app.py --server.port 8502
```

If a stale process is wedged and `kill` does not take, `kill -9 <PID>`. Do not
`pkill -f streamlit` on a shared machine — you will take out a teammate's session.

## `pdfplumber` fails to install

`pdfplumber` pulls `pdfminer.six`, `pypdfium2`, `Pillow` and `cryptography`, and the last
two are the ones that break. What the failure looks like and what to do:

- **`error: command 'clang' failed` / missing `Python.h` on macOS** — you need the command
  line tools: `xcode-select --install`. Then retry the install.
- **A `cryptography` build failure mentioning Rust or `cargo`** — pip is trying to build
  from source because no wheel matched your interpreter. Upgrade pip first, which usually
  finds the wheel: `pip install --upgrade pip setuptools wheel`, then retry.
- **`Pillow` build failure mentioning `zlib` or `libjpeg`** — same cause, same fix. On
  Linux, `sudo apt install libjpeg-dev zlib1g-dev` if the wheel genuinely does not exist
  for your platform.
- **It installed but `import pdfplumber` fails** — you are almost certainly outside the
  venv. Re-run `source .venv/bin/activate` and check `which python`.

A separate warning you can ignore: Streamlit suggests installing `watchdog` for better
performance. It is optional and affects only file-watching speed during development.

## The app runs but a PDF renders no text

Not a setup problem. The PDF is a scan of a printed page — an image, with no text layer.
Extracting text from it needs OCR, which is out of scope. The app detects this case and
says so. Try a different PDF, e.g. anything from arXiv.
