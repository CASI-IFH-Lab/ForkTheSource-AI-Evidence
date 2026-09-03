"""A2 - the reviewer dashboard. ``streamlit run dashboard/app.py``.

The shape of this file is deliberate: **every number on screen is computed by
a plain function that returns plain data, and the ``st.*`` calls only draw
it.** ``summary_rows``, ``headline``, ``progress_stages``, ``worklist_rows``,
``signal_rows`` and ``entry_panel`` take a ``Ledger`` and give back dicts, so
`tests/test_dashboard_data.py` can assert what the reviewer will see without
starting Streamlit. A dashboard whose correctness can only be checked by
looking at it is a dashboard nobody checks.

It reads a ``Ledger`` and nothing else. No pipeline, no resolvers, no judge -
`tests/test_layout.py` enforces that in both directions, and it is what lets
A2 be built and demonstrated while Ritik's lane is still in flight. A3 adds
the live run; nothing here is rewritten when it does.

The counts guard is the one hard refusal. When ``counts_are_consistent()`` is
false the page renders an error and stops, because a worklist that is
confidently wrong about how many references it covers is worse than no
worklist. That mirrors ``Ledger.assert_consistent()`` and Ritik's
``PipelineIntegrityError``.
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import streamlit as st

from dashboard import theme
from src import settings
from src.contract import Ledger, LedgerEntry, load_ledger

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER_DIR = REPO_ROOT / "data" / "output"
FIXTURE_LEDGER = REPO_ROOT / "tests" / "fixtures" / "ledger_fixture.json"


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def integrity_problem(ledger: Ledger) -> str | None:
    """The reason this ledger must not be rendered, or ``None`` if it is sound.

    Returns a message rather than raising so the caller can put it on screen.
    A raised exception in a Streamlit script is a stack trace where the
    summary should be, which tells the reviewer nothing about what went
    wrong with their document.
    """
    counts = ledger.summary_counts()
    total = len(ledger.entries)
    if not ledger.counts_are_consistent():
        return (
            f"Status counts do not add up: {sum(counts.values())} verdicts across "
            f"{total} references ({counts}). The summary is not rendered, because "
            "counters that disagree with the worklist would be worse than no counters."
        )
    return None


# ---------------------------------------------------------------------------
# Row 1 - the summary. The demo's opening image.
# ---------------------------------------------------------------------------


def headline(ledger: Ledger) -> dict:
    """The one-line claim above the counters: N in, M worth checking.

    "Worth checking" is every entry that is not ``verified`` - the three
    statuses that put a row on a human's desk. It is deliberately not
    "problems found": the phrase names what the reviewer has to do, not what
    the references are.
    """
    counts = ledger.summary_counts()
    total = len(ledger.entries)
    worth_checking = total - counts["verified"]
    return {
        "document_name": ledger.document_name,
        "total": total,
        "worth_checking": worth_checking,
        "verified": counts["verified"],
        "coverage": ledger.evidence_coverage(),
        "resolved": sum(1 for e in ledger.entries if e.evidence.resolved is not None),
        "claims": len(ledger.claims),
    }


def summary_rows(ledger: Ledger) -> list[dict]:
    """One row per status, worst first, with the share each one holds.

    Built from ``Ledger.summary_counts()`` rather than by counting entries
    here - B1 already wrote that method, it already guarantees all four
    statuses are present with their zeros, and a second implementation in
    the UI is how the counters start disagreeing with the worklist.
    """
    counts = ledger.summary_counts()
    total = len(ledger.entries)
    rows = []
    for status in theme.STATUS_ORDER:
        style = theme.status_style(status)
        count = counts[status]
        rows.append(
            {
                "status": status,
                "label": style["label"],
                "icon": style["icon"],
                "color": style["color"],
                "soft": style["soft"],
                "blurb": style["blurb"],
                "count": count,
                # 0 references is a real state - an empty ledger - and it
                # renders as four empty bars rather than a division by zero.
                "share": (count / total) if total else 0.0,
            }
        )
    return rows


def _counter_html(row: dict) -> str:
    pct = round(row["share"] * 100)
    return (
        '<div class="ft-counter">'
        '<div class="ft-top">'
        f'<span class="ft-n" style="color:{row["color"]}">{row["count"]}</span>'
        f'<span class="ft-label" style="color:{row["color"]}">{row["label"]}</span>'
        f'<span class="ft-share">{pct}%</span>'
        "</div>"
        f'<div class="ft-track" style="background:{row["soft"]}">'
        f'<div class="ft-fill" style="width:{row["share"] * 100:.4f}%;'
        f'background:{row["color"]}"></div>'
        "</div>"
        f'<div class="ft-blurb">{row["blurb"]}</div>'
        "</div>"
    )


def render_summary(ledger: Ledger) -> None:
    """Row 1: the headline claim, four counters, and the coverage line."""
    head = headline(ledger)
    st.markdown(
        f'<div class="ft-headline"><b>{head["total"]}</b> references in · '
        f'<b>{head["worth_checking"]}</b> worth checking · '
        f'<b>0</b> accusations</div>',
        unsafe_allow_html=True,
    )

    for column, row in zip(st.columns(4), summary_rows(ledger)):
        with column:
            st.markdown(_counter_html(row), unsafe_allow_html=True)

    st.caption(
        f'{head["resolved"]} of {head["total"]} references have a resolved record '
        f'({head["coverage"] * 100:.0f}% evidence coverage) · '
        f'{head["claims"]} claims read from the body'
    )


# ---------------------------------------------------------------------------
# Row 2 - the AIR progress strip
# ---------------------------------------------------------------------------


def judge_models(ledger: Ledger) -> list[str]:
    """Every distinct ``judge_model`` in the ledger, in first-seen order.

    Read off the ledger rather than out of ``config.yaml`` on purpose: the
    config says which model we MEANT to call, and the ledger says which one
    actually answered. When the gateway was down those differ, and the strip
    should say so - that is the whole point of A1 recording the path.
    """
    seen: list[str] = []
    for entry in ledger.entries:
        name = entry.verdict.judge_model
        if name not in seen:
            seen.append(name)
    return seen


def _configured_model(stage: str) -> str | None:
    try:
        return settings.model_for(stage)
    except Exception:
        return None


def progress_stages(ledger: Ledger | None = None) -> list[dict]:
    """The seven chips, each with the model name where there is one.

    In A2 this is static: it describes the run that produced the ledger on
    screen. A3 wires the same shape to ``run(..., progress=cb)`` so the chips
    light live. The structure does not change between the two, which is why
    the callback contract is honoured here already.
    """
    models = judge_models(ledger) if ledger is not None else []
    chips = []
    for stage in theme.STAGES:
        model: str | None = None
        source = ""
        if stage.get("air"):
            model_stage = str(stage.get("model_stage", ""))
            if model_stage == "judge" and models:
                model = models[0] if len(models) == 1 else f"{len(models)} models"
                source = "as run"
            else:
                model = _configured_model(model_stage)
                source = "configured"
        chips.append(
            {
                "key": str(stage["key"]),
                "label": str(stage["label"]),
                "air": bool(stage.get("air")),
                "model": model,
                "model_source": source,
                "done": ledger is not None,
            }
        )
    return chips


def render_progress_strip(ledger: Ledger | None) -> None:
    """Row 2. The beat where the AIR platform becomes visible - give it weight."""
    st.markdown("##### Pipeline")
    chips = progress_stages(ledger)
    for column, chip in zip(st.columns(len(chips)), chips):
        with column:
            accent = theme.AIR_ACCENT if chip["air"] else theme.MUTED
            mark = "●" if chip["done"] else "○"
            st.markdown(
                f'<div style="border:1px solid {theme.RULE};border-radius:8px;'
                f'padding:.4rem .5rem;text-align:center;'
                f'border-top:3px solid {accent}">'
                f'<div style="font-size:.78rem;font-weight:600;color:{theme.INK}">'
                f'{mark} {chip["label"]}</div>'
                + (
                    f'<div style="font-size:.66rem;color:{accent};font-weight:600;'
                    f'margin-top:.2rem;word-break:break-all">AIR · {chip["model"]}</div>'
                    if chip["air"] and chip["model"]
                    else '<div style="font-size:.66rem;color:'
                    + theme.MUTED
                    + ';margin-top:.2rem">deterministic</div>'
                )
                + "</div>",
                unsafe_allow_html=True,
            )

    fallbacks = [name for name in judge_models(ledger or Ledger(document_name="")) if name.startswith("fallback:")]
    if fallbacks:
        st.warning(
            "Some verdicts in this ledger were produced without the gateway "
            f"({', '.join(fallbacks)}). The run is complete and the results are "
            "deterministic; they are just not model-written.",
            icon="⚠",
        )


# ---------------------------------------------------------------------------
# Row 3 - the worklist and the evidence detail
# ---------------------------------------------------------------------------


def lookup_url(entry: LedgerEntry) -> tuple[str, str] | None:
    """One click to the record, as (label, url), or ``None``.

    Never invents an identifier. The waterfall only ever reshapes something
    already present: the provider's own URL, then the printed or resolved
    DOI, then an arXiv id, and only as a last resort a title search - which
    is a search, not a claim that the URL is the record.
    """
    reference, resolved = entry.reference, entry.evidence.resolved
    if resolved is not None and resolved.url:
        return ("open the resolved record", resolved.url)
    doi = (resolved.doi if resolved is not None else None) or reference.doi
    if doi:
        return ("open the DOI", f"https://doi.org/{doi}")
    arxiv_id = (resolved.arxiv_id if resolved is not None else None) or reference.arxiv_id
    if arxiv_id:
        return ("open the arXiv entry", f"https://arxiv.org/abs/{arxiv_id}")
    if reference.title:
        query = urllib.parse.quote_plus(reference.title)
        return ("search for the title", f"https://scholar.google.com/scholar?q={query}")
    return None


def signal_rows(entry: LedgerEntry) -> list[dict]:
    """The four match signals, formatted, with ``doi_match`` as three states."""
    ev = entry.evidence
    doi = theme.doi_match_state(ev.doi_match)
    return [
        {
            "name": "title similarity",
            "value": f"{ev.title_similarity:.2f}",
            "color": theme.INK,
        },
        {
            "name": "author overlap",
            "value": f"{ev.author_overlap:.2f}",
            "color": theme.INK,
        },
        {
            "name": "year difference",
            "value": "not comparable" if ev.year_delta is None else f"{ev.year_delta}",
            "color": theme.MUTED if ev.year_delta is None else theme.INK,
        },
        {
            "name": "DOI",
            "value": f'{doi["icon"]} {doi["label"]}',
            "color": doi["color"],
        },
    ]


def worklist_rows(ledger: Ledger, limit: int | None = None) -> list[dict]:
    """Entries as flat dicts, already ordered by ``Ledger.worklist()``.

    The ordering is B1's, not the UI's: ``-priority`` with a ``ref_id``
    tie-break, so two runs of the same document produce the same top three.
    """
    rows = []
    for entry in ledger.worklist(limit):
        style = theme.status_style(entry.verdict.status)
        rows.append(
            {
                "ref_id": entry.reference.ref_id,
                "status": entry.verdict.status,
                "status_label": style["label"],
                "color": style["color"],
                "soft": style["soft"],
                "icon": style["icon"],
                "priority": entry.priority,
                "confidence": entry.verdict.confidence,
                "title": entry.reference.title or entry.reference.raw_text,
                "rationale": entry.verdict.rationale,
                "checks": list(entry.verdict.checks),
                "indicators": [str(i) for i in entry.evidence.indicators],
                "judge_model": entry.verdict.judge_model,
                "lookup": lookup_url(entry),
                "entry": entry,
            }
        )
    return rows


def entry_panel(entry: LedgerEntry) -> dict:
    """As-printed versus resolved, as two dicts with the same keys.

    Same keys on both sides so the two columns line up row for row: a field
    the resolver did not return shows as an em dash opposite the printed
    value, which is what makes a missing field visible instead of absent.
    """
    ref, resolved = entry.reference, entry.evidence.resolved
    printed = {
        "title": ref.title,
        "authors": ", ".join(ref.authors) if ref.authors else None,
        "year": ref.year,
        "doi": ref.doi,
        "venue": ref.venue,
        "arxiv id": ref.arxiv_id,
    }
    if resolved is None:
        found = {key: None for key in printed}
        provider = None
    else:
        found = {
            "title": resolved.title,
            "authors": ", ".join(resolved.authors) if resolved.authors else None,
            "year": resolved.year,
            "doi": resolved.doi,
            "venue": resolved.venue,
            "arxiv id": resolved.arxiv_id,
        }
        provider = resolved.provider
    return {
        "printed": printed,
        "resolved": found,
        "provider": provider,
        "has_resolved": resolved is not None,
        "raw_text": ref.raw_text,
        "notes": list(entry.evidence.notes),
        "cited_by": list(ref.cited_by_claims),
    }


def _chip(label: str, style: dict) -> str:
    return (
        f'<span class="ft-chip" style="background:{style["soft"]};'
        f'color:{style["color"]}">{label}</span>'
    )


def _render_checks(checks: list[str]) -> None:
    """1-3 things a human can do in a minute - or an honest note that there are none.

    A fallback verdict carries no checks (``Verdict.checks`` has max 3 and no
    minimum, deliberately), and an empty gap on screen reads as a bug. Saying
    so is the honest degradation the whole design is built on.
    """
    if not checks:
        st.markdown(
            f'<span style="color:{theme.MUTED};font-size:.8rem">'
            "no suggested checks — this verdict came from the fallback path</span>",
            unsafe_allow_html=True,
        )
        return
    for check in checks:
        st.markdown(f"- {check}")


def render_worklist(ledger: Ledger, top_n: int = 3) -> None:
    """Row 3a: the top few by priority, in full."""
    rows = worklist_rows(ledger, top_n)
    st.markdown(f"##### Start here — top {len(rows)} by priority")
    if not rows:
        st.info("This ledger has no entries.")
        return

    for row in rows:
        with st.container(border=True):
            left, right = st.columns([5, 2])
            with left:
                st.markdown(
                    _chip(f'{row["icon"]} {row["status_label"]}', row)
                    + "".join(
                        _chip(theme.indicator_style(i)["label"], theme.indicator_style(i))
                        for i in row["indicators"]
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(f'**{row["ref_id"]}** · {row["title"]}')
                st.markdown(row["rationale"])
                _render_checks(row["checks"])
                if row["lookup"]:
                    label, url = row["lookup"]
                    st.markdown(f"[{label} ↗]({url})")
            with right:
                st.metric("priority", f'{row["priority"]:.2f}')
                st.caption(f'confidence {row["confidence"] * 100:.0f}%')
                st.caption(f'judged by {row["judge_model"]}')


def render_all_entries(ledger: Ledger) -> None:
    """Row 3b: every entry as an expander, same order as the worklist."""
    st.markdown("##### Every reference")
    for row in worklist_rows(ledger):
        entry = row["entry"]
        panel = entry_panel(entry)
        title = f'{row["icon"]}  {row["ref_id"]} · {row["status_label"]} · {row["title"][:70]}'
        with st.expander(title):
            printed_col, found_col = st.columns(2)
            with printed_col:
                st.markdown("**As printed**")
                for key, value in panel["printed"].items():
                    st.markdown(f"{key}: {value if value not in (None, '') else '—'}")
            with found_col:
                header = (
                    f'**Resolved record** · {panel["provider"]}'
                    if panel["has_resolved"]
                    else "**Resolved record**"
                )
                st.markdown(header)
                if not panel["has_resolved"]:
                    st.markdown("nothing resolved for this entry")
                else:
                    for key, value in panel["resolved"].items():
                        st.markdown(f"{key}: {value if value not in (None, '') else '—'}")

            st.markdown("**Signals**")
            signal_cols = st.columns(4)
            for column, signal in zip(signal_cols, signal_rows(entry)):
                with column:
                    st.markdown(
                        f'<div style="font-size:.72rem;color:{theme.MUTED}">'
                        f'{signal["name"]}</div>'
                        f'<div style="font-weight:600;color:{signal["color"]}">'
                        f'{signal["value"]}</div>',
                        unsafe_allow_html=True,
                    )

            if row["indicators"]:
                st.markdown(
                    "".join(
                        _chip(theme.indicator_style(i)["label"], theme.indicator_style(i))
                        for i in row["indicators"]
                    ),
                    unsafe_allow_html=True,
                )
                for indicator in row["indicators"]:
                    blurb = theme.indicator_style(indicator)["blurb"]
                    if blurb:
                        st.caption(blurb)

            st.markdown("**Suggested checks**")
            _render_checks(row["checks"])
            if row["lookup"]:
                label, url = row["lookup"]
                st.markdown(f"[{label} ↗]({url})")
            if panel["notes"]:
                st.caption(" · ".join(panel["notes"]))
            st.caption(f'as printed: {panel["raw_text"]}')


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------


def render_ledger(ledger: Ledger) -> None:
    """Draw one ledger. Import-safe, and refuses rather than lies."""
    st.markdown(theme.CSS, unsafe_allow_html=True)

    problem = integrity_problem(ledger)
    if problem is not None:
        st.error(f"This ledger cannot be displayed. {problem}", icon="⛔")
        return

    st.markdown(f"#### {ledger.document_name}")
    render_summary(ledger)
    st.divider()
    render_progress_strip(ledger)
    st.divider()
    render_worklist(ledger)
    st.divider()
    render_all_entries(ledger)


def available_ledgers() -> list[Path]:
    """Ledger JSON on disk, newest first, with the committed fixture last.

    The fixture is always offered so a fresh clone with no ``data/output/``
    still has something to render - R5, and the reason A2 could be built
    before P6 existed.
    """
    found = sorted(LEDGER_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if FIXTURE_LEDGER.exists():
        found.append(FIXTURE_LEDGER)
    return found


def render_sidebar() -> Path | None:
    with st.sidebar:
        st.markdown("### ForkTheSource")
        st.caption("Verifiability, never accusations.")

        options = available_ledgers()
        chosen: Path | None = None
        if options:
            chosen = st.selectbox(
                "Ledger",
                options,
                format_func=lambda p: p.name,
            )
        else:
            st.warning("No ledger JSON found.")

        st.divider()
        st.markdown("**Models**")
        for label, stage in (("extract", "extractor"), ("judge", "judge")):
            name = _configured_model(stage)
            st.caption(f'{label}: {name or "not configured"}')

        st.divider()
        st.markdown("**Upload a PDF**")
        st.file_uploader("PDF", type=["pdf"], disabled=True, label_visibility="collapsed")
        st.caption("pipeline wiring lands in A3")

        return chosen


def main() -> None:
    st.set_page_config(page_title="ForkTheSource", layout="wide")
    path = render_sidebar()
    if path is None:
        st.info("Point the sidebar at a ledger JSON to begin.")
        return
    try:
        ledger = load_ledger(path)
    except Exception as exc:
        st.error(f"Could not read {path.name}: {type(exc).__name__} — {exc}", icon="⛔")
        return
    render_ledger(ledger)


if __name__ == "__main__":
    main()
