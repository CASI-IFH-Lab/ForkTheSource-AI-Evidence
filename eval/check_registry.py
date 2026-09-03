"""Probe each corpus reference against OpenAlex and Crossref, to label honestly.

Read-only. Writes a JSON report to eval/outputs/ (gitignored) and prints a table.
This is a labelling aid, not part of the harness: run_eval.py never calls a network.

    python eval/check_registry.py            # both documents
    python eval/check_registry.py control    # one of them
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
import time
import unicodedata
import warnings

warnings.filterwarnings("ignore")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "corpus"))
sys.path.insert(0, os.path.dirname(HERE))          # repo root, for src.settings
import build_corpus as B

from src.settings import thresholds

HDR = {"User-Agent": "ForkTheSource-corpus-labelling/0.1 (ASU AIR Spark Challenge)"}
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s,;)\]}\"<>]+")
ARXIV_RE = re.compile(r"arXiv:(\d{4}\.\d{4,5})", re.I)
DOCS = {"paper1": ["Applications of Entropy"], "control": ["Simulation of Quantum"]}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())


def sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def guess_title(text: str) -> str:
    """Pull a probable title out of a reference string, for a title search."""
    m = re.search(r"\.\s*(?:19|20)\d\d[a-z]?\.\s*(.+)", text)   # ACM: Authors. Year. Title.
    tail = m.group(1) if m else text
    m2 = re.match(r"(.+?)\.\s+(?:In\s|[A-Z][a-z]+\s|https?://|arXiv)", tail)
    cand = (m2.group(1) if m2 else tail).strip()
    if not m:   # Elsevier style: Authors, Title, Venue year.
        parts = [p.strip() for p in re.split(r",\s*", text)]
        cand = max(parts, key=len) if parts else text
    return re.sub(r"\s+", " ", cand)[:220]


def get(url: str, timeout: int = 30):
    try:
        r = requests.get(url, timeout=timeout, headers=HDR)
        return r.status_code, (r.json() if r.status_code == 200 else None)
    except Exception as e:                                    # network is not the point here
        return "ERR", str(e)[:80]


def probe(text: str) -> dict:
    doi_m = DOI_RE.search(text)
    ax_m = ARXIV_RE.search(text)
    # An Elsevier-style entry ends the DOI with a full stop ("doi:10.3390/e10030261.").
    # Left on, every lookup 404s and falls through to a title search, which reads as a
    # corpus problem when it is a probe problem.
    doi = doi_m.group(0).rstrip(".,;:)") if doi_m else None
    out = {"printed_doi": doi,
           "printed_arxiv": ax_m.group(1) if ax_m else None,
           "title_guess": guess_title(text)}
    lookup = out["printed_doi"] or (f"10.48550/arXiv.{out['printed_arxiv']}"
                                    if out["printed_arxiv"] else None)
    if lookup:
        st, j = get(f"https://api.openalex.org/works/https://doi.org/{lookup}")
        out["oa_by_id_status"] = st
        if j:
            out.update(oa_title=j.get("title"), oa_year=j.get("publication_year"),
                       oa_type=j.get("type"), oa_retracted=j.get("is_retracted"),
                       route="doi" if out["printed_doi"] else "arxiv")
            out["title_sim"] = sim(out["title_guess"], j.get("title") or "")
            return out
    # no identifier, or the identifier did not resolve: fall back to title search
    st, j = get("https://api.openalex.org/works?filter=title.search:"
                + requests.utils.quote(out["title_guess"])
                + "&per-page=3&select=doi,title,publication_year,type,is_retracted")
    out["oa_search_status"] = st
    out["oa_count"] = (j or {}).get("meta", {}).get("count") if j else None
    hits = []
    for w in (j or {}).get("results", []):
        hits.append({"doi": w.get("doi"), "title": w.get("title"),
                     "year": w.get("publication_year"), "type": w.get("type"),
                     "sim": sim(out["title_guess"], w.get("title") or "")})
    out["oa_hits"] = hits
    out["title_sim"] = max([h["sim"] for h in hits], default=0.0)
    out["route"] = "title-search"
    time.sleep(2.0)
    st, j = get("https://api.crossref.org/works?query.bibliographic="
                + requests.utils.quote(out["title_guess"]) + "&rows=3&select=DOI,title,issued")
    out["cr_status"] = st
    out["cr_hits"] = [{"doi": it.get("DOI"), "title": (it.get("title") or [""])[0],
                       "sim": sim(out["title_guess"], (it.get("title") or [""])[0])}
                      for it in ((j or {}).get("message", {}).get("items", []))]
    out["cr_best"] = max([h["sim"] for h in out["cr_hits"]], default=0.0)
    return out


def classify(p: dict, th: dict) -> tuple[str, str]:
    strong, weak = th["title_strong"], th["title_weak"]
    if p.get("route") in ("doi", "arxiv") and p.get("oa_by_id_status") == 200:
        if p.get("oa_retracted"):
            return "conflict", "registry record carries a retraction flag"
        if p.get("title_sim", 0) >= strong:
            return "verified", "identifier resolves, title agrees"
        return "AMBIGUOUS", (f"identifier resolves but title_sim={p['title_sim']:.3f} "
                             f"vs title_strong={strong}")
    best = max(p.get("title_sim", 0.0), p.get("cr_best", 0.0))
    if best >= strong:
        return "verified", f"title search resolves, best_sim={best:.3f}"
    if best < weak:
        return "unresolvable", f"no record above title_weak; best_sim={best:.3f}"
    return "AMBIGUOUS", f"best_sim={best:.3f} sits between title_weak and title_strong"


def main() -> int:
    th = thresholds()
    want = sys.argv[1:] or list(DOCS)
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(outdir, exist_ok=True)
    report = {}
    for doc in want:
        _, _, rr = B.split_front_body_refs(
            B.extract_pages(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "corpus", f"{doc}.pdf")))
        refs = B.parse_references(rr, DOCS[doc])
        print("#" * 100)
        print(f"{doc}: probing {len(refs)} references "
              f"(title_strong={th['title_strong']}, title_weak={th['title_weak']})")
        rows = {}
        for n in sorted(refs):
            p = probe(refs[n])
            verdict, why = classify(p, th)
            p["verdict"], p["why"] = verdict, why
            rows[f"R{n:02d}"] = p
            ident = p["printed_doi"] or (("arXiv:" + p["printed_arxiv"])
                                         if p["printed_arxiv"] else "-")
            print(f"  R{n:02d} {verdict:13} sim={p.get('title_sim', 0):.3f} "
                  f"route={p.get('route','-'):12} {ident[:44]}")
            print(f"       {why}")
            time.sleep(1.2)
        report[doc] = rows
    path = os.path.join(outdir, "registry_probe.json")
    json.dump(report, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
