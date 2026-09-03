<!--
  ForkTheSource PR template. Matches Section 8 of the Module Implementation Plan.
  Delete the HTML comments as you fill it in. Keep every heading.
  Reviews are budgeted at 15 minutes, so the reviewer's guide at the bottom is not
  optional - it is the thing that makes that budget realistic.
-->

## Module

**ID:** <!-- e.g. B1, P3, A1, R2. One PR, one module. -->
**Merge-queue item(s) closed:** <!-- e.g. #2. Say "and #N" if this PR closes more than one. -->
**Owner:** <!-- your name -->

<!--
  If this PR closes more than one queue item, say so loudly here AND in the title.
  A queue item that is quietly satisfied by someone else's branch gets a redundant PR
  opened against it.
-->

## What this changes

<!-- Two or three sentences. What a teammate needs to know before reading the diff. -->

## Definition of done

<!--
  Copy the DoD for your module from the plan, one checkbox per line, and put the
  evidence next to each box - a command and its output, not "works on my machine".
  An unchecked box is fine if you say why. An unevidenced check is not.
-->

- [ ] <!-- DoD item --> — evidence: <!-- command + result -->
- [ ] <!-- DoD item --> — evidence: <!-- command + result -->

## Project ground rules

Every PR, regardless of module:

- [ ] No model name anywhere in `src/`. `grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/` finds nothing.
- [ ] `./scripts/check_secrets.sh` passes (pytest runs it too).
- [ ] `.env` is untracked and `git status` does not list it.
- [ ] Model names read via `src.settings.model_for(stage)`; temperatures via `src.settings.temperature_for(stage)`.
- [ ] Every model reply validated against a schema; on failure, retry once, then keep `raw_text` and set the `malformed` indicator - never drop an entry.
- [ ] `pytest` passes, and the count went up if this PR adds behaviour.

## How I tested

<!--
  Verbatim commands and verbatim output. Paste the pytest summary line.
  If you drove the app by hand, say which PDF and what you saw on screen.
  "Ran the tests" is not an answer; "29 passed in 0.58s" is.
-->

```
$ pytest
```

## Eval output

<!--
  REQUIRED ONCE R2 EXISTS. R2 is the eval harness; until it is merged, leave this
  section as-is and tick the N/A box. Once R2 lands, every PR that touches a stage
  pastes its eval run here, unedited, including the failures.
-->

- [ ] N/A — R2 (eval harness) is not merged yet.
- [ ] Eval run pasted below.

```
(paste raw eval output here - do not summarize, do not trim the failures)
```

## Statuses and indicators touched

<!--
  Only if this PR touches classification. Delete the section otherwise.
  Statuses:   verified | needs_check | conflict | unresolvable
  Indicators: retracted | version_mismatch | doi_mismatch | duplicate_entry | orphan | malformed
  Say which ones this PR can now emit, and which it deliberately cannot yet.
-->

## What this unblocks

<!-- Module IDs that become startable when this merges. Tag their owners. -->

## Reviewer's guide

<!--
  The 15-minute budget lives or dies here. Name the two or three files that actually
  need reading and say what to look for in each. List the files that can be skimmed
  (tests, generated fixtures, docs) so the reviewer does not spend the budget on them.
-->

**Read these:**
1. `path/to/file.py` — <!-- what to check -->

**Skim or skip:** <!-- e.g. tests, docs, fixtures -->

## Anything I was unsure about

<!--
  Guesses, assumptions, things you would like a second opinion on. This section
  existing is what stops a wrong assumption becoming a merged convention.
-->
