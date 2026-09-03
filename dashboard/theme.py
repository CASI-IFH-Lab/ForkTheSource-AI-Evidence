"""Every colour, label and icon the dashboard uses, defined exactly once.

Two rules govern this file.

**The words are process states, never verdicts about people.** `needs_check`
reads as "Needs checking", not "Suspicious". `conflict` reads as "Conflict",
which describes the evidence disagreeing with the printed entry - it does not
describe the author. Nothing here, and nothing built from here, may use a
term from `config.yaml:banned_terms`; `tests/test_dashboard_data.py` scans
every string in this module against that list, read from settings rather
than copied.

**A colour is a claim.** `version_mismatch` is deliberately NOT red: a
preprint cited where the journal version exists is a correct citation with a
note, and colouring it red would manufacture the exact false alarm this
project exists to avoid. Only `conflict` and `retracted` get red.

Defined once so the counters, the chips, the worklist and the expanders
cannot drift apart - the failure mode being a status that is amber in the
summary and red three rows further down.
"""

from __future__ import annotations

from src.contract import INDICATORS, STATUSES

# ---------------------------------------------------------------------------
# Statuses
# ---------------------------------------------------------------------------

# order: worst first, so every list in the UI reads the same way down the page
STATUS_ORDER: tuple[str, ...] = ("conflict", "needs_check", "unresolvable", "verified")

STATUS_STYLE: dict[str, dict[str, str]] = {
    "verified": {
        "label": "Verified",
        "icon": "✓",
        "color": "#1a7f4b",
        "soft": "#e6f4ec",
        "blurb": "The resolved record matches the reference as printed.",
    },
    "needs_check": {
        "label": "Needs checking",
        "icon": "!",
        "color": "#b26a00",
        "soft": "#fdf1dd",
        "blurb": "Something does not line up, or the evidence is incomplete.",
    },
    "conflict": {
        "label": "Conflict",
        "icon": "×",
        "color": "#b3261e",
        "soft": "#fbe9e7",
        "blurb": "The evidence and the printed entry disagree in a way that matters.",
    },
    "unresolvable": {
        "label": "Unresolvable",
        "icon": "?",
        "color": "#5f6368",
        "soft": "#eceff1",
        "blurb": "No record was found, or too little of the entry survived to look up.",
    },
}


def status_style(status: str) -> dict[str, str]:
    """Style for a status, or a neutral grey for anything unrecognised.

    Falls back rather than raising: a dashboard that refuses to draw because
    it met a status it does not know is worse than one that draws it grey
    and labels it plainly. The counts guard in ``app.py`` is where a real
    inconsistency stops the page.
    """
    return STATUS_STYLE.get(
        status,
        {
            "label": str(status).replace("_", " ").capitalize(),
            "icon": "·",
            "color": "#5f6368",
            "soft": "#eceff1",
            "blurb": "",
        },
    )


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

INDICATOR_STYLE: dict[str, dict[str, str]] = {
    "retracted": {
        "label": "retracted",
        "color": "#b3261e",
        "soft": "#fbe9e7",
        "blurb": "The provider's record carries a retraction notice.",
    },
    "version_mismatch": {
        # Not red, and not a problem. See this module's docstring.
        "label": "version mismatch",
        "color": "#1a73e8",
        "soft": "#e8f0fe",
        "blurb": "A preprint and a published version both exist. The citation is fine; the note is for the reader.",
    },
    "doi_mismatch": {
        "label": "DOI mismatch",
        "color": "#b26a00",
        "soft": "#fdf1dd",
        "blurb": "The printed DOI and the resolved record's DOI are different strings.",
    },
    "duplicate_entry": {
        "label": "duplicate entry",
        "color": "#b26a00",
        "soft": "#fdf1dd",
        "blurb": "The same work appears more than once in this bibliography.",
    },
    "orphan": {
        "label": "orphan",
        "color": "#5f6368",
        "soft": "#eceff1",
        "blurb": "The entry resolved, but no claim in the body cites it.",
    },
    "malformed": {
        "label": "malformed",
        "color": "#5f6368",
        "soft": "#eceff1",
        "blurb": "The entry did not parse cleanly. That is missing information, not a disagreement.",
    },
}


