"""Tests for the progress-file parser in scripts/update_status.py.

Scope is deliberately narrow: the parser and the open-items rule. The rest of the
tool is git and subprocess plumbing that these tests would only re-assert by mocking,
and the properties that actually matter about it - never crashes, exits 0 - are
covered here by feeding the parser and the report builder garbage.

The parser is the part with real logic and real consequences: if it silently drops a
BLOCKED block, somebody sits idle for an hour and STATUS.md says everything is fine.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _load_tool():
    """Load scripts/update_status.py by path.

    `scripts/` is not a package and should not become one just to be testable, so
    load the file directly rather than adding an __init__.py to a directory of
    standalone scripts.
    """
    path = REPO / "scripts" / "update_status.py"
    spec = importlib.util.spec_from_file_location("_update_status_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


WELL_FORMED = """\
## 1:05 — P2 MERGED
branch: ritik/p2-resolvers -> main @ 4f1a9c2
tests: 148 passed
publishes: resolve(ref: Reference, config: dict | None = None) -> ResolvedSource | None
notes: Crossref first, then arXiv.
next: P3 evidence builder, ETA 2:10
"""


# ---------------------------------------------------------------------------
# the happy path
# ---------------------------------------------------------------------------
def test_well_formed_block_parses(tool):
    blocks = tool.parse_progress_text(WELL_FORMED, person="ritik")
    assert len(blocks) == 1
    block = blocks[0]
    assert block.ok
    assert block.person == "ritik"
    assert block.clock == "1:05"
    assert block.module == "P2"
    assert block.status == "MERGED"
    assert block.owner is None
    fields = dict(block.fields)
    assert fields["branch"] == "ritik/p2-resolvers -> main @ 4f1a9c2"
    assert fields["tests"] == "148 passed"
    # A signature with colons in it must survive intact - the field split is on the
    # FIRST colon only, or every `publishes:` line in the repo gets truncated.
    assert fields["publishes"].startswith("resolve(ref: Reference")
    assert fields["publishes"].endswith("ResolvedSource | None")
    assert fields["next"] == "P3 evidence builder, ETA 2:10"


def test_clock_sorts_numerically_not_lexically(tool):
    blocks = tool.parse_progress_text("## 2:40 — P3 READY\n## 10:05 — P4 READY\n")
    assert [b.clock_minutes for b in blocks] == [160, 605]


def test_every_status_word_is_recognised(tool):
    text = "".join(f"## 0:0{i % 10} — M{i} {word}\n" for i, word in enumerate(tool.STATUS_WORDS))
    blocks = tool.parse_progress_text(text)
    assert [b.status for b in blocks] == list(tool.STATUS_WORDS)
    assert all(b.ok for b in blocks)


def test_plain_hyphen_separator_is_accepted(tool):
    (block,) = tool.parse_progress_text("## 0:15 - S0 STARTED\ntests: 131 passed\n")
    assert (block.module, block.status) == ("S0", "STARTED")


def test_fenced_blocks_are_skipped(tool):
    """The worked example in every progress file lives in a fence and must not report."""
    text = "# progress\n```\n## 9:99 — FAKE MERGED\ntests: 0 passed\n```\n" + WELL_FORMED
    blocks = tool.parse_progress_text(text)
    assert [b.module for b in blocks] == ["P2"]


def test_later_heading_ends_a_block(tool):
    text = "## 0:15 — S0 STARTED\ntests: 131 passed\n\n### notes\nnext: not mine\n"
    (block,) = tool.parse_progress_text(text)
    assert dict(block.fields) == {"tests": "131 passed"}


# ---------------------------------------------------------------------------
# requests and blockers - the section people actually read
# ---------------------------------------------------------------------------
REQUEST = """\
## 1:30 — REQUEST -> @arsha
NEED: Verdict.rationale widened to str | None in src/contract.py
WHY: rule_based_status() has no rationale for the trivially-verified case.
UNBLOCKED MEANWHILE BY: passing the literal "rule: exact DOI match".
BLOCKS ME AT: 2:30
"""


def test_request_block_parses_with_its_owner(tool):
    (block,) = tool.parse_progress_text(REQUEST, person="ritik")
    assert block.status == "REQUEST"
    assert block.owner == "arsha"
    # A request heading names no module of its own, so REQUEST is its module. That is
    # what lets a later "REQUEST MERGED" retire it in an append-only file.
    assert block.module == "REQUEST"
    fields = dict(block.fields)
    assert fields["NEED"].startswith("Verdict.rationale widened")
    assert fields["BLOCKS ME AT"] == "2:30"
    assert block.label() == "REQUEST -> @arsha"


def test_request_is_picked_up_as_open(tool):
    per_person = {"ritik": tool.parse_progress_text(WELL_FORMED + "\n" + REQUEST, person="ritik")}
    items = tool.open_items(per_person)
    assert [(b.status, b.owner) for b in items] == [("REQUEST", "arsha")]


def test_blocked_is_picked_up_as_open(tool):
    text = "## 1:00 — P3 BLOCKED\nnotes: waiting on the judge contract\n"
    per_person = {"roy": tool.parse_progress_text(text, person="roy")}
    (item,) = tool.open_items(per_person)
    assert (item.module, item.status, item.person) == ("P3", "BLOCKED", "roy")


def test_later_merged_for_the_same_module_retires_it(tool):
    text = "## 1:00 — P3 BLOCKED\nnotes: waiting\n\n## 2:05 — P3 MERGED\ntests: 150 passed\n"
    per_person = {"roy": tool.parse_progress_text(text, person="roy")}
    assert tool.open_items(per_person) == []


def test_request_merged_retires_a_request(tool):
    text = REQUEST + "\n## 2:20 — REQUEST MERGED\nnotes: arsha landed it\n"
    per_person = {"ritik": tool.parse_progress_text(text, person="ritik")}
    assert tool.open_items(per_person) == []


def test_merged_for_a_different_module_does_not_retire_it(tool):
    """Err toward showing a stale request, never toward hiding a live one."""
    text = "## 1:00 — P3 BLOCKED\nnotes: waiting\n\n## 2:05 — P4 MERGED\ntests: 150 passed\n"
    per_person = {"roy": tool.parse_progress_text(text, person="roy")}
    assert [b.module for b in tool.open_items(per_person)] == ["P3"]


def test_an_earlier_merged_does_not_retire_a_later_block(tool):
    """Only a MERGED that comes AFTER the blocker counts - order is the whole signal."""
    text = "## 1:00 — P3 MERGED\ntests: 140 passed\n\n## 2:05 — P3 BLOCKED\nnotes: regressed\n"
    per_person = {"roy": tool.parse_progress_text(text, person="roy")}
    assert [b.status for b in tool.open_items(per_person)] == ["BLOCKED"]


def test_another_persons_merged_does_not_retire_your_blocker(tool):
    blocked = "## 1:00 — P3 BLOCKED\nnotes: waiting\n"
    merged = "## 2:05 — P3 MERGED\ntests: 150 passed\n"
    per_person = {
        "roy": tool.parse_progress_text(blocked, person="roy"),
        "arsha": tool.parse_progress_text(merged, person="arsha"),
    }
    assert [b.person for b in tool.open_items(per_person)] == ["roy"]


def test_open_items_are_ordered_oldest_first(tool):
    per_person = {
        "roy": tool.parse_progress_text("## 3:00 — P5 BLOCKED\nnotes: b\n", person="roy"),
        "arsha": tool.parse_progress_text("## 1:00 — A2 BLOCKED\nnotes: a\n", person="arsha"),
    }
    assert [b.clock for b in tool.open_items(per_person)] == ["1:00", "3:00"]


# ---------------------------------------------------------------------------
# garbage in, report out - the parser must never be the reason the tool dies
# ---------------------------------------------------------------------------
MALFORMED = """\
## not even close
## 1:00 — P2 FINISHED
## — P2 MERGED
##1:00—P2 MERGED
## 1:00 — merged
branch: dangling field with no block
tests:
## 1:00 — P2 STARTED
: leading colon
random prose that is not a field
publishes: fine
"""


def test_malformed_blocks_do_not_raise(tool):
    blocks = tool.parse_progress_text(MALFORMED, person="ritik")
    # The one recognisable block is found; the rest are recorded, not fatal.
    ok = [b for b in blocks if b.ok]
    assert [(b.module, b.status) for b in ok] == [("P2", "STARTED")]
    assert dict(ok[0].fields) == {"publishes": "fine"}
    assert any(not b.ok for b in blocks), "unparseable headings should still be recorded"


def test_malformed_headings_are_reported_not_silently_dropped(tool):
    """A block that does not parse has to be visible, or people trust a lie."""
    per_person = {"ritik": tool.parse_progress_text(MALFORMED, person="ritik")}
    rendered = "\n".join(tool.section_open(per_person, []))
    assert "unparseable block heading" in rendered
    assert "progress/ritik.md:" in rendered


def test_unknown_status_word_is_not_treated_as_a_status(tool):
    (block,) = tool.parse_progress_text("## 1:00 — P2 FINISHED\ntests: 1 passed\n")
    assert block.status is None
    assert not block.ok


def test_empty_and_binaryish_input_parse_to_nothing(tool):
    for text in ("", "\n\n\n", "no headings here at all", "\x00\x01 junk", "## \n"):
        assert tool.parse_progress_text(text) == []


def test_unterminated_fence_swallows_the_rest_rather_than_crashing(tool):
    blocks = tool.parse_progress_text("```\n" + WELL_FORMED)
    assert blocks == []


def test_open_items_survives_a_file_of_only_garbage(tool):
    per_person = {"ritik": tool.parse_progress_text(MALFORMED, person="ritik")}
    assert tool.open_items(per_person) == []


def test_section_lanes_reports_a_person_with_no_parseable_block(tool):
    per_person = {"roy": tool.parse_progress_text("## nope\n", person="roy")}
    rendered = "\n".join(tool.section_lanes(per_person))
    assert "### roy" in rendered
    assert "Nothing to report" in rendered


def test_empty_open_section_says_so_explicitly(tool):
    """An empty heading reads like the script broke."""
    rendered = "\n".join(tool.section_open({}, []))
    assert "None — nobody is waiting." in rendered


# ---------------------------------------------------------------------------
# the properties the whole tool has to hold
# ---------------------------------------------------------------------------
def test_normalize_ignores_only_the_timestamp(tool):
    a = "# STATUS — generated 2026-09-03 17:55 UTC, main @ abc1234\n\nbody\n"
    b = "# STATUS — generated 2026-09-03 18:40 UTC, main @ abc1234\n\nbody\n"
    c = "# STATUS — generated 2026-09-03 18:40 UTC, main @ deadbee\n\nbody\n"
    assert tool._normalize(a) == tool._normalize(b), "timestamp must not count as a change"
    assert tool._normalize(a) != tool._normalize(c), "the sha must count as a change"


def test_stdout_mode_never_writes_and_exits_zero(tool, capsys):
    assert tool.main(["--stdout"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# STATUS — generated ")
    for heading in (
        "## ⚠️ OPEN REQUESTS AND BLOCKERS",
        "## What is on main",
        "## In flight",
        "## Published interfaces",
        "## Latest from each lane",
        "## Tests:",
    ):
        assert heading in out, f"missing section: {heading}"


def test_sections_appear_in_the_agreed_order(tool, capsys):
    tool.main(["--stdout"])
    out = capsys.readouterr().out
    order = [
        "## ⚠️ OPEN REQUESTS AND BLOCKERS",
        "## What is on main",
        "## In flight",
        "## Published interfaces",
        "## Latest from each lane",
        "## Tests:",
    ]
    positions = [out.index(h) for h in order]
    assert positions == sorted(positions), "blockers first, tests last"


def test_a_section_that_explodes_does_not_take_the_report_down(tool):
    def boom():
        raise RuntimeError("git ate itself")

    rendered = "\n".join(tool._safe(boom, "## What is on main"))
    assert "## What is on main" in rendered
    assert "RuntimeError" in rendered


def test_the_published_interface_probe_never_raises(tool):
    results = tool.probe_interfaces()
    assert len(results) == len(tool.PUBLISHED)
    for module, mark, marks, _note in results:
        assert mark in (tool.YES, tool.NO, tool.WARN), module
        assert marks, f"{module} has no symbols listed"
        assert all(m in (tool.YES, tool.NO) for _s, m in marks), module


def test_the_progress_directory_matches_the_team(tool):
    """Three lanes, three files. A missing file means somebody has nowhere to report."""
    per_person, notes = tool.read_progress()
    assert notes == []
    assert set(per_person) == {"ritik", "arsha", "roy"}


def test_shared_format_doc_is_not_parsed_as_a_person(tool):
    per_person, _ = tool.read_progress()
    assert "_FORMAT" not in per_person


def test_branch_age_is_bucketed_not_minute_precise(tool):
    """Minute precision here would rewrite a tracked STATUS.md once a minute forever."""
    assert tool._age(0) == "<15m"
    assert tool._age(60 * 14) == "<15m"
    assert tool._age(60 * 22) == tool._age(60 * 23) == "15m"
    assert tool._age(60 * 59) == "45m"
    assert tool._age(3600) == "1h"
    assert tool._age(3600 + 60 * 20) == "1h 15m"
    assert tool._age(3600 * 25) == "1d 1h"
    assert tool._age(3600 * 48) == "2d"
    assert tool._age(-5) == "<15m", "a clock-skewed future commit must not crash"
