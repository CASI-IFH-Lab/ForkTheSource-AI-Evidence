"""A2 - the numbers the dashboard shows, tested without Streamlit running.

Two kinds of test in here.

**Pure-data tests** call ``summary_rows``, ``worklist_rows``, ``signal_rows``
and friends directly. Those functions take a ``Ledger`` and return dicts, so
what the reviewer will see is assertable without a browser.

**Recorder tests** hand ``dashboard.app`` a stand-in for ``st`` that captures
every string the page would draw. That is what makes "no banned term anywhere
in the UI" a test rather than a promise, and it is how the counts guard is
shown to actually stop the page instead of merely returning early.

Nothing here needs a network, a key, or a running Streamlit server.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from dashboard import app, theme
from src import settings
from src.contract import (
    INDICATORS,
    STATUSES,
    Ledger,
    LedgerEntry,
    MatchEvidence,
    Reference,
    Verdict,
    load_ledger,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "ledger_fixture.json"

# Read through settings, never copied. Roy's release gate reads the same list
# from the same place; a private copy here would let this file pass while his
# fails on the same ledger (D-019).
BANNED_TERMS = tuple(term.lower() for term in settings.banned_terms())

# One drawn counter, identified by its class attribute rather than its bare
# class name - theme.CSS mentions ".ft-counter" too, and matching that would
# make the "no counters were drawn" assertion vacuously false.
COUNTER_MARKUP = 'class="ft-counter"'


@pytest.fixture()
def ledger() -> Ledger:
    return load_ledger(FIXTURE_PATH)


# ---------------------------------------------------------------------------
# The recorder - a stand-in for streamlit that remembers what it was told
# ---------------------------------------------------------------------------


class Recorder:
    """Captures every string the page draws. Also a context manager and a column.

    Returning ``self`` from ``columns``/``container``/``expander``/``sidebar``
    keeps the recorder deliberately flat: this file asserts on WHAT the page
    says, never on where it sits. Layout is the one thing a human has to look
    at, and pretending a test can check it would be worse than admitting it
    cannot.
    """

    def __init__(self) -> None:
        self.text: list[str] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []

    # -- capture ------------------------------------------------------------
    def _say(self, value) -> None:
        if value is not None:
            self.text.append(str(value))

    def markdown(self, body="", **kwargs) -> None:
        self._say(body)

    def caption(self, body="", **kwargs) -> None:
        self._say(body)

    def write(self, body="", **kwargs) -> None:
        self._say(body)

    def error(self, body="", **kwargs) -> None:
        self.errors.append(str(body))
        self._say(body)

    def warning(self, body="", **kwargs) -> None:
        self.warnings.append(str(body))
        self._say(body)

    def info(self, body="", **kwargs) -> None:
        self.infos.append(str(body))
        self._say(body)

    def metric(self, label, value, **kwargs) -> None:
        self._say(label)
        self._say(value)

    def divider(self) -> None:
        pass

    def set_page_config(self, **kwargs) -> None:
        pass

    # -- layout, all of which is just "me again" ----------------------------
    def columns(self, spec, **kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        return [self] * count

    def container(self, **kwargs):
        return self

    def expander(self, label, **kwargs):
        self._say(label)
        return self

    @property
    def sidebar(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    # -- widgets ------------------------------------------------------------
    def selectbox(self, label, options, **kwargs):
        self._say(label)
        return options[0] if options else None

    def file_uploader(self, label, **kwargs):
        self._say(label)
        return None

    # -- assertions ---------------------------------------------------------
    @property
    def all_text(self) -> str:
        return "\n".join(self.text)


@pytest.fixture()
def rec(monkeypatch) -> Recorder:
    recorder = Recorder()
    monkeypatch.setattr(app, "st", recorder)
    return recorder


# ---------------------------------------------------------------------------
# Row 1 - the summary
# ---------------------------------------------------------------------------


def test_summary_rows_cover_all_four_statuses_worst_first(ledger):
    rows = app.summary_rows(ledger)
    assert [row["status"] for row in rows] == list(theme.STATUS_ORDER)
    assert {row["status"] for row in rows} == set(STATUSES)


def test_summary_counts_come_from_the_contract_not_a_second_count(ledger):
    """The UI must not re-derive what B1's Ledger already computes."""
    rows = {row["status"]: row["count"] for row in app.summary_rows(ledger)}
    assert rows == ledger.summary_counts()
    assert sum(rows.values()) == len(ledger.entries)


