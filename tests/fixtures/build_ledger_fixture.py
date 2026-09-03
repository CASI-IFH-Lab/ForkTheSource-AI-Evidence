"""Generates ``tests/fixtures/ledger_fixture.json``.

The fixture is built through the real ``src.contract`` models and the real
``src.priority.compute_priority`` (weights passed explicitly - this
generator never touches ``config.yaml`` or ``src.settings``; see
``src/priority.py``'s docstring for why). Nothing in ``ledger_fixture.json``
is hand-typed: this file is the single source of truth for it. Re-run it to
regenerate the committed fixture; ``tests/test_contract.py`` asserts the
committed file is byte-identical to a fresh run.

Run directly to print status counts, indicator counts, coverage, and the
worklist order:

    python tests/fixtures/build_ledger_fixture.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    # Allow `python tests/fixtures/build_ledger_fixture.py` to find `src`
    # even when the repo root isn't already on sys.path.
    _ROOT = Path(__file__).resolve().parent.parent.parent
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

from src.contract import (
    Claim,
    Indicator,
    Ledger,
    LedgerEntry,
    MatchEvidence,
    Reference,
    ResolvedSource,
    Verdict,
    VerdictStatus,
    save_ledger,
)
from src.priority import compute_priority

FIXTURE_PATH = Path(__file__).resolve().parent / "ledger_fixture.json"

JUDGE_MODEL = "stub-judge-v0"

# Mirrors the `priority.*` block documented in docs/contract.md and the
# schema config.yaml is expected to grow. Passed explicitly to
# compute_priority() below - see src/priority.py's docstring for why this
# generator never reads config.yaml/src.settings.
WEIGHTS = {
    "severity": {
        "conflict": 1.0,
        "needs_check": 0.6,
        "unresolvable": 0.5,
        "verified": 0.0,
    },
    "usage_base": 0.4,
    "usage_step": 0.2,
    "retracted_bonus": 0.3,
    "cap": 1.0,
}

# claim_id, text, page, ref_ids -- each Reference's cited_by_claims below is
# derived from this table (see _cited_by), not hand-typed, so the two can
# never drift apart.
CLAIMS_RAW = [
    (
        "C01",
        "The Transformer architecture relies solely on attention "
        "mechanisms, dispensing with recurrence and convolutions entirely.",
        2,
        ["R01"],
    ),
    (
        "C02",
        "Bidirectional pretraining on masked tokens outperformed prior "
        "left-to-right language model pretraining on downstream tasks.",
        3,
        ["R02"],
    ),
    (
        "C03",
        "Fine-tuning the pretrained encoder added only a lightweight output "
        "layer for each downstream task.",
        4,
        ["R02"],
    ),
    (
        "C04",
        "Residual connections allowed training of substantially deeper "
        "convolutional networks without a degradation in accuracy.",
        5,
        ["R03"],
    ),
    (
        "C05",
        "A multinational registry analysis reported an association between "
        "the treatment and increased in-hospital mortality.",
        6,
        ["R04"],
    ),
    (
        "C06",
        "A lightweight cross-attention module reduced streaming latency "
        "relative to full-attention baselines.",
        7,
        ["R05"],
    ),
    (
        "C07",
        "The same result was reported in the immediately preceding "
        "citation.",
        7,
        ["R06"],
    ),
    (
        "C08",
        "The masked-language-model objective was later adopted by several "
        "follow-up encoder architectures.",
        8,
        ["R08"],
    ),
]

CLAIMS = [
    Claim(claim_id=claim_id, text=text, page=page, ref_ids=ref_ids)
    for claim_id, text, page, ref_ids in CLAIMS_RAW
]


def _cited_by(ref_id: str) -> list[str]:
    return [claim.claim_id for claim in CLAIMS if ref_id in claim.ref_ids]


def _entry(reference: Reference, evidence: MatchEvidence, verdict: Verdict) -> LedgerEntry:
    n_citing = len(reference.cited_by_claims)
    priority = compute_priority(evidence, verdict, n_citing, weights=WEIGHTS)
    return LedgerEntry(reference=reference, evidence=evidence, verdict=verdict, priority=priority)


def _build_entries() -> list[LedgerEntry]:
    entries = []

    # R01 -- verified, clean match via arXiv id, no DOI printed.
    reference = Reference(
        ref_id="R01",
        raw_text='Vaswani, A. et al. "Attention Is All You Need." NeurIPS, 2017.',
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
        year=2017,
        arxiv_id="1706.03762",
        venue="NeurIPS",
        cited_by_claims=_cited_by("R01"),
    )
    resolved = ResolvedSource(
        provider="arxiv",
        title="Attention Is All You Need",
        authors=reference.authors,
        year=2017,
        venue="NeurIPS 2017",
        url="https://arxiv.org/abs/1706.03762",
        raw={"arxiv_id": "1706.03762"},
    )
    evidence = MatchEvidence(
        ref_id="R01",
        resolved=resolved,
        title_similarity=1.0,
        author_overlap=1.0,
        year_delta=0,
        notes=["Matched via arXiv identifier 1706.03762."],
    )
    verdict = Verdict(
        ref_id="R01",
        status=VerdictStatus.VERIFIED,
        confidence=0.98,
        rationale="Reference resolves cleanly to the arXiv record with matching title, authors, and year.",
        judge_model=JUDGE_MODEL,
    )
    entries.append(_entry(reference, evidence, verdict))

    # R02 -- verified, version_mismatch: preprint cited, journal version
    # resolved. Must not be conflict -- this is the #1 false-alarm risk.
    #
    # This is the row D-020 keys on, so preprint-ness is set EXPLICITLY on
    # both sides and exactly one of them is a preprint:
    #   citation side  -> arxiv_id="1810.04805"  (a preprint)
    #   resolved side  -> is_preprint=False      (the NAACL record)
    # "Exactly one side is a preprint" is the whole test. It is NOT a venue
    # comparison: live API responses (D-036) show Crossref preprints have an
    # empty container-title, arXiv is absent from Crossref entirely, and
    # OpenAlex returns source=null for this very NAACL record -- so a venue
    # test would detect nothing here, on the one row it exists for.
    reference = Reference(
        ref_id="R02",
        raw_text='Devlin, J. et al. "BERT: Pre-training of Deep Bidirectional '
        'Transformers for Language Understanding." arXiv:1810.04805, 2018.',
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        year=2018,
        arxiv_id="1810.04805",
        venue="arXiv preprint",
        cited_by_claims=_cited_by("R02"),
    )
    resolved = ResolvedSource(
        provider="acl-anthology",
        title=reference.title,
        authors=reference.authors,
        year=2019,
        doi="10.18653/v1/N19-1423",
        venue="NAACL-HLT 2019",
        # The resolved record is the published version, and the provider
        # SAYS SO -- False here means "the provider says not a preprint",
        # not "we did not check". D-036.
        is_preprint=False,
        url="https://aclanthology.org/N19-1423/",
        raw={"anthology_id": "N19-1423"},
    )
    evidence = MatchEvidence(
        ref_id="R02",
        resolved=resolved,
        title_similarity=1.0,
        author_overlap=1.0,
        year_delta=1,
        indicators=[Indicator.VERSION_MISMATCH],
        notes=[
            "Citation points at the arXiv preprint; the resolver returned "
            "the peer-reviewed NAACL 2019 version of the same work."
        ],
    )
    verdict = Verdict(
        ref_id="R02",
        status=VerdictStatus.VERIFIED,
        confidence=0.9,
        rationale=(
            "Same paper at a different publication stage: title and author "
            "identity are exact and the published version supersedes the "
            "preprint."
        ),
        checks=["Confirm the preprint and published version share the same author list and abstract."],
        judge_model=JUDGE_MODEL,
    )
    entries.append(_entry(reference, evidence, verdict))

    # R03 -- conflict, doi_mismatch: real title/authors, a DOI belonging to a
    # different record. Modelled the way docs/defect_catalog.md S1 describes
    # the swapped-DOI defect: the resolver matches on title/author and finds
    # the RIGHT paper, and the printed DOI is then compared against that
    # record's DOI and disagrees -> doi_match=False. Deliberately not
    # doi_match=True with a low title similarity: the catalog calls
    # `conflict` reached via title mismatch "right answer, wrong reason",
    # and doi_match=True beside a doi_mismatch indicator contradicts itself.
    # False here also means "the DOIs disagree", which the tri-state keeps
    # distinct from None = "no DOI to compare".
    reference = Reference(
        ref_id="R03",
        raw_text='He, K. et al. "Deep Residual Learning for Image Recognition." '
        "CVPR, 2016. doi:10.1109/CVPR.2016.90",
        title="Deep Residual Learning for Image Recognition",
        authors=["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
        year=2016,
        doi="10.1109/CVPR.2016.90",
        arxiv_id="1512.03385",
        venue="CVPR",
        cited_by_claims=_cited_by("R03"),
    )
    resolved = ResolvedSource(
        provider="crossref",
        title="Deep Residual Learning for Image Recognition",
        authors=reference.authors,
        year=2016,
        doi="10.1109/CVPR.2016.90",
        venue="CVPR 2016",
        url="https://doi.org/10.1109/cvpr.2016.90",
        raw={"note": "record matched on title/author, not on the printed DOI"},
    )
    evidence = MatchEvidence(
        ref_id="R03",
        resolved=resolved,
        title_similarity=1.0,
        author_overlap=1.0,
        year_delta=0,
        doi_match=False,
        indicators=[Indicator.DOI_MISMATCH],
        notes=[
            "Title, authors and year identify this work unambiguously, but "
            "the printed DOI is not the DOI of that work."
        ],
    )
    verdict = Verdict(
        ref_id="R03",
        status=VerdictStatus.CONFLICT,
        confidence=0.85,
        rationale=(
            "The work itself is identified confidently by title and "
            "authors, but the printed DOI belongs to a different record, so "
            "the two identifiers in this citation disagree."
        ),
        checks=[
            "Verify the DOI against the publisher's page for the cited title.",
            "Check whether the printed DOI was mistyped or copied from an adjacent reference.",
        ],
        judge_model=JUDGE_MODEL,
    )
    entries.append(_entry(reference, evidence, verdict))

    # R04 -- conflict, retracted: resolves correctly but the publisher
    # record carries a retraction notice (a real, documented retraction).
    reference = Reference(
        ref_id="R04",
        raw_text=(
            'Mehra, M.R. et al. "Hydroxychloroquine or chloroquine with or '
            'without a macrolide for treatment of COVID-19: a multinational '
            'registry analysis." The Lancet, 2020.'
        ),
        title=(
            "Hydroxychloroquine or chloroquine with or without a macrolide "
            "for treatment of COVID-19: a multinational registry analysis"
        ),
        authors=["Mandeep R. Mehra", "Sapan S. Desai", "Frank Ruschitzka", "Amit N. Patel"],
        year=2020,
        doi="10.1016/S0140-6736(20)31180-6",
        venue="The Lancet",
        cited_by_claims=_cited_by("R04"),
    )
    resolved = ResolvedSource(
        provider="crossref",
        title=reference.title,
        authors=reference.authors,
        year=2020,
        doi="10.1016/S0140-6736(20)31180-6",
        venue="The Lancet",
        is_retracted=True,
        url="https://doi.org/10.1016/s0140-6736(20)31180-6",
        raw={"retraction_notice": True},
    )
    evidence = MatchEvidence(
        ref_id="R04",
        resolved=resolved,
        title_similarity=1.0,
        author_overlap=1.0,
        year_delta=0,
        doi_match=True,
        indicators=[Indicator.RETRACTED],
        notes=["The publisher record for this DOI carries a retraction notice."],
    )
    verdict = Verdict(
        ref_id="R04",
        status=VerdictStatus.CONFLICT,
        confidence=0.95,
        rationale=(
            "The reference resolves correctly, but the publisher record "
            "shows the article was retracted, so claims drawn from it "
            "should not be relied upon as cited."
        ),
        checks=["Confirm whether the citing text depends on findings specific to the retracted analysis."],
        judge_model=JUDGE_MODEL,
    )
    entries.append(_entry(reference, evidence, verdict))

    # R05 -- unresolvable, no indicator: a plausible entry with no matching
    # record in any configured resolver.
    reference = Reference(
        ref_id="R05",
        raw_text='Okoye, T. and Lindqvist, S. "A Lightweight Cross-Attention '
        'Module for Streaming ASR." Workshop on Efficient NLP, 2021.',
        title="A Lightweight Cross-Attention Module for Streaming ASR",
        authors=["T. Okoye", "S. Lindqvist"],
        year=2021,
        venue="Workshop on Efficient NLP",
        cited_by_claims=_cited_by("R05"),
    )
    evidence = MatchEvidence(
        ref_id="R05",
        resolved=None,
        notes=["No matching record was found in any configured resolver."],
    )
    verdict = Verdict(
        ref_id="R05",
        status=VerdictStatus.UNRESOLVABLE,
        confidence=0.4,
        rationale="No resolver returned a matching record for this citation; it may be from an unindexed venue.",
        checks=["Search additional indexes not covered by the automated resolvers."],
        judge_model=JUDGE_MODEL,
    )
    entries.append(_entry(reference, evidence, verdict))

    # R06 -- unresolvable, malformed: an unparseable "ibid." entry, raw_text
    # preserved.
    reference = Reference(
        ref_id="R06",
        raw_text="Ibid., p. 42.",
        cited_by_claims=_cited_by("R06"),
    )
    evidence = MatchEvidence(
        ref_id="R06",
        resolved=None,
        indicators=[Indicator.MALFORMED],
        notes=["Citation text could not be parsed into a structured reference."],
    )
    verdict = Verdict(
        ref_id="R06",
        status=VerdictStatus.UNRESOLVABLE,
        confidence=0.3,
        rationale=(
            "The citation text is a back-reference notation rather than a "
            "standalone bibliographic entry and cannot be resolved on its "
            "own."
        ),
        checks=["Trace the preceding full citation this entry refers back to."],
        judge_model=JUDGE_MODEL,
    )
    entries.append(_entry(reference, evidence, verdict))

    # R07 -- verified, orphan: resolves perfectly but is not cited by any
    # claim. verified rather than needs_check per D-017: `orphan` is derived
    # from the claim map, not from resolution, so it says how the
    # bibliography is used, not whether the cited work exists. An uncited
    # reference that resolves cleanly IS verified.
    reference = Reference(
        ref_id="R07",
        raw_text='Goodfellow, I. et al. "Generative Adversarial Networks." NeurIPS, 2014.',
        title="Generative Adversarial Networks",
        authors=["Ian J. Goodfellow", "Jean Pouget-Abadie", "Mehdi Mirza", "Bing Xu"],
        year=2014,
        arxiv_id="1406.2661",
        venue="NeurIPS",
        cited_by_claims=_cited_by("R07"),
    )
    resolved = ResolvedSource(
        provider="arxiv",
        title=reference.title,
        authors=reference.authors,
        year=2014,
        venue="NeurIPS 2014",
        url="https://arxiv.org/abs/1406.2661",
        raw={"arxiv_id": "1406.2661"},
    )
    evidence = MatchEvidence(
        ref_id="R07",
        resolved=resolved,
        title_similarity=1.0,
        author_overlap=1.0,
        year_delta=0,
        indicators=[Indicator.ORPHAN],
        notes=["Reference resolves cleanly but is not cited by any claim in the document."],
    )
    verdict = Verdict(
        ref_id="R07",
        status=VerdictStatus.VERIFIED,
        confidence=0.9,
        rationale=(
            "The citation is sound - title, authors and year all match the "
            "resolved record. The note is only that no claim in the document "
            "points at it."
        ),
        checks=["Search the document text for an uncaptured citation to this reference."],
        judge_model=JUDGE_MODEL,
    )
    entries.append(_entry(reference, evidence, verdict))

    # R08 -- needs_check, duplicate_entry: same underlying DOI as R02, but a
    # divergent printed venue. needs_check rather than conflict per D-016:
    # divergent metadata means at least one copy is wrong and nothing in the
    # evidence says which, which is exactly what needs_check describes.
    #
    # KNOWN FIXTURE SIMPLIFICATION: D-016 puts `duplicate_entry` on BOTH rows
    # of a duplicate pair, sharing one defect_id. Here only R08 carries it,
    # because R02 is the version-pair example and giving it a second
    # indicator would blur the one row that exists to prove
    # version_mismatch never means conflict. A fixture that did both
    # properly would need a ninth entry - D-023's "split the injection"
    # rule. Roy's labels, not this fixture, are what R2 scores.
    reference = Reference(
        ref_id="R08",
        raw_text='Devlin, J. et al. "BERT: Pre-training of Deep Bidirectional '
        'Transformers for Language Understanding." EMNLP, 2019. '
        "doi:10.18653/V1/N19-1423",
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        year=2019,
        doi="10.18653/V1/N19-1423",
        venue="EMNLP",
        cited_by_claims=_cited_by("R08"),
    )
    resolved = ResolvedSource(
        provider="acl-anthology",
        title=reference.title,
        authors=reference.authors,
        year=2019,
        doi="10.18653/V1/N19-1423",
        venue="NAACL-HLT 2019",
        url="https://aclanthology.org/N19-1423/",
        raw={"anthology_id": "N19-1423"},
    )
    evidence = MatchEvidence(
        ref_id="R08",
        resolved=resolved,
        title_similarity=1.0,
        author_overlap=1.0,
        year_delta=0,
        doi_match=True,
        indicators=[Indicator.DUPLICATE_ENTRY],
        notes=[
            "This DOI already appears against a separate reference-list "
            "entry (R02) with different printed venue metadata."
        ],
    )
    verdict = Verdict(
        ref_id="R08",
        status=VerdictStatus.NEEDS_CHECK,
        confidence=0.8,
        rationale=(
            "Two reference-list entries resolve to the same DOI with "
            "inconsistent printed venue metadata. At least one of the two "
            "is wrong and the evidence does not say which, so a human "
            "should decide."
        ),
        checks=["Determine whether this is a duplicate reference-list entry or two distinct citations wrongly sharing a DOI."],
        judge_model=JUDGE_MODEL,
    )
    entries.append(_entry(reference, evidence, verdict))

    return entries


def build_ledger() -> Ledger:
    return Ledger(
        document_name="fixture-paper.pdf",
        claims=CLAIMS,
        entries=_build_entries(),
    )


def main() -> None:
    ledger = build_ledger()
    save_ledger(ledger, FIXTURE_PATH)

    print("status counts:", ledger.summary_counts())
    print("indicator counts:", ledger.indicator_counts())
    print("coverage:", ledger.evidence_coverage())
    print("worklist:", [entry.reference.ref_id for entry in ledger.worklist()])


if __name__ == "__main__":
    main()
