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

Expected: `Python 3.13.7`, or any 3.11+. The code uses `X | Y` type syntax and builtin
generics, so **3.10 or older will not run it.**

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

Now open `.env` and set both values:

```
AIR_API_KEY=<paste your own key from Voyager here>
AIR_BASE_URL=<leave this as the value already in .env.example>
```

`AIR_BASE_URL` ships in the template with the correct gateway URL already filled in —
you only need to replace `AIR_API_KEY`. Both names must be present. `.env` is in
`.gitignore` and must never be committed; verify with:

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
collected 29 items

tests/test_app.py ...                                                    [ 10%]
tests/test_config.py .....                                               [ 27%]
tests/test_intake.py ......                                              [ 48%]
tests/test_pipeline_contract.py ...............                          [100%]

============================== 29 passed in 0.58s ==============================
```

**29 passed** is the number as of commit `4328eb7`. It will only ever go up; if you see
fewer tests collected than files, your `pytest` is probably the system one rather than
the venv's — check with `which pytest`.

These tests need no VPN, no key and no network. If they pass, the app will start.

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
listing — it consumes no tokens and calls no model.

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
   Expected exactly: `AIR_API_KEY` and `AIR_BASE_URL`.
4. **You edited `.env.example` instead of `.env`.** Common, and the app cannot tell.

The same applies verbatim to `AIR_API_KEY is not set`.

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