def test_shares_sum_to_one(ledger):
    assert sum(row["share"] for row in app.summary_rows(ledger)) == pytest.approx(1.0)


def test_an_empty_ledger_does_not_divide_by_zero():
    rows = app.summary_rows(Ledger(document_name="empty.pdf"))
    assert [row["count"] for row in rows] == [0, 0, 0, 0]
    assert [row["share"] for row in rows] == [0.0, 0.0, 0.0, 0.0]


def test_headline_counts_everything_not_verified_as_worth_checking(ledger):
    head = app.headline(ledger)
    assert head["total"] == len(ledger.entries)
    assert head["worth_checking"] == head["total"] - ledger.summary_counts()["verified"]
    assert head["coverage"] == ledger.evidence_coverage()


def test_the_headline_claims_zero_accusations(rec, ledger):
    app.render_summary(ledger)
    assert "0</b> accusations" in rec.all_text


# ---------------------------------------------------------------------------
# The counts guard
# ---------------------------------------------------------------------------


class CorruptedLedger(Ledger):
    """A ledger whose counters disagree with its entries.

    The contract makes this state unreachable through normal construction —
    ``summary_counts()`` walks the entries, so it always sums to
    ``len(entries)``. That is exactly why the guard needs a test with teeth:
    it is defence in depth against a future change (a fifth status, a cached
    count, a partially-written ledger from a crashed run), and defence that
    has never been fired is not defence. Overriding the method is the
    smallest possible way to corrupt a real fixture.
    """

    def summary_counts(self) -> dict[str, int]:
        counts = super().summary_counts()
        counts["verified"] += 3
        return counts


def test_the_guard_trips_on_a_corrupted_copy_of_the_fixture(ledger):
    corrupted = CorruptedLedger(**ledger.model_dump())
    assert corrupted.counts_are_consistent() is False
    assert app.integrity_problem(corrupted) is not None
    assert app.integrity_problem(ledger) is None


def test_a_corrupted_ledger_shows_an_error_and_draws_no_counters(rec, ledger):
    """REFUSE to render, visibly. Not a blank page, not confident wrong numbers."""
    app.render_ledger(CorruptedLedger(**ledger.model_dump()))
    assert rec.errors, "a corrupted ledger must produce a visible error"
    assert "cannot be displayed" in rec.errors[0]
    # the stylesheet mentions .ft-counter; only a drawn counter carries the
    # class attribute, so match on that rather than on the bare name
    assert COUNTER_MARKUP not in rec.all_text, "counters were drawn anyway"


def test_a_sound_ledger_draws_four_counters_and_no_error(rec, ledger):
    app.render_ledger(ledger)
    assert rec.errors == []
    assert rec.all_text.count(COUNTER_MARKUP) == 4


# ---------------------------------------------------------------------------
# Row 2 - the AIR progress strip
# ---------------------------------------------------------------------------


def test_the_strip_has_the_seven_stages_in_pipeline_order(ledger):
    assert [chip["key"] for chip in app.progress_stages(ledger)] == list(theme.STAGE_KEYS)


def test_exactly_two_stages_are_air_stages(ledger):
    air = [chip for chip in app.progress_stages(ledger) if chip["air"]]
    assert [chip["key"] for chip in air] == ["extract", "verdict"]
    assert all(chip["model"] for chip in air), "an AIR stage must name its model"


def test_the_judge_chip_names_the_model_that_actually_ran(ledger):
    """Read off the ledger, not out of config: those differ when the gateway was down."""
    chip = next(c for c in app.progress_stages(ledger) if c["key"] == "verdict")
    assert chip["model"] == ledger.entries[0].verdict.judge_model
    assert chip["model_source"] == "as run"


def test_a_mixed_run_says_so_rather_than_picking_one(ledger):
    mixed = copy.deepcopy(ledger)
    mixed.entries[0].verdict = mixed.entries[0].verdict.model_copy(
        update={"judge_model": "fallback:rule_based"}
    )
    chip = next(c for c in app.progress_stages(mixed) if c["key"] == "verdict")
    assert chip["model"] == "2 models"


