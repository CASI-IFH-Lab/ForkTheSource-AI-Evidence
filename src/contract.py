"""Shared data contract for the ForkTheSource AI-Evidence pipeline.

Every lane (intake, resolvers, matching, judge, dashboard) reads and writes
these types, and only these types, when crossing a lane boundary. Anything a
single lane needs internally does not belong here:

- ``ParsedDocument``, and other intake-only intermediate shapes, live in
  ``src/ingest/`` - they never cross a lane boundary, so they are not part
  of the contract.
- Matching thresholds (title-similarity cutoffs, year-delta tolerances, and
  the like) are tuning knobs, not types - they live in ``config.yaml``
  under ``resolvers.*`` / ``matching.*``.
- Prompts belong to the lane that owns the model call issuing them; each
  lane keeps its own ``prompts.py``. A prompt string is not a shared type.

A type that only one lane touches is not a contract type, no matter how
convenient it would be to define it here.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTRACT_VERSION = "v0"


class VerdictStatus(str, Enum):
    """The four outcomes a judge can reach for a reference.

    There is deliberately no ``extraction_failed`` status: a reference whose
    extraction failed still keeps its ``raw_text``, gets the ``malformed``
    indicator, and stays in the ledger as ``unresolvable`` (or whatever the
    judge decides) rather than being dropped or special-cased out of the
    status vocabulary.
    """

    VERIFIED = "verified"
    NEEDS_CHECK = "needs_check"
    CONFLICT = "conflict"
    UNRESOLVABLE = "unresolvable"


class Indicator(str, Enum):
    """Orthogonal flags that can co-occur with any status.

    Indicators describe *why* a reference looks the way it does; status
    describes *what to do about it*. They are independent vocabularies -
    see ``docs/contract.md`` for the table of which combinations are
    expected in practice.
    """

    RETRACTED = "retracted"
    VERSION_MISMATCH = "version_mismatch"
    DOI_MISMATCH = "doi_mismatch"
    DUPLICATE_ENTRY = "duplicate_entry"
    ORPHAN = "orphan"
    MALFORMED = "malformed"


STATUSES: tuple[str, ...] = tuple(status.value for status in VerdictStatus)
INDICATORS: tuple[str, ...] = tuple(indicator.value for indicator in Indicator)


_DOI_PREFIX_RE = re.compile(
    r"^(?:(?:https?://)?(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE
)
_DOI_TRAILING_RE = re.compile(r"[\s;:,.]+$")


def _normalize_doi(value: str) -> str:
    """Lowercase, strip a doi:/doi.org prefix, and trim trailing junk.

    Never invents a DOI - this only reshapes a value that is already
    present; ``None`` is handled by the caller before this runs.
    """
    value = value.strip()
    value = _DOI_PREFIX_RE.sub("", value)
    value = value.strip().lower()
    value = _DOI_TRAILING_RE.sub("", value)
    return value


class _ContractModel(BaseModel):
    """Shared base: unknown fields are a contract violation, not a typo to
    silently ignore, and enum fields normalize to plain strings so callers
    (and JSON output) don't have to care about the enum type."""

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True,
    )


