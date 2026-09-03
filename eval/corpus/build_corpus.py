"""Build the Phase 1 eval corpus from the untouched originals in originals/.

Reproducible: delete paper1.pdf and control.pdf, run this, get them back byte-for-byte
equivalent in content. Nothing here reads or writes anything outside eval/.

    python eval/corpus/build_corpus.py            # build both, print the verification report
    python eval/corpus/build_corpus.py --verify   # rebuild into a temp dir and report only

Route (see docs/decisions.md D-303): the pipeline consumes extracted text, not PDF
internals, so the spiked paper is REBUILT single-column with reportlab from the original's
extracted text rather than edited in the PDF text layer. The bibliography is a curated
30-entry selection of the original's 282, renumbered contiguously, with every in-text
bracket remapped.

Requires reportlab, which is not in requirements.txt (Ritik's file) -- REQUEST filed in
progress/roy.md. Install locally with: pip install reportlab
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
import warnings

warnings.filterwarnings("ignore")

import pdfplumber
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINALS = os.path.join(HERE, "originals")

# The text layer of both originals loses inter-word spaces at pdfplumber's default
# x_tolerance (3.0). 1.5 recovers them; established by inspection, do not lower.
X_TOL = 1.5

# --------------------------------------------------------------------------------------
# The spiked paper: which of the original's 282 references survive, in original numbering.
# Curated, not a prefix -- a prefix loses every 10.48550 row (lowest is [41]) and the
# version-pair candidate ([49]). See D-303.
# --------------------------------------------------------------------------------------
KEEP = [1, 6, 8, 12, 13, 15, 16, 18, 19, 20, 21, 22, 23, 26, 28, 31, 33,
        42, 43, 44, 48, 49, 52, 53, 54, 55, 56, 113]

# Added entries, keyed by the original reference number they are inserted AFTER.
# D04: an entry no registry holds -- no DOI, no arXiv ID (defect_catalog.md section 2).
# D16: a real retracted paper, metadata read from the OpenAlex record for its DOI.
ADDED = {
    44: ("D04",
         "R. Lindner, P. Vasquez, K. Ohara, Entropy-based regularisation for robust "
         "feature selection in high-dimensional classification, Entropy 24 (9) (2022) 1231."),
    48: ("D16",
         "B. Saravanan, V. Mohanraj, J. Senthilkumar, A fuzzy entropy technique for "
         "dimensionality reduction in recommender systems using deep learning, "
         "Soft Computing 23 (8) (2019) 2575\u20132583. doi:10.1007/s00500-019-03807-9."),
}

# Reference-text injections, keyed by original reference number.
# (defect_id, pattern, replacement) applied to the cleaned reference text.
INJECT = {
    15: ("D07", r"Vol\.\s*1,\s*1961", "Vol. 1, 1963"),
    21: ("D01", r"doi:10\.1103/physreve\.71\.021906", "doi:10.1137/S0097539796300921"),
    49: ("D20",
         r"Information\s+Sciences\s+421\s*\(2017\)\s*254\u2013271\.\s*"
         r"doi:10\.48550/\s*arXiv\.1705\.01601\.",
         "arXiv preprint (2017)."),
}

# D14 is a body-only edit: this reference's single in-text marker is deleted and its
# reference text is left byte-identical.
ORPHAN_OLD = 55

# In-text markers for the two ADDED entries. Every slot inherits a bracket the remap
# deletes anyway -- each host sentence cites a reference that is not in KEEP -- so the
# body's bracket count does not change on their account. No slot names an author or a
# year, which would move a real attribution onto an added entry.
#   D04 gets three (D-027: its priority must clear the clean-unresolvable floor, which
#       needs usage saturated at three citing claims).
#   D16 gets one (defect_catalog.md section 7: cited once in the body).
ADDED_MARKERS = {
    "D04": [
        (r"(has\s+been\s+proposed\s+in\s*)\[38\]", "p7  differential entropy / feature selection"),
        (r"(Max-entropy\s+is\s+used\s+in\s*)\[193\]", "p17 max-entropy / feature extraction"),
        (r"(each\s+feature\s+in\s+Picture\s+Fuzzy\s+Sets\s*)\[110\]",
         "p11 fuzzy entropy / feature selection"),
    ],
    "D16": [
        (r"(robustness\s+against\s+outliers\s+in\s+clustering\s+techniques\s+in\s*)\[106\]",
         "p11 fuzzy entropy / clustering"),
    ],
}

CONTROL_KEEP_N = 30  # the control is a straight prefix, no renumbering needed

PROVENANCE = {
    "paper1": (
        "Modified copy for citation-provenance evaluation. Original: arXiv:2503.02921, "
        "CC-BY 4.0. The bibliography is a 30-entry curated selection of the original's 282, "
        "renumbered contiguously, and six entries or their in-text markers are altered. "
        "The untouched original is eval/corpus/originals/2503.02921.pdf."
    ),
    "control": (
        "Modified copy for citation-provenance evaluation. Original: arXiv:2410.12660, "
        "CC-BY 4.0. The bibliography is the original's first 30 entries, unaltered. "
        "No reference or in-text marker has been changed. "
        "The untouched original is eval/corpus/originals/2410.12660.pdf."
    ),
}

REF_HEAD = re.compile(r"^\s*(references|bibliography)\s*$", re.I)
MARKER = re.compile(r"^\s*\[(\d{1,3})\]\s*\S")
BRACKET = re.compile(r"\[\s*\d{1,3}(?:\s*,\s*\d{1,3})*\s*\]")


# --------------------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------------------
def extract_pages(path: str) -> list[str]:
    with pdfplumber.open(path) as pdf:
        return [(p.extract_text(x_tolerance=X_TOL) or "") for p in pdf.pages]


def split_front_body_refs(pages: list[str]) -> tuple[str, str, str]:
    """Return (front_matter, body, reference_block) as raw line-joined text."""
    lines = "\n".join(pages).split("\n")
    heads = [i for i, ln in enumerate(lines) if REF_HEAD.match(ln.strip())]
    if not heads:
        raise RuntimeError("no References heading found -- extraction changed")
    ref_start = heads[-1]
    abs_at = next((i for i, ln in enumerate(lines) if ln.strip().upper() == "ABSTRACT"), None)
    front_end = abs_at if abs_at is not None else 0
    return ("\n".join(lines[:front_end]),
            "\n".join(lines[front_end:ref_start]),
            "\n".join(lines[ref_start + 1:]))


def strip_running_heads(text: str, title_words: list[str]) -> str:
    """Drop running headers, bare page numbers, and page-number+title footers."""
    key = "".join(w.lower() for w in title_words)
    out = []
    for ln in text.split("\n"):
        s = ln.strip()
        flat = "".join(s.lower().split())
        if not s:
            continue
        if re.fullmatch(r"[\d\s]{1,6}", s):     # bare page numbers, incl. digit-spaced
            continue
        if flat == key or flat.startswith(key):
            continue
        m = re.match(r"^(\d{1,3})\s+(.*)$", s)
        if m and "".join(m.group(2).lower().split()).startswith(key):
            continue
        out.append(s)
    return "\n".join(out)


# A hyphen before one of these is a suspended hyphen ("Amplitude- and fluctuation-based"),
# not a word the PDF broke across a line. Joining it corrupts the title, and a corrupted
# title on a clean row shows up as a false alarm that is the corpus's fault, not P5's.
SUSPENDED = r"(?:and|or|nor|to|based|free|like|type|specific|dependent|driven)\b"


def dehyphenate(s: str) -> str:
    """Rejoin words the PDF broke across a line with a hyphen, leaving suspended ones."""
    return re.sub(r"(?<=[a-z])-\s+(?!" + SUSPENDED + r")(?=[a-z])", "", s)


def fix_dois(s: str) -> str:
    """Rejoin DOIs the original line-wrapped mid-string.

    The original prints "doi:10.3390/e10030261"; its text layer wraps after the slash and
    yields "doi:10.3390/ e10030261". Left alone the entry carries an unparseable
    identifier, and a clean row with a malformed DOI is an eval result nobody can explain.
    """
    s = re.sub(r"\bdoi:\s+", "doi:", s, flags=re.I)
    s = re.sub(r"(10\.\d{4,9}/)\s+(?=[A-Za-z0-9])", r"\1", s)
    # A wrap further inside the suffix: "10.1021/acs.chemrev. 9b00829". Only rejoined when
    # what follows looks like a suffix continuation (digit then 3+ alphanumerics, no space),
    # so a DOI that legitimately ends a sentence is never glued to the next word.
    s = re.sub(r"(10\.\d{4,9}/\S*?)\.\s+(?=\d[A-Za-z0-9]{3,}\b)", r"\1.", s)
    return s


def fix_accents(s: str) -> str:
    """Recompose accents the text layer emits as spacing characters.

    The original renders "Smieja" as S + U+00B4 (spacing acute) rather than U+015A. Left
    alone it lowers author overlap against the registry record, which would flip D20's
    expected `verified` to `needs_check` for a reason that has nothing to do with the
    defect. This restores what the paper actually prints; it is a fidelity repair, not an
    edit to the citation.
    """
    for spacing, combining in [("´", "́"), ("ˇ", "̌"),
                               ("¨", "̈"), ("˘", "̆"),
                               ("˜", "̃")]:
        s = re.sub(r"([A-Za-z])" + spacing,
                   lambda m: unicodedata.normalize("NFC", m.group(1) + combining), s)
    return unicodedata.normalize("NFC", s)


def parse_references(block: str, title_words: list[str]) -> dict[int, str]:
    """Split a [n]-numbered reference block into {number: cleaned text}."""
    block = strip_running_heads(block, title_words)
    refs: dict[int, str] = {}
    cur_n, cur = None, []
    for ln in block.split("\n"):
        m = MARKER.match(ln)
        if m:
            if cur_n is not None:
                refs[cur_n] = " ".join(cur)
            cur_n = int(m.group(1))
            cur = [ln.strip()[m.end(1) + 1:].strip()]
        elif cur_n is not None:
            cur.append(ln.strip())
    if cur_n is not None:
        refs[cur_n] = " ".join(cur)
    # keep only the monotonic 1..N run, so stray bracketed text cannot inject an entry
    clean, expect = {}, 1
    for n in sorted(refs):
        if n == expect:
            clean[n] = fix_dois(fix_accents(dehyphenate(re.sub(r"\s+", " ", refs[n])).strip()))
            expect += 1
    return clean


# --------------------------------------------------------------------------------------
# renumbering and remapping
# --------------------------------------------------------------------------------------
def build_slots() -> list[tuple[str, object]]:
    """Ordered new bibliography: ('keep', old_num) or ('add', defect_id)."""
    slots: list[tuple[str, object]] = []
    for old in KEEP:
        slots.append(("keep", old))
        if old in ADDED:
            slots.append(("add", ADDED[old][0]))
    return slots


DEL = "@@DELBRACKET@@"


def remap_brackets(body: str, old_to_new: dict[int, int]) -> tuple[str, int, int]:
    """Renumber every in-text bracket; drop absent elements; mark emptied brackets.

    An emptied bracket becomes a DEL sentinel rather than "" so that tidy_punctuation can
    repair only the text that actually lost a citation, and never touch prose that merely
    happens to look similar.
    """
    deleted = kept = 0

    def repl(m):
        nonlocal deleted, kept
        nums = [int(x) for x in re.findall(r"\d+", m.group(0))]
        new = [old_to_new[n] for n in nums if n in old_to_new]
        if not new:
            deleted += 1
            return DEL
        kept += 1
        return "[" + ", ".join(str(n) for n in sorted(set(new))) + "]"

    return BRACKET.sub(repl, body), kept, deleted


# Connectors that read as dangling once the bracket they introduced is gone.
DANGLING = r"(?:in|into|from|of|with|by|see|cf\.)"


def tidy_punctuation(s: str) -> str:
    """Repair what removing a bracket leaves behind, anchored on the DEL sentinel."""
    # "found, e.g., in [X] and the references therein" -> "... in the references therein"
    s = re.sub(r"\b(in|see)\s*" + DEL + r"\s*and\s+(?=the\s+references\s+therein)",
               r"\1 ", s, flags=re.I)
    # "an algorithm proposed in [X]." -> "an algorithm." -- the participle strands too
    s = re.sub(r"\s*\b(?:proposed|presented|described|developed|reported|introduced"
               r"|studied|discussed|found|given)\s+" + DANGLING + r"\s*" + DEL +
               r"\s*(?=[.,;:])", "", s, flags=re.I)
    # "proposed in [X]." -> "proposed." ; "used in [X]," -> "used,"
    s = re.sub(r"\s*\b" + DANGLING + r"\s*" + DEL + r"\s*(?=[.,;:])", "", s, flags=re.I)
    # "See, e.g., [X] for references on ..." -> "See, e.g., references on ..."
    s = re.sub(r"\s*" + DEL + r"\s+for\s+(?=references\b)", " ", s, flags=re.I)
    # a bracket inside parentheses that emptied them: "(see [X])" -> ""
    s = re.sub(r"\(\s*(?:see\s*)?" + DEL + r"\s*[,;]?\s*\)", "", s, flags=re.I)
    # everything else: drop the sentinel and the space that preceded it
    s = re.sub(r"[ \t]*" + DEL, "", s)
    s = re.sub(r"\s+([.,;:)])", r"\1", s)
    s = re.sub(r"\(\s*[,;]?\s*\)", "", s)
    s = re.sub(r"\[\s*\]", "", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    return s


def reflow(body: str) -> list[str]:
    """Turn PDF line-broken text into paragraph blocks for reportlab."""
    flat = re.sub(r"\s+", " ", body.replace("\n", " ")).strip()
    parts = re.split(r"(?=(?:\d+(?:\.\d+)+\s+[A-Z])|(?:\u2022\s))", flat)
    return [p.strip() for p in parts if p.strip()]


# --------------------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------------------
def register_font() -> tuple[str, str]:
    """A TTF is required: the bibliography carries Latin Extended-A (S-acute, etc.)."""
    for reg, bold, name in [
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "CorpusSans"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "CorpusSans"),
    ]:
        if os.path.exists(reg):
            pdfmetrics.registerFont(TTFont(name, reg))
            if os.path.exists(bold):
                pdfmetrics.registerFont(TTFont(name + "-Bold", bold))
                return name, name + "-Bold"
            return name, name
    raise RuntimeError("no TTF font found; reportlab's built-ins cannot render this text")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_pdf(out_path: str, title: str, front: str, paras: list[str],
               refs: list[str], provenance: str) -> None:
    base, bold = register_font()
    styles = getSampleStyleSheet()
    body_st = ParagraphStyle("body", parent=styles["Normal"], fontName=base,
                             fontSize=9.5, leading=13, alignment=TA_JUSTIFY,
                             spaceAfter=5)
    title_st = ParagraphStyle("title", parent=styles["Title"], fontName=bold,
                              fontSize=15, leading=19, spaceAfter=10)
    head_st = ParagraphStyle("head", parent=styles["Heading1"], fontName=bold,
                             fontSize=12, leading=15, spaceBefore=12, spaceAfter=7)
    note_st = ParagraphStyle("note", parent=body_st, fontSize=8, leading=11,
                             textColor="#555555", spaceAfter=10)
    ref_st = ParagraphStyle("ref", parent=body_st, fontSize=9, leading=12,
                            alignment=0, spaceAfter=4)

    doc = SimpleDocTemplate(out_path, pagesize=LETTER,
                            leftMargin=1.0 * inch, rightMargin=1.0 * inch,
                            topMargin=0.9 * inch, bottomMargin=0.9 * inch,
                            title=title, author="see original")
    flow = [Paragraph(esc(title), title_st), Paragraph(esc(provenance), note_st)]
    for ln in [l for l in front.split("\n") if l.strip()][:8]:
        flow.append(Paragraph(esc(ln.strip()), body_st))
    flow.append(Spacer(1, 8))
    for p in paras:
        flow.append(Paragraph(esc(p), body_st))
    flow.append(Paragraph("References", head_st))
    for i, r in enumerate(refs, 1):
        flow.append(Paragraph(f"[{i}] {esc(r)}", ref_st))
    doc.build(flow)


# --------------------------------------------------------------------------------------
# the two builds
# --------------------------------------------------------------------------------------
def build_spike(out_path: str) -> dict:
    src = os.path.join(ORIGINALS, "2503.02921.pdf")
    pages = extract_pages(src)
    title_words = ["Applications", "of", "Entropy", "in", "Data", "Analysis", "and",
                   "Machine", "Learning:", "A", "Review"]
    front, body_raw, ref_raw = split_front_body_refs(pages)
    refs_all = parse_references(ref_raw, title_words)
    if len(refs_all) < 282:
        raise RuntimeError(f"expected 282 references in the original, parsed {len(refs_all)}")

    body = fix_accents(strip_running_heads(body_raw, title_words))
    words_before = len(body.split())
    brackets_before = len(BRACKET.findall(body))

    # 1. reserve the added entries' marker slots before the general remap deletes them
    slots_hit = []
    for did, slots in ADDED_MARKERS.items():
        for pat, where in slots:
            body, n = re.subn(pat, r"\1@@%sMARKER@@" % did, body, count=1)
            slots_hit.append((did, where, n))
    if any(n != 1 for _, _, n in slots_hit):
        raise RuntimeError(f"marker slots not matched exactly once: {slots_hit}")

    # 2. D14 -- delete the orphan target's single in-text marker
    orphan_hits = len(re.findall(r"\[\s*%d\s*\]" % ORPHAN_OLD, body))
    if orphan_hits != 1:
        raise RuntimeError(f"D14 expects exactly one [{ORPHAN_OLD}] marker, found {orphan_hits}")
    body = re.sub(r"\s*\[\s*%d\s*\]" % ORPHAN_OLD, "", body, count=1)

    # 3. new numbering
    slots = build_slots()
    old_to_new = {old: i + 1 for i, (kind, old) in enumerate(slots) if kind == "keep"}
    added_new = {did: i + 1 for i, (kind, did) in enumerate(slots) if kind == "add"}
    if ORPHAN_OLD in old_to_new:
        pass  # kept: its entry stays, only the marker went

    # 4. remap every remaining bracket
    body, kept_br, del_br = remap_brackets(body, old_to_new)
    for did in ADDED_MARKERS:
        body = body.replace("@@%sMARKER@@" % did, "[%d]" % added_new[did])
    body = tidy_punctuation(body)
    words_after = len(body.split())

    # 5. the bibliography, with the reference-text injections applied
    out_refs, before_after = [], {}
    for kind, key in slots:
        if kind == "add":
            did = key
            text = next(t for k, (d, t) in ADDED.items() if d == did)
            out_refs.append(text)
            before_after[did] = ("(no such entry -- added)", text)
        else:
            text = refs_all[key]
            if key in INJECT:
                did, pat, rep = INJECT[key]
                new_text, n = re.subn(pat, rep, text)
                if n != 1:
                    raise RuntimeError(f"injection {did} on old [{key}] matched {n} times")
                before_after[did] = (text, new_text)
                text = new_text
            elif key == ORPHAN_OLD:
                before_after["D14"] = (text, text)
            out_refs.append(text)

    paras = reflow(body)
    render_pdf(out_path, "Applications of Entropy in Data Analysis and Machine Learning: A Review",
               front, paras, out_refs, PROVENANCE["paper1"])

    return {"refs": out_refs, "old_to_new": old_to_new, "added_new": added_new,
            "before_after": before_after, "body": body,
            "words_before": words_before, "words_after": words_after,
            "brackets_before": brackets_before, "brackets_kept": kept_br,
            "brackets_deleted": del_br, "slots_hit": slots_hit}


def build_control(out_path: str) -> dict:
    src = os.path.join(ORIGINALS, "2410.12660.pdf")
    pages = extract_pages(src)
    title_words = ["Simulation", "of", "Quantum", "Computers:", "Review", "and",
                   "Acceleration", "Opportunities"]
    front, body_raw, ref_raw = split_front_body_refs(pages)
    refs_all = parse_references(ref_raw, title_words)
    body = fix_accents(strip_running_heads(body_raw, title_words))
    words_before = len(body.split())
    brackets_before = len(BRACKET.findall(body))

    old_to_new = {n: n for n in range(1, CONTROL_KEEP_N + 1)}   # straight prefix
    body, kept_br, del_br = remap_brackets(body, old_to_new)
    body = tidy_punctuation(body)
    out_refs = [refs_all[n] for n in range(1, CONTROL_KEEP_N + 1)]

    render_pdf(out_path, "Simulation of Quantum Computers: Review and Acceleration Opportunities",
               front, reflow(body), out_refs, PROVENANCE["control"])
    return {"refs": out_refs, "body": body, "words_before": words_before,
            "words_after": len(body.split()), "brackets_before": brackets_before,
            "brackets_kept": kept_br, "brackets_deleted": del_br}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=HERE, help="where to write paper1.pdf / control.pdf")
    args = ap.parse_args()

    spike_path = os.path.join(args.out, "paper1.pdf")
    control_path = os.path.join(args.out, "control.pdf")
    os.makedirs(args.out, exist_ok=True)

    print("building the spiked paper ...")
    s = build_spike(spike_path)
    print(f"  wrote {spike_path}  ({len(s['refs'])} references)")
    print("building the clean control ...")
    c = build_control(control_path)
    print(f"  wrote {control_path}  ({len(c['refs'])} references)")

    if len(s["refs"]) != 30:
        print(f"FAIL: spiked paper has {len(s['refs'])} references, expected 30")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