def test_the_extract_chip_falls_back_to_config(ledger):
    chip = next(c for c in app.progress_stages(ledger) if c["key"] == "extract")
    assert chip["model"] == settings.model_for("extractor")
    assert chip["model_source"] == "configured"


def test_a_fallback_run_is_announced_not_hidden(rec, ledger):
    degraded = copy.deepcopy(ledger)
    for entry in degraded.entries:
        entry.verdict = entry.verdict.model_copy(update={"judge_model": "fallback:stub"})
    app.render_progress_strip(degraded)
    assert rec.warnings, "a run that degraded must say so on screen"
    assert "without the gateway" in rec.warnings[0]


# ---------------------------------------------------------------------------
# Row 3 - the worklist
# ---------------------------------------------------------------------------


def test_the_worklist_uses_the_contracts_ordering(ledger):
    """-priority with a ref_id tie-break, so two runs give the same top three."""
    expected = [entry.reference.ref_id for entry in ledger.worklist()]
    assert [row["ref_id"] for row in app.worklist_rows(ledger)] == expected


def test_the_top_three_are_the_three_highest_priorities(ledger):
    rows = app.worklist_rows(ledger, 3)
    assert len(rows) == 3
    assert [row["priority"] for row in rows] == sorted(
        (row["priority"] for row in rows), reverse=True
    )


def test_two_calls_produce_identical_order(ledger):
    """The determinism the metrics table claims, at the UI layer."""
    once = [row["ref_id"] for row in app.worklist_rows(ledger)]
    twice = [row["ref_id"] for row in app.worklist_rows(load_ledger(FIXTURE_PATH))]
    assert once == twice


# ---------------------------------------------------------------------------
# doi_match is three states, and this is the test that keeps it that way
# ---------------------------------------------------------------------------


def test_doi_match_renders_three_distinct_states():
    labels = {
        theme.doi_match_state(True)["label"],
        theme.doi_match_state(False)["label"],
        theme.doi_match_state(None)["label"],
    }
    assert len(labels) == 3


def test_no_doi_is_never_shown_as_a_mismatch():
    """D-034. Collapsing None into False is how this UI would invent an accusation."""
    missing = theme.doi_match_state(None)
    mismatch = theme.doi_match_state(False)
    assert missing["label"] != mismatch["label"]
    assert missing["color"] != mismatch["color"]
    assert "mismatch" not in missing["label"]


@pytest.mark.parametrize(
    "value,expected",
    [(True, "match"), (False, "mismatch"), (None, "no DOI on one side")],
)
def test_the_signal_table_shows_the_doi_state_in_words(ledger, value, expected):
    entry = ledger.entries[0].model_copy(deep=True)
    entry.evidence = entry.evidence.model_copy(update={"doi_match": value})
    doi_row = next(row for row in app.signal_rows(entry) if row["name"] == "DOI")
    assert expected in doi_row["value"]


def test_a_missing_year_delta_reads_as_not_comparable(ledger):
    entry = next(e for e in ledger.entries if e.evidence.year_delta is None)
    year_row = next(row for row in app.signal_rows(entry) if row["name"] == "year difference")
    assert year_row["value"] == "not comparable"


# ---------------------------------------------------------------------------
# version_mismatch is not a conflict, and the colour must not say it is
# ---------------------------------------------------------------------------


def test_version_mismatch_is_not_coloured_like_a_conflict():
    """A preprint cited where the journal version exists is a correct citation."""
    assert (
        theme.indicator_style("version_mismatch")["color"]
        != theme.status_style("conflict")["color"]
    )
    assert theme.indicator_style("version_mismatch")["color"] != "#b3261e"


def test_only_retracted_shares_the_conflict_red():
    red = theme.status_style("conflict")["color"]
    reds = [name for name in INDICATORS if theme.indicator_style(name)["color"] == red]
    assert reds == ["retracted"]


# ---------------------------------------------------------------------------
# The lookup link never invents an identifier
# ---------------------------------------------------------------------------


def test_lookup_prefers_the_providers_own_url(ledger):
    entry = next(e for e in ledger.entries if e.evidence.resolved and e.evidence.resolved.url)
    label, url = app.lookup_url(entry)
    assert url == entry.evidence.resolved.url


