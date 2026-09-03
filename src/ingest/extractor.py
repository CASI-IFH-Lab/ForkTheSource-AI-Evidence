"""P2 - reference extractor. Owner: Ritik. The first AIR call in the pipeline.

Public interface (P4, P5, A3 import only these):

    split_entries(references_text) -> list[str]      plain code, no model
    extract_references(doc)        -> ExtractionResult(references, malformed_ref_ids)
    extract_claims(doc, refs)      -> list[Claim]    re-exported from src.ingest.claims

``extract_claims`` is implemented in ``src.ingest.claims`` - plain regex, no model, no
cache, no config - and re-exported here because the P2 card names the two extraction
entry points as one interface.

## The split is the part that must be right

A wrong split makes every downstream number wrong and no prompt fixes it: the model is
called once per entry, so an entry boundary in the wrong place produces a confidently
extracted reference that does not exist. ``split_entries`` is therefore plain Python,
tested alone against both real fixtures, and it does four things P1's measurements said
it had to:

* **Markers must be at line START and monotonic from 1.** A wrapped line reading
  "2014. Some title" is not entry 2014. Bracketed ``[n]`` is tried first, then ``n.``
  / ``n)``, then a blank-line split for author-year styles with no markers at all.
* **The tail gets truncated.** P1 hands over everything after the references heading,
  appendices included: on ``sample.pdf`` 26% of ``references_text`` is the attention
  -visualisation appendix, rendered by pdfplumber as reversed single-character lines
  ('tI', 'si'). The last entry stops at the last line that still reads as reference
  prose.
* **Page furniture is dropped.** Both real papers interleave it *between entries*:
  bare page numbers ('10', '11', '12') in the arXiv paper, and a running footer
  ("PLOS Biology | DOI:... 8 / 9") three times in the PLOS one. Left in, it would be
  glued onto the end of whichever entry preceded it.
* **Wrapped lines are rejoined** with a space, except after a trailing hyphen, where
  the hyphen is DROPPED and the fragments join directly: "im-\\nage" -> "image". A hyphen
  in that position is syllabic hyphenation, and leaving it in is what poisoned the title
  search - see ``_rejoin``, which is the only place with enough information to decide.

## malformed is a side-channel, NOT a derived predicate

``Reference`` forbids extra fields (B1, Tier 1, frozen), so there is nowhere on it to
store a flag. ``extract_references`` therefore returns **two** things:

    result = extract_references(doc)
    result.references          # list[Reference], one per entry, never short
    result.malformed_ref_ids   # frozenset[str], the ones extraction could not read

It is a ``NamedTuple``, so ``refs, malformed = extract_references(doc)`` also works.

The first version of this used ``is_malformed(ref) == (ref.title is None)`` and that was
**wrong**, for a reason worth keeping written down: a reference that genuinely has no
title - a standard, a dataset, a "personal communication" - is a perfectly good
extraction, and the predicate could not tell it apart from a failure. Roy's corpus
carries a genuine-unresolvable row to exercise that path, and stamping ``malformed`` on
an ``injected: false`` entry costs a row of recall that presents as a P5 bug. See D-102.

Membership of ``malformed_ref_ids`` comes from the **extraction attempt**: the entry is
in the set when no reply validated against ``Reference`` after the configured retry. A
well-formed reply whose ``title`` is null is NOT malformed. P5 stamps
``Indicator.MALFORMED`` on exactly this set; the entry is still in ``references``, still
carries its ``raw_text``, and is never dropped.

**Extraction never drops an entry.** ``len(out) == len(entries)`` is asserted in code
before returning, not just in a test.

## ref_id

``R`` + 1-based position, zero-padded to two digits (``R01``..``R99``), widening to
three for a bibliography of 100 or more, never mixed within one document. This is not a
choice made here - it is specified in ``eval/golden/FORMAT.md`` and it is the single
coupling point between Roy's golden labels and this pipeline. Ids are compared as
opaque strings: ``"R03"`` and ``"R3"`` are different references.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

from src import settings
from src.contract import Reference
from src.ingest import prompts
from src.ingest.claims import extract_claims
from src.ingest.pdf_parser import ParsedDocument

# Re-exported, not defined here. The P2 card names extract_references and
# extract_claims as one public interface - "other modules may import ONLY these" - so
# both are importable from this module, and the agreed interface table in
# scripts/update_status.py looks for both here. The implementation stays in claims.py
# because it shares nothing with the extractor: no model, no cache, no config.
__all__ = [
    "ExtractionResult",
    "ParsedDocument",
    "extract_claims",
    "extract_references",
    "marker_style",
    "ref_id_for",
    "split_entries",
]

_STAGE = "extractor"

# --- marker styles, tried in this order ------------------------------------
# Each must match at the START of a line and be followed by whitespace then content,
# so "[12]" alone on a line, or "1.5 times faster", is not a marker.
_BRACKETED = re.compile(r"^\s*\[(\d{1,3})\]\s+(?=\S)")
_NUMBERED = re.compile(r"^\s*(\d{1,3})[.)]\s+(?=\S)")
_MARKER_STYLES = (("bracketed", _BRACKETED), ("numbered", _NUMBERED))

# A line that is nothing but a short number: a page number. Capped at four digits so a
# wrapped PMID ("24482835") or a long numeric identifier is not mistaken for furniture.
_BARE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")
_DIGITS = re.compile(r"\d+")

# Furniture thresholds. A running header repeats on every page of the reference region;
# a real reference line does not repeat three times with only its digits differing.
# Both bounds matter: without the length floor, "arXiv:1607.06450, 2016." (23 chars,
# 5 occurrences in sample.pdf) would be deleted as furniture.
_FURNITURE_MIN_REPEATS = 3
_FURNITURE_MIN_LENGTH = 30

# A blank line in references_text is a PAGE boundary (P1 joins pages with one). The
# final entry continues across one only if what follows still reads like reference
# prose; real continuation lines in both fixtures run 48-94 characters.
_CONTINUATION_MIN_LENGTH = 30

# A trailing run this sparse is a rendering artifact, not a reference. sample.pdf's
# appendix measures a median of 4.0 characters per line.
_FRAGMENT_MEDIAN_MAX = 5

# Below this, a marker style has not really been found - two entries in a row that both
# match and count up is the weakest evidence worth acting on.
_MIN_ENTRIES = 2

_JSON_KEYS = ("title", "authors", "year", "doi", "arxiv_id", "venue")
_CACHE_FILENAME = "extractor_cache.json"


# ---------------------------------------------------------------------------
# Step 1: the pre-splitter. Plain Python, no model, no network.
# ---------------------------------------------------------------------------
def _drop_page_furniture(lines: list[str]) -> tuple[list[str], list[str]]:
    """Remove bare page numbers and repeated running headers/footers.

    Returns (kept, dropped); the dropped list exists so a test can assert on what went
    and a caller can see it. Blank lines are KEPT - they are page boundaries and the
    final-entry rule reads them.
    """
    repeats: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if len(stripped) >= _FURNITURE_MIN_LENGTH:
            key = _DIGITS.sub("#", stripped)
            repeats[key] = repeats.get(key, 0) + 1

    kept: list[str] = []
    dropped: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and _BARE_NUMBER.fullmatch(line):
            dropped.append(line)
            continue
        if (
            len(stripped) >= _FURNITURE_MIN_LENGTH
            and repeats.get(_DIGITS.sub("#", stripped), 0) >= _FURNITURE_MIN_REPEATS
        ):
            dropped.append(line)
            continue
        kept.append(line)
    return kept, dropped


def _marker_starts(lines: list[str], pattern: re.Pattern[str]) -> list[int]:
    """Line indices where a marker appears whose number is the next one expected.

    Monotonic from 1, which is what makes this robust: any line that happens to start
    with a number is ignored unless that number is exactly the one due next.
    """
    starts: list[int] = []
    expected = 1
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match and int(match.group(1)) == expected:
            starts.append(index)
            expected += 1
    return starts


def _median_length(lines: list[str]) -> float:
    lengths = [len(line.strip()) for line in lines if line.strip()]
    return statistics.median(lengths) if lengths else 0.0


def _final_entry_end(lines: list[str], start: int) -> int:
    """Where the LAST entry stops - which is where the appendix tail gets cut.

    Every other entry is bounded by the next marker. The last one has to be bounded by
    what the text looks like, in two passes: walk forward across page boundaries only
    while the text still reads like reference prose, then trim any trailing run sparse
    enough to be a rendering artifact.
    """
    index = start
    end = start
    while index < len(lines):
        if lines[index].strip():
            end = index + 1
            index += 1
            continue
        ahead = index + 1
        while ahead < len(lines) and not lines[ahead].strip():
            ahead += 1
        if ahead >= len(lines) or len(lines[ahead].strip()) < _CONTINUATION_MIN_LENGTH:
            break
        index = ahead

    for cut in range(start + 1, end):
        if _median_length(lines[cut:end]) < _FRAGMENT_MEDIAN_MAX:
            return cut
    return end


def _rejoin(lines: list[str]) -> str:
    """One entry's lines into one string, with the hyphen rule.

    **The hyphen decision is made HERE, at the join, and it cannot be made anywhere
    else.** This function knows something the joined string does not: which hyphens
    were the last character before a line break. A rule applied to the finished string
    cannot tell `im-age` (a line-break artifact) from `short-term` (printed that way),
    because by then they look identical - and both are common. 17 of 40 `sample.pdf`
    entries carry a hyphen, genuine ones mixed in with artifacts.

    So: a hyphen that was the last character before a break is DROPPED, because in
    print that position is syllabic hyphenation. A hyphen anywhere else is kept
    untouched. Measured on both real papers: 30 line-end hyphens, of which ~26 are
    syllabic (`im-age`, `Convolu-tional`, `sci-ence`, `Pharma-ceutical`). This is what
    poisons the title search - "Deep residual learning for im-age recognition" does not
    find the paper it names, and the wrong record it does find scored `conflict`.

    **The one exception is a hyphen after a digit**, which is printed punctuation inside
    an identifier rather than a break in a word: `plos_sample.pdf` splits a DOI across
    `10.1016/S0140-` / `6736(13)62227-8`, and dropping that hyphen produces a DOI that
    is not the cited work's. A corrupted title finds nothing; a corrupted DOI can find
    somebody else's paper and assert it confidently, which is the worse failure.

    **Known cost, measured, not guessed:** a genuine compound that breaks exactly at its
    own hyphen loses it - `attention-`/`based` becomes `attentionbased` and `pre-`/
    `clinical` becomes `preclinical`. That is 2 words across 74 real references against
    ~26 repaired ones, and neither survives into a lookup key that matters. Separating
    those two cases needs a dictionary, which is not a thing this file is going to grow.
    """
    out = ""
    for line in lines:
        piece = line.strip()
        if not piece:
            continue
        if not out:
            out = piece
        elif out.endswith("-"):
            if len(out) >= 2 and out[-2].isdigit():
                out += piece  # inside an identifier - keep the printed hyphen
            else:
                out = out[:-1] + piece  # line-break hyphenation - drop it
        else:
            out += " " + piece
    return out


def split_entries(references_text: str) -> list[str]:
    """Split a references block into one string per entry. Plain code, no model.

    Empty in, empty out - an image-only PDF reaches here with "" and must not raise.
    """
    if not references_text.strip():
        return []

    lines, _dropped = _drop_page_furniture(references_text.splitlines())

    for _style, pattern in _MARKER_STYLES:
        starts = _marker_starts(lines, pattern)
        if len(starts) >= _MIN_ENTRIES:
            spans = list(zip(starts, starts[1:]))
            spans.append((starts[-1], _final_entry_end(lines, starts[-1])))
            return [_rejoin(lines[first:last]) for first, last in spans]

    # No usable markers: author-year style. Blank lines are the only boundary left.
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            blocks.append(_rejoin(current))
            current = []
    if current:
        blocks.append(_rejoin(current))
    return [block for block in blocks if block]


def marker_style(references_text: str) -> str:
    """Which style ``split_entries`` would use. For diagnostics and tests."""
    lines, _ = _drop_page_furniture(references_text.splitlines())
    for style, pattern in _MARKER_STYLES:
        if len(_marker_starts(lines, pattern)) >= _MIN_ENTRIES:
            return style
    return "blank-line"


# ---------------------------------------------------------------------------
# ref_id
# ---------------------------------------------------------------------------
def ref_id_for(position: int, total: int) -> str:
    """``R`` + 1-based position, two digits, three when the document has 100 or more.

    Width is decided by the DOCUMENT, not by the position, so one file never mixes
    widths - see eval/golden/FORMAT.md, which owns this format.
    """
    width = 2 if total < 100 else 3
    return f"R{position:0{width}d}"


# ---------------------------------------------------------------------------
# Step 3: the cache. One JSON file, keyed by everything that changes an answer.
# ---------------------------------------------------------------------------
def cache_path() -> Path:
    return settings.cache_dir() / _CACHE_FILENAME


def cache_key(entry: str, model: str, temperature: float, schema_version: Any) -> str:
    """Hash of everything that can change the reply.

    Prompt version is in here because a reworded prompt produces different output from
    the same entry, and serving the old answer would be a silent regression. Schema
    version is config's documented invalidation lever.
    """
    payload = json.dumps(
        {
            "entry": entry,
            "model": model,
            "temperature": temperature,
            "prompt_version": prompts.PROMPT_VERSION,
            "schema_version": schema_version,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_cache() -> dict[str, Any]:
    path = cache_path()
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError):
        # A corrupt cache is a slow run, not a failed one.
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _save_cache(cache: dict[str, Any]) -> None:
    """Atomic replace, so a crash mid-write cannot leave a truncated cache behind."""
    path = cache_path()
    try:
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(path.parent), delete=False, suffix=".tmp"
        )
        with handle:
            json.dump(cache, handle, sort_keys=True, ensure_ascii=False, indent=0)
        os.replace(handle.name, path)
    except OSError:
        pass  # An unwritable cache is a slow run, not a failed one.


# ---------------------------------------------------------------------------
# Step 3: one call per entry
# ---------------------------------------------------------------------------
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def _strip_to_json(text: str) -> str:
    """Take the outermost {...} out of a reply, fences and stray prose included."""
    cleaned = _FENCE_RE.sub("", text.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        return cleaned
    return cleaned[start : end + 1]


def _coerce_year(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r"\b(1[5-9]\d{2}|20\d{2}|21\d{2})\b", value)
        if match:
            return int(match.group(1))
    return None


def _reference_from_reply(reply: str, ref_id: str, raw_text: str) -> Reference:
    """Build a validated Reference from one model reply. Raises on anything unusable.

    ``ref_id`` and ``raw_text`` are ours and are never taken from the model - the model
    is asked for six bibliographic fields and nothing else, and a model-supplied ref_id
    would be a join key we did not control.
    """
    data = json.loads(_strip_to_json(reply))
    if not isinstance(data, dict):
        raise ValueError(f"reply is a {type(data).__name__}, not an object")

    unexpected = set(data) - set(_JSON_KEYS)
    if unexpected:
        raise ValueError(f"reply has unexpected keys: {sorted(unexpected)}")

    authors = data.get("authors") or []
    if not isinstance(authors, list) or not all(isinstance(a, str) for a in authors):
        raise ValueError("authors must be an array of strings")

    return Reference(
        ref_id=ref_id,
        raw_text=raw_text,
        title=data.get("title") or None,
        authors=[a.strip() for a in authors if a.strip()],
        year=_coerce_year(data.get("year")),
        doi=data.get("doi") or None,
        arxiv_id=data.get("arxiv_id") or None,
        venue=data.get("venue") or None,
    )


def _malformed_reference(ref_id: str, raw_text: str) -> Reference:
    """The never-dropped fallback: position, printed text, and nothing invented."""
    return Reference(ref_id=ref_id, raw_text=raw_text)


class ExtractionResult(NamedTuple):
    """What ``extract_references`` returns: every entry, plus which ones failed.

    A ``NamedTuple`` so both spellings work and neither is a trap::

        result = extract_references(doc)          # result.references, result.malformed_ref_ids
        references, malformed = extract_references(doc)

    ``malformed_ref_ids`` is a ``frozenset`` because it is a membership test with no
    meaningful order, and because a caller must not be able to mutate it into
    disagreeing with ``references``.
    """

    references: list[Reference]
    malformed_ref_ids: frozenset[str]


def _call_model(client: Any, entry: str, model: str, temperature: float, timeout: float) -> str:
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=prompts.build_messages(entry),
        timeout=timeout,
    )
    return response.choices[0].message.content or ""


def extract_references(
    doc: ParsedDocument,
    config: dict[str, Any] | None = None,
    client: Any = None,
) -> ExtractionResult:
    """Split the references block, then extract each entry with one AIR call.

    One call per entry rather than one for the whole block: a single call over forty
    entries fails as forty, and its output cannot be cached per entry or aligned back
    to positions with any confidence.

    ``client`` is injectable so the offline tests never touch the network. Passing one
    is the only way to run this without a key; left as None it builds the shared
    gateway client from the environment.
    """
    entries = split_entries(doc.references_text)
    if not entries:
        return ExtractionResult([], frozenset())

    config = config or settings.load_config()
    model = settings.model_for(_STAGE, config)
    temperature = settings.temperature_for(_STAGE, config)
    llm = settings.llm_settings(config)
    timeout = float(llm["timeout_seconds"])
    max_retries = int(llm["max_retries"])
    schema_version = settings.cache_settings(config).get("schema_version")

    cache = _load_cache()
    total = len(entries)
    out: list[Reference] = []
    malformed: set[str] = set()

    for position, entry in enumerate(entries, start=1):
        ref_id = ref_id_for(position, total)
        key = cache_key(entry, model, temperature, schema_version)

        reference: Reference | None = None
        cached = cache.get(key)
        if isinstance(cached, str):
            try:
                reference = _reference_from_reply(cached, ref_id, entry)
            except Exception:  # noqa: BLE001 - a stale cached reply is just a miss
                reference = None

        if reference is None:
            if client is None:
                from src.llm import get_client  # deferred: needs credentials

                client = get_client()
            # One retry, from config. Attempt 0 is the call; attempt 1 is the retry.
            for attempt in range(max_retries + 1):
                try:
                    reply = _call_model(client, entry, model, temperature, timeout)
                    reference = _reference_from_reply(reply, ref_id, entry)
                    cache[key] = reply
                    _save_cache(cache)
                    break
                except Exception:  # noqa: BLE001 - see the module docstring
                    if attempt >= max_retries:
                        reference = None
                    continue

        if reference is None:
            # No reply validated after the configured retry. The entry still ships,
            # with its printed text and nothing invented - and its id goes in the set,
            # because that is the only place the failure is recorded.
            reference = _malformed_reference(ref_id, entry)
            malformed.add(ref_id)
        out.append(reference)

    # Asserted in code, not only in a test: extraction never drops an entry.
    if len(out) != total:
        raise RuntimeError(
            f"extractor dropped entries: {len(out)} out for {total} in - this is a bug, "
            "not a data problem; every entry must come back, malformed if necessary"
        )
    return ExtractionResult(out, frozenset(malformed))
