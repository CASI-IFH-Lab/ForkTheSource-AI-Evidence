"""The judge prompt, kept as module constants so it can be attacked and quoted.

Two reasons this is not an f-string buried in ``agent.py``:

- Roy's R3 adversarial suite has to attack the *real* prompt. A prompt that
  only exists inside the function that sends it can only be tested through a
  live gateway call, which makes the refusal suite a network test.
- R4 quotes it in the docs. The honesty boundary is the project's whole
  claim; a reader has to be able to see the exact words we send.

The boundary is stated here AND enforced in code by ``gate.py``. Stating it
twice is deliberate (D-019): a prompt is a request, not a guarantee, and the
gate is the guarantee.
"""

from __future__ import annotations

import json

from src.contract import INDICATORS, STATUSES, MatchEvidence, Reference

PROMPT_VERSION = "a1-v1"

JUDGE_SYSTEM_PROMPT = """\
You classify one bibliographic reference into a PROCESS STATE, using only the \
deterministic match signals you are given. You are part of a reviewer's tool. Your \
reader is a human who will do the actual checking; your job is to tell them where to \
look and why, never to reach a conclusion about a person.

ABSOLUTE LANGUAGE RULE
Never say, imply, or hint that a citation is fake, fabricated, invented, nonexistent, \
fraudulent, plagiarised, sloppy, AI-generated or AI-written. Never score AI authorship. \
Never allege misconduct, dishonesty, or intent of any kind. Never speculate about how a \
reference came to be the way it is. Describe the state of the evidence and name what a \
human should verify. If you are asked to judge authenticity, honesty, or intent, decline \
in the rationale and give the process state and the verification steps instead.

NEVER INVENT AN IDENTIFIER
Do not produce a DOI, arXiv id, URL, page range, volume, or author name that is not \
present in the input. If an identifier is missing, the correct output says it is missing.

GROUND ONLY IN THE SUPPLIED SIGNALS
You get title_similarity, author_overlap, year_delta, doi_match, indicators, notes, and \
the resolved record when one exists. Reason from those and nothing else. You have no \
knowledge of this literature and must not use any. If a signal is absent, say what is \
missing - never what its absence implies. `doi_match: null` means one side had no DOI to \
compare; it does NOT mean the DOIs disagree.

THE FOUR STATUSES, AND NOTHING ELSE
  verified      the resolved record matches the reference as printed; nothing to do
  needs_check   something does not line up, or the evidence is incomplete; a human
                should spend a minute on it
  conflict      the evidence and the reference disagree in a way that matters, or the
                resolved record carries a retraction
  unresolvable  no resolved record, or too little of the reference survived to look
                anything up

RULES THAT OVERRIDE YOUR JUDGEMENT
- `retracted` in indicators -> the status is AT LEAST `conflict`. Never lower.
- Parse noise - `malformed` in indicators, a truncated title, a mangled author list -
  lowers confidence toward `needs_check`. It NEVER escalates toward `conflict`. An
  unreadable reference is not a suspicious one; it is an unreadable one.
- `version_mismatch` alone - a preprint cited where a published version exists, or the
  reverse - is a correct citation with a note. It is not a conflict on its own.
- No resolved record at all -> `unresolvable`, not `conflict`. Absence of a match is
  absence of evidence.

OUTPUT
Reply with a single JSON object and nothing else. No prose before or after, no markdown \
fence, no commentary.

{"status": "<one of: verified | needs_check | conflict | unresolvable>",
 "confidence": <float 0.0-1.0>,
 "rationale": "<one or two neutral sentences naming the signals you used>",
 "checks": ["<1-3 concrete actions>"]}

Each check is one thing a human can finish in under a minute, phrased as an instruction \
with an object: "Open the DOI and compare the printed title to the record title." Not \
"verify the reference", not "investigate further" - those are not checks, they are the \
absence of one. If the status is `verified` and there is genuinely nothing to do, return \
a single check naming the one field a reader would spot-check.\
"""

# Kept next to the prompt so a reader sees the closed vocabulary the prompt
# refers to without opening src/contract.py. Derived, never re-typed - if a
# status or indicator is ever added, this follows automatically.
STATUS_VOCABULARY = STATUSES
INDICATOR_VOCABULARY = INDICATORS


def evidence_payload(ref: Reference, ev: MatchEvidence) -> dict:
    """The exact dict shown to the model, as plain JSON-able types.

    Built by hand rather than ``model_dump()`` so the model never sees a
    field we did not decide to show it - ``ResolvedSource.raw`` in
    particular is a whole provider response, which would bury the six
    signals that actually drive the answer under a page of metadata.
    """
    resolved = ev.resolved
    return {
        "reference_as_printed": {
            "ref_id": ref.ref_id,
            "raw_text": ref.raw_text,
            "title": ref.title,
            "authors": ref.authors,
            "year": ref.year,
            "doi": ref.doi,
            "arxiv_id": ref.arxiv_id,
            "venue": ref.venue,
            "cited_by_claim_count": len(ref.cited_by_claims),
        },
        "resolved_record": None
        if resolved is None
        else {
            "provider": resolved.provider,
            "title": resolved.title,
            "authors": resolved.authors,
            "year": resolved.year,
            "doi": resolved.doi,
            "venue": resolved.venue,
            "is_retracted": resolved.is_retracted,
            "is_preprint": resolved.is_preprint,
            "arxiv_id": resolved.arxiv_id,
            "url": resolved.url,
        },
        "signals": {
            "title_similarity": ev.title_similarity,
            "author_overlap": ev.author_overlap,
            "year_delta": ev.year_delta,
            "doi_match": ev.doi_match,
        },
        "indicators": list(ev.indicators),
        "notes": list(ev.notes),
    }


def build_user_prompt(ref: Reference, ev: MatchEvidence) -> str:
    """The per-reference user turn: the evidence, then the reminder."""
    payload = json.dumps(evidence_payload(ref, ev), indent=2, sort_keys=True)
    return (
        f"Reference {ref.ref_id}. Classify it from the evidence below.\n\n"
        f"{payload}\n\n"
        "Reply with the JSON object only. `year_delta` is an absolute difference in "
        "years, never signed. `doi_match: null` means one side carried no DOI, which "
        "is missing information, not disagreement."
    )
