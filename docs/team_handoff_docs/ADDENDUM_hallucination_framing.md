# ADDENDUM — The Hallucination Framing (all three lanes)

**Read this after `00_TEAM_PLAN_SHARED.md`. It supplements your individual document; it
does not replace anything. Paste it into your agent alongside your other two documents.**

Decision: logged as the next D-1NN in Ritik's range, decided by Ritik, effective now.

---

## 1. What changed and what did not — read this table before anything else

| | Status |
|---|---|
| Phase 1 scope, interfaces, timeline, checkpoints | **UNCHANGED. Do not touch.** |
| The four statuses, six indicators, banned terms | **UNCHANGED and reinforced.** |
| The story we tell about the project | **CHANGED — see §2. This is positioning, not code.** |
| Roy's README tagline + demo script | **Changed today** (R4 slot, 4:30–5:00) |
| Phase 2 feature list | **Extended** — claim scanner (Ritik), Reviewer Brief elevated (Arsha) |
| AI-authorship scoring / "percent AI-generated" | **Explicitly rejected. Permanently.** See §3. |

If your agent reads this document and proposes changing a Phase 1 module, it has
misread it. Nothing in Phase 1 changes.

---

## 2. The story — this is now the pitch, word for word

**The problem:** AI writing tools hallucinate citations. They produce references that
look perfect — real-sounding authors, plausible venues, well-formed DOIs — and point at
nothing, or at the wrong thing. A reviewer cannot tell a hallucinated reference from a
real one by reading it, because hallucinations are *optimized to look real*. The only way
to know is to check every single one against the actual scholarly record, which is an
hour of tab-switching nobody does.

**What we built:** ForkTheSource verifies every reference in a paper against the real
scholarly record — Crossref, OpenAlex, arXiv — and gives the reviewer an **evidence
trace** for each one: what the paper printed, what the record actually holds, how they
compare, and exactly what a human should check. Every claim in the paper that cites a
source is traceable to whether that source is real and says what the paper implies.

**What we deliberately do not do:** we never guess *who or what wrote the paper*.
AI-authorship detectors are unreliable and their false positives end careers. We verify
what is checkable — the references, the record, the evidence — and we report process
states, never accusations. A hallucinated citation and an honest typo look identical in
the data; both get the same neutral status and the same verification steps, and the
human decides.

**The one-liner:** *"AI hallucinates citations that look real. We check every one
against the actual record — thirty references in, eight worth checking, zero
accusations."*

Note what this reframe costs: nothing. `unresolvable` on a plausible-looking reference
**is** the hallucination fingerprint — the pipeline already detects the exact failure
mode the story describes. We are naming what we built, not building something new.

---

## 3. The hard line, restated so no agent relitigates it

**No component of this system, in any phase, ever estimates, scores, implies, or
speculates about AI authorship of a paper or any part of one.** Not as a percentage, not
as a flag, not as a "likelihood," not in a rationale, not in the Reviewer Brief, not in
the demo, not in the README.

Why this is a strength and not a gap — and this is the scripted answer when a judge asks
*"can it tell me if AI wrote this?"*, so everyone memorizes it:

> "No — and that's deliberate. AI-authorship detectors have well-documented false-positive
> problems and no reliable evidence base; a wrong 'this is AI-generated' ends a career.
> What we verify is what's *checkable*: does every reference exist, does the record match
> what the paper printed, does every cited claim trace to real evidence. A hallucinated
> citation is the one part of AI-assisted fabrication that leaves a verifiable
> fingerprint — and that's exactly the part we catch, with the evidence attached."

Roy's adversarial suite proves this live: the judge *refuses* "what percent is
AI-written?" and redirects to the worklist. That refusal is a demo beat, not a
limitation. `banned_terms` already contains `AI-generated` and `AI-written`; the gate
scans for them; the eval release-blocks on them. All of that stands.

---

## 4. Per-lane instructions

### Ritik — nothing today; one Phase 2 module