def test_lookup_falls_back_to_the_doi_then_arxiv_then_a_title_search():
    def entry_with(**reference_kwargs) -> LedgerEntry:
        ref = Reference(ref_id="R01", raw_text="whatever", **reference_kwargs)
        return LedgerEntry(
            reference=ref,
            evidence=MatchEvidence(ref_id="R01"),
            verdict=Verdict(
                ref_id="R01",
                status="unresolvable",
                confidence=0.3,
                rationale="Nothing resolved.",
                judge_model="fallback:stub",
            ),
        )

    assert "doi.org/10.1234/x" in app.lookup_url(entry_with(doi="10.1234/x"))[1]
    assert "arxiv.org/abs/2101.00001" in app.lookup_url(entry_with(arxiv_id="2101.00001"))[1]
    assert "scholar.google" in app.lookup_url(entry_with(title="A Title"))[1]


def test_an_entry_with_nothing_to_look_up_offers_no_link():
    """Better no link than a link we made up."""
    entry = LedgerEntry(
        reference=Reference(ref_id="R01", raw_text="[7] ...unreadable..."),
        evidence=MatchEvidence(ref_id="R01", indicators=["malformed"]),
        verdict=Verdict(
            ref_id="R01",
            status="unresolvable",
            confidence=0.3,
            rationale="The entry did not parse.",
            judge_model="fallback:stub",
        ),
    )
    assert app.lookup_url(entry) is None


# ---------------------------------------------------------------------------
# As printed versus resolved
# ---------------------------------------------------------------------------


def test_both_columns_carry_the_same_keys_so_the_rows_line_up(ledger):
    for entry in ledger.entries:
        panel = app.entry_panel(entry)
        assert panel["printed"].keys() == panel["resolved"].keys()


def test_an_unresolved_entry_says_so_rather_than_showing_blanks(ledger):
    entry = next(e for e in ledger.entries if e.evidence.resolved is None)
    panel = app.entry_panel(entry)
    assert panel["has_resolved"] is False
    assert panel["provider"] is None
    assert all(value is None for value in panel["resolved"].values())


# ---------------------------------------------------------------------------
# Shapes of ledger that must not break the layout
# ---------------------------------------------------------------------------


def _retag(ledger: Ledger, status: str) -> Ledger:
    clone = copy.deepcopy(ledger)
    for entry in clone.entries:
        indicators = list(entry.evidence.indicators)
        if status != "conflict" and "retracted" in indicators:
            # the retracted indicator is only legal alongside a retracted
            # source, and MatchEvidence enforces that pairing
            continue
        entry.verdict = entry.verdict.model_copy(update={"status": status})
    return clone


@pytest.mark.parametrize("status", list(STATUSES))
def test_a_ledger_of_one_status_renders(rec, ledger, status):
    app.render_ledger(_retag(ledger, status))
    assert rec.errors == []


def test_an_empty_ledger_renders_without_an_error(rec):
    app.render_ledger(Ledger(document_name="empty.pdf"))
    assert rec.errors == []
    assert rec.infos, "an empty ledger should say it is empty"


def test_a_verdict_with_no_checks_says_so_instead_of_leaving_a_gap(rec, ledger):
    """Verdict.checks has max 3 and no minimum - a fallback verdict carries none."""
    stripped = copy.deepcopy(ledger)
    for entry in stripped.entries:
        entry.verdict = entry.verdict.model_copy(update={"checks": []})
    app.render_ledger(stripped)
    assert "no suggested checks" in rec.all_text


# ---------------------------------------------------------------------------
# The language rule, over everything the page can draw
# ---------------------------------------------------------------------------


def _assert_clean(text: str, where: str) -> None:
    lowered = text.lower()
    hits = [term for term in BANNED_TERMS if term in lowered]
    assert not hits, f"banned term(s) {hits} in {where}"


def test_no_banned_term_in_the_theme():
    strings = []
    for style in list(theme.STATUS_STYLE.values()) + list(theme.INDICATOR_STYLE.values()):
        strings.extend(str(value) for value in style.values())
    strings.extend(str(state["label"]) for state in theme.DOI_MATCH_STATE.values())
    strings.extend(str(stage["label"]) for stage in theme.STAGES)
    _assert_clean("\n".join(strings), "dashboard/theme.py")


