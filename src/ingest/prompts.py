"""P2's extractor prompt, as module constants. Owner: Ritik.

Kept out of extractor.py so that changing the wording is a visible, reviewable diff
rather than a line buried in call plumbing - and so ``PROMPT_VERSION`` can be part of
the cache key. **Bump PROMPT_VERSION whenever you change SYSTEM_PROMPT or the user
template.** Every cached response was produced by a specific wording, so a silent edit
would leave the cache serving answers from a prompt that no longer exists.

No model name appears here. The model and temperature come from ``config.yaml`` through
``src.settings`` - see the ground rule in docs/config_reference.md.
"""

from __future__ import annotations

#: Part of the cache key. Bump on ANY wording change below.
PROMPT_VERSION = "p2-extractor-v1"

SYSTEM_PROMPT = """\
You extract bibliographic fields from a single reference-list entry.

Return ONE JSON object and nothing else. No prose, no explanation, no markdown fences.

The object has exactly these six keys:

  "title"    string or null - the work's title, exactly as printed
  "authors"  array of strings - full names as printed, in printed order; [] if none
  "year"     integer or null - the four-digit publication year
  "doi"      string or null - the DOI as printed
  "arxiv_id" string or null - the arXiv identifier as printed
  "venue"    string or null - journal, conference, or publisher

RULES, in order of importance:

1. NEVER guess, complete or construct an identifier. If no DOI is printed in the entry,
   "doi" is null. If no arXiv id is printed, "arxiv_id" is null. Do not derive a DOI
   from a title, a venue, or your own knowledge of the paper. An invented identifier is
   worse than a missing one, because the pipeline will resolve it and report a false
   match against a real but unrelated record.

2. Copy, do not normalise. Reproduce the title exactly as printed, including its
   capitalisation and punctuation. Collapse runs of whitespace to single spaces and
   nothing else. Do not expand abbreviations, do not fix apparent typos, do not
   translate, do not add or remove subtitles. A line-break hyphen that appears inside a
   word ("attention-based") is part of the printed text - leave it.

3. Both of these forms carry an arXiv id, and both appear in the real corpus:
     "arXiv preprint arXiv:1607.06450"  -> arxiv_id "1607.06450"
     "CoRR, abs/1409.0473"              -> arxiv_id "1409.0473"
   Strip a leading "arXiv:" or "abs/" and keep the bare identifier, version suffix
   included if one is printed ("1607.06450v2").

4. Authors are the people, not the venue. "In Proceedings of NIPS" is a venue, not an
   author. Keep each author as one string in the form printed - do not reorder
   "Surname, F." into "F. Surname" or vice versa. Drop a trailing "et al."; it is not a
   name.

5. The leading marker is not part of any field. "[12]" or "12." at the start of the
   entry is its position in the list, which the caller already knows.

6. If the text is too mangled to read as a reference, return every key as null (and
   "authors" as []). Say nothing about it - the caller detects and records this. Do NOT
   invent plausible values to fill the object.
"""

USER_TEMPLATE = """\
Reference-list entry:

{entry}

Return the JSON object now."""


def build_messages(entry: str) -> list[dict[str, str]]:
    """The exact message list sent for one entry. Pure - no config, no client."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(entry=entry)},
    ]