def indicator_style(indicator: str) -> dict[str, str]:
    return INDICATOR_STYLE.get(
        indicator,
        {
            "label": str(indicator).replace("_", " "),
            "color": "#5f6368",
            "soft": "#eceff1",
            "blurb": "",
        },
    )


# ---------------------------------------------------------------------------
# doi_match is TRI-STATE and renders as three things
# ---------------------------------------------------------------------------

# D-034. Collapsing None into "mismatch" is the single most likely way this
# UI manufactures a false accusation, so the three states are defined here
# rather than reconstructed at each call site with a truthiness test.
DOI_MATCH_STATE: dict[str | None, dict[str, str]] = {
    True: {"label": "match", "icon": "✓", "color": "#1a7f4b"},
    False: {"label": "mismatch", "icon": "×", "color": "#b3261e"},
    None: {"label": "no DOI on one side", "icon": "–", "color": "#5f6368"},
}


def doi_match_state(value: bool | None) -> dict[str, str]:
    """Three states, never two. ``None`` is missing information, not disagreement."""
    if value is True:
        return DOI_MATCH_STATE[True]
    if value is False:
        return DOI_MATCH_STATE[False]
    return DOI_MATCH_STATE[None]


# ---------------------------------------------------------------------------
# The AIR progress strip
# ---------------------------------------------------------------------------

# The seven stages, in pipeline order. Two of them run on AIR, and those two
# are the beat at 0:20 of the demo where the platform becomes visible - the
# strip names the model, which is why `air` is a field and not a colour.
STAGES: tuple[dict[str, object], ...] = (
    {"key": "intake", "label": "intake", "air": False},
    {"key": "extract", "label": "extract", "air": True, "model_stage": "extractor"},
    {"key": "resolve", "label": "resolve", "air": False},
    {"key": "evidence", "label": "evidence", "air": False},
    {"key": "verdict", "label": "judge", "air": True, "model_stage": "judge"},
    {"key": "priority", "label": "priority", "air": False},
    {"key": "ledger", "label": "ledger", "air": False},
)

STAGE_KEYS: tuple[str, ...] = tuple(str(stage["key"]) for stage in STAGES)

AIR_ACCENT = "#5b2d90"  # ASU maroon-adjacent purple, used only for AIR stages
INK = "#202124"
MUTED = "#5f6368"
RULE = "#dadce0"
CANVAS = "#ffffff"

# ---------------------------------------------------------------------------
# Sanity: the vocabulary here is the contract's, not a second copy
# ---------------------------------------------------------------------------

assert set(STATUS_STYLE) == set(STATUSES), "theme statuses drifted from src.contract"
assert set(STATUS_ORDER) == set(STATUSES), "STATUS_ORDER drifted from src.contract"
assert set(INDICATOR_STYLE) == set(INDICATORS), "theme indicators drifted from src.contract"


CSS = f"""
<style>
  .ft-headline {{ font-size: 1.05rem; color: {MUTED}; margin: 0 0 .35rem 0; }}
  .ft-headline b {{ color: {INK}; font-size: 1.35rem; }}

  .ft-counter {{
    border: 1px solid {RULE}; border-radius: 10px; padding: .7rem .85rem .8rem .85rem;
    background: {CANVAS};
  }}
  .ft-counter .ft-top {{ display: flex; align-items: baseline; gap: .45rem; }}
  .ft-counter .ft-n {{ font-size: 2.1rem; font-weight: 700; line-height: 1; }}
  .ft-counter .ft-label {{ font-size: .82rem; font-weight: 600; letter-spacing: .01em; }}
  .ft-counter .ft-share {{ margin-left: auto; font-size: .78rem; color: {MUTED}; }}
  .ft-counter .ft-track {{
    height: 7px; border-radius: 4px; margin-top: .6rem; overflow: hidden;
  }}
  .ft-counter .ft-fill {{ height: 100%; border-radius: 4px; }}
  .ft-counter .ft-blurb {{ font-size: .72rem; color: {MUTED}; margin-top: .45rem; line-height: 1.3; }}

  .ft-chip {{
    display: inline-block; padding: .12rem .5rem; border-radius: 999px;
    font-size: .72rem; font-weight: 600; margin: 0 .3rem .3rem 0; white-space: nowrap;
  }}
</style>
"""