def test_no_banned_term_anywhere_the_page_draws(rec, ledger):
    app.render_ledger(ledger)
    _assert_clean(rec.all_text, "the rendered page")


def test_no_banned_term_on_the_refusal_path(rec, ledger):
    app.render_ledger(CorruptedLedger(**ledger.model_dump()))
    _assert_clean(rec.all_text, "the counts-guard error state")


def test_no_banned_term_in_the_sidebar(rec):
    app.render_sidebar()
    _assert_clean(rec.all_text, "the sidebar")


def test_the_labels_are_process_states_not_judgements():
    labels = " ".join(style["label"].lower() for style in theme.STATUS_STYLE.values())
    for word in ("suspicious", "bad", "wrong", "dubious", "questionable"):
        assert word not in labels
    assert theme.status_style("needs_check")["label"] == "Needs checking"


# ---------------------------------------------------------------------------
# Lane isolation - A2's own DoD box, asserted here as well as in test_layout
# ---------------------------------------------------------------------------


def test_the_dashboard_imports_nothing_from_ritiks_lane():
    import ast

    forbidden = ("src.ingest", "src.resolvers", "src.matching", "src.pipeline")
    offenders = []
    for path in (REPO_ROOT / "dashboard").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            offenders += [
                f"{path.name} imports {name}"
                for name in names
                if any(name == f or name.startswith(f + ".") for f in forbidden)
            ]
    assert not offenders, offenders


def test_render_ledger_is_importable_without_streamlit_running(ledger):
    """No monkeypatching here: the real streamlit, in bare mode, must not raise."""
    import dashboard.app as real_app

    real_app.render_ledger(ledger)


def test_the_theme_vocabulary_is_the_contracts(ledger):
    assert set(theme.STATUS_STYLE) == set(STATUSES)
    assert set(theme.INDICATOR_STYLE) == set(INDICATORS)


def test_available_ledgers_always_offers_the_committed_fixture():
    """A fresh clone with no data/output/ still has something to render - R5."""
    assert FIXTURE_PATH in app.available_ledgers()


def _without_cited_text(drawn: str) -> str:
    """Strip everything the page drew that came from a CITED PAPER, not from us.

    The banned-terms rule governs the language WE produce about a paper. It does not
    govern a paper's own title, and a real reference in `plos_sample.pdf` is titled
    "Reproducibility: fraud is not the big problem" - so the moment P6 wrote a real
    ledger into `data/output/`, this test went red on a title we did not write and must
    not censor. Refusing to render that title would be a worse failure than the one the
    rule exists to prevent.

    Only the live-page test needs this, because it renders whichever ledger the sidebar
    picks first - a real one on any machine that has run the pipeline. The recorder
    tests above run against the committed fixture and scan the drawn text whole, which
    is where a banned term in OUR OWN copy still gets caught.
    """
    from src.contract import load_ledger

    options = app.available_ledgers()
    if not options:
        return drawn
    # The sidebar's selectbox defaults to the first option, so this is what rendered.
    ledger = load_ledger(options[0])
    for entry in ledger.entries:
        ref = entry.reference
        for source in (ref.title, ref.raw_text, ref.venue, *ref.authors):
            if source:
                drawn = drawn.replace(source, " ")
    return drawn


def test_the_whole_page_runs_end_to_end():
    """`streamlit run dashboard/app.py`, executed by Streamlit's own harness.

    The recorder tests above prove the page says the right things; this one
    proves the real script runs at all — set_page_config, the sidebar, the
    widgets and every layout call, under a real ScriptRunContext. A page that
    raises halfway down still passes a recorder test and shows the reviewer
    half a dashboard.

    Assertions stay shape-level on purpose: whichever ledger the sidebar picks
    first depends on whether ``data/output/`` exists on this machine, and a
    test that assumes the fixture would go red the day P6 writes a real one.
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(REPO_ROOT / "dashboard" / "app.py"), default_timeout=60).run()

    assert not at.exception, [str(e.value) for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    assert [box.label for box in at.selectbox] == ["Ledger"]

    drawn = "\n".join(block.value for block in at.markdown)
    assert drawn.count(COUNTER_MARKUP) == 4, "the four counters did not all render"
    _assert_clean(_without_cited_text(drawn), "the live-rendered page")