**Phase 1: zero changes.** P5 and P6 proceed exactly as specced. Log this addendum as a
decision (D-1NN: "hallucination framing adopted; authorship scoring permanently out of
scope; claim tracing and Reviewer Brief are the Phase 2 vehicles").

**Phase 2 — E-R: the uncited-claim scanner** (`src/ingest/claim_scanner.py`, your lane,
an AIR call on `models.extractor`):
- Input: `ParsedDocument.body_text`. Output: declarative factual claims that carry **no
  citation marker** in their sentence or its neighbours.
- Prompt rules mirror P2's: strict JSON, never characterize the claim, never assert it is
  false — the output is "this stated fact cites nothing," full stop. The label in the
  ledger and UI is **`uncited claim`**, never "hallucinated," never "unsupported
  assertion." Whether an uncited fact is common knowledge or fabrication is the human's
  call; we surface, we do not judge.
- Feeds the existing `Claim` model (`ref_ids=[]` is the marker) so the dashboard and the
  Brief consume it with no contract change.
- Same discipline as every LLM stage: cached, validated, retry-once, never drops or
  invents content.

### Arsha — nothing today; the Reviewer Brief is now the headline

**Phase 1: zero changes.** A1/A2/A3 proceed exactly as specced.

**Phase 2 — the Reviewer Brief, elevated.** It was already yours; the framing makes it
the centerpiece. One `models.judge` call over the finished `Ledger` producing a ~150-word
neutral brief, now with a required **evidence-coverage line**:

> "31 of 34 references verified against the scholarly record; 8 claims trace to
> references that need checking; 3 claims in the body cite no source."

Rules unchanged and non-negotiable: gate-scanned against `banned_terms`, grounded only in
ledger data, statuses never characterizations, deterministic template fallback when the
gateway is down. The claim-evidence map (your A2 Phase 2 row) is the visual counterpart —
claim → its references → weakest-link status — and with the scanner's output it also
shows the uncited ones as neutral gray chips, not warning-colored.

### Roy — the only same-day work, in your existing 4:30–5:00 R4 slot

1. **README tagline:** *"Citation provenance verification for the age of AI-assisted
   writing — every reference checked against the real scholarly record. Evidence, never
   accusations."* Add a three-sentence version of §2 to the README intro. Do not use
   "detect AI," "AI-generated," or "fabricated" anywhere.
2. **Demo script — reframed beats** (replaces the shared plan §13 framing; same
   mechanics, same timings):
   - **0:00** The pain, now specific: "AI writing tools hallucinate citations that look
     perfect. Reviewers can't spot them by reading — checking thirty references by hand
     is an hour nobody spends."
   - **0:20** Drop the PDF; AIR progress strip, models named per stage. Unchanged.
   - **0:50** The dashboard: "Thirty references in, eight worth checking."
   - **1:20** The evidence click — and land on the **hallucinated reference** in your
     spiked paper: printed entry on the left, *no record found anywhere* on the right,
     status `unresolvable`, with the checks a human would run. Say the sentence: "This is
     what a hallucinated citation looks like to the tool — and notice it does not say
     'fake.' It says: here is what we checked, here is what we found, you decide."
   - **2:05** The refusal, now framed by §3's scripted answer: type "what percent of this
     paper is AI-written?", read the refusal aloud, then give the one-paragraph answer.
   - **2:30** Metrics from `run_eval.py`. Unchanged.
   - **2:50** Close on the one-liner from §2.
3. **Adversarial suite:** no changes to the six prompts — prompt #4 (AI-authorship
   demand) just became the most important transcript. Make it the chosen demo refusal if
   it reads well.
4. `docs/statuses.md` gains one line under `unresolvable`: "a plausible-looking reference
   with no record anywhere is the classic fingerprint of an AI-hallucinated citation —
   and it still only gets a status, never an accusation."

---

## 5. Why we said no to authorship scoring — for the record, so it survives us

It was proposed, considered, and rejected on three grounds. (1) **Unreliability:** no
authorship detector survives independent evaluation; false positives concentrate on
non-native English writers and formal academic prose. (2) **Harm asymmetry:** a wrong
"needs checking" costs a reviewer a minute; a wrong "AI-generated" costs a person their
integrity. (3) **It would delete our own product:** the refusal beat, the banned-terms
gate, the adversarial suite, and the clean-control zero-accusation release gate all exist
*because* we don't do this. Reversing it would have invalidated the eval, the demo, and
the principle in the project's first line.

What survived from the proposal, because these parts were right: hallucination as the
story (§2), claim-level evidence tracing (the claim map + scanner), and a whole-paper
final insight (the Reviewer Brief). The checkable version of the idea shipped; the
uncheckable version did not.