class Reference(_ContractModel):
    ref_id: str
    raw_text: str = Field(min_length=1)
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    venue: str | None = None
    cited_by_claims: list[str] = Field(default_factory=list)

    @field_validator("doi")
    @classmethod
    def _validate_doi(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_doi(value)


class Claim(_ContractModel):
    claim_id: str
    text: str = Field(min_length=1)
    page: int | None = None
    ref_ids: list[str] = Field(default_factory=list)


class ResolvedSource(_ContractModel):
    """One provider's record for a reference.

    ``is_preprint`` is TRI-STATE, with the same discipline as
    ``MatchEvidence.doi_match`` (D-034):

    ``True``   the provider says this record is a preprint
    ``False``  the provider says it is not
    ``None``   the provider did not say

    ``None`` must NOT be read as ``False``. Reading it that way turns "we
    could not tell" into "definitely a published version", which is exactly
    the assertion D-020's test must not make on missing data.

    Resolvers set it from provider-native signals, never by string-matching
    ``venue`` - live API responses show ``venue`` is unusable for this (see
    D-036).
    """

    provider: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    venue: str | None = None
    is_retracted: bool = False
    is_preprint: bool | None = None
    arxiv_id: str | None = None
    url: str | None = None
    raw: dict

    @field_validator("doi")
    @classmethod
    def _validate_doi(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_doi(value)


class MatchEvidence(_ContractModel):
    ref_id: str
    resolved: ResolvedSource | None = None
    title_similarity: float = Field(default=0.0, ge=0, le=1)
    author_overlap: float = Field(default=0.0, ge=0, le=1)
    year_delta: int | None = Field(default=None, ge=0)
    doi_match: bool | None = None
    indicators: list[Indicator] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("indicators")
    @classmethod
    def _dedupe_indicators(cls, value: list) -> list:
        seen: set = set()
        deduped = []
        for item in value:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped

    @model_validator(mode="after")
    def _require_retracted_indicator(self) -> "MatchEvidence":
        if self.resolved is not None and self.resolved.is_retracted:
            if Indicator.RETRACTED.value not in self.indicators:
                raise ValueError(
                    "resolved.is_retracted is True but the 'retracted' "
                    "indicator is missing"
                )
        return self


class Verdict(_ContractModel):
    ref_id: str
    status: VerdictStatus
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)
    checks: list[str] = Field(default_factory=list, max_length=3)
    judge_model: str


class LedgerEntry(_ContractModel):
    reference: Reference
    evidence: MatchEvidence
    verdict: Verdict
    priority: float = Field(default=0.0, ge=0, le=1)

    @model_validator(mode="after")
    def _require_ref_id_alignment(self) -> "LedgerEntry":
        ids = {self.reference.ref_id, self.evidence.ref_id, self.verdict.ref_id}
        if len(ids) != 1:
            raise ValueError(
                "reference/evidence/verdict ref_id mismatch: "
                f"reference={self.reference.ref_id!r} "
                f"evidence={self.evidence.ref_id!r} "
                f"verdict={self.verdict.ref_id!r}"
            )
        return self


class Ledger(_ContractModel):
    document_name: str
    contract_version: str = CONTRACT_VERSION
    claims: list[Claim] = Field(default_factory=list)
    entries: list[LedgerEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_unique_ref_ids(self) -> "Ledger":
        seen: set[str] = set()
        dupes: set[str] = set()
        for entry in self.entries:
            ref_id = entry.reference.ref_id
            if ref_id in seen:
                dupes.add(ref_id)
            seen.add(ref_id)
        if dupes:
            raise ValueError(f"duplicate ref_id(s) across ledger entries: {sorted(dupes)}")
        return self

    def summary_counts(self) -> dict[str, int]:
        """Entry count per status; all four statuses present, zeros included."""
        counts = {status: 0 for status in STATUSES}
        for entry in self.entries:
            counts[entry.verdict.status] += 1
        return counts

    def indicator_counts(self) -> dict[str, int]:
        """Occurrence count per indicator; all six present, zeros included."""
        counts = {indicator: 0 for indicator in INDICATORS}
        for entry in self.entries:
            for indicator in entry.evidence.indicators:
                counts[indicator] += 1
        return counts

    def evidence_coverage(self) -> float:
        """Share of entries with a resolved source, rounded to 4dp."""
        if not self.entries:
            return 0.0
        resolved_count = sum(1 for entry in self.entries if entry.evidence.resolved is not None)
        return round(resolved_count / len(self.entries), 4)

    def counts_are_consistent(self) -> bool:
        return sum(self.summary_counts().values()) == len(self.entries)

    def assert_consistent(self) -> None:
        if not self.counts_are_consistent():
            raise ValueError("status counts do not sum to len(entries)")

    def worklist(self, limit: int | None = None) -> list[LedgerEntry]:
        """Entries sorted by (-priority, ref_id).

        The ref_id tie-break is required so identical input always produces
        identical order, regardless of dict/list iteration happenstance.
        """
        ordered = sorted(self.entries, key=lambda entry: (-entry.priority, entry.reference.ref_id))
        return ordered[:limit] if limit is not None else ordered


def load_ledger(path: str | Path) -> Ledger:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Ledger.model_validate(data)


def save_ledger(ledger: Ledger, path: str | Path) -> Path:
    ledger.assert_consistent()
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = ledger.model_dump(mode="json")
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    out_path.write_text(text, encoding="utf-8")
    return out_path
