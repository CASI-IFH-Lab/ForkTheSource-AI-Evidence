"""The seven-stage pipeline.

    PDF
     |
     1. intake           plain code   pull text out of the PDF, find the bibliography
     2. extractor        model        turn each raw reference string into JSON fields
     3. resolver         plain code   look each reference up in public catalogues
     4. judge            model        does the paper's citation match what we found?
     5. repro_extractor  model        pull the paper's reproducibility claims out
     6. repro_judge      model        are those claims actually backed by evidence?
     7. critic           model        review the write-up before a human sees it
     |
    Table of results

Every stage module in this package exposes the same entry point:

    run(payload, config) -> result

so the app can walk STAGES in order without special-casing anything. Only stage 1
is implemented in M0; the rest raise NotImplementedError and say which milestone
they land in.
"""

STAGES: tuple[str, ...] = (
    "intake",
    "extractor",
    "resolver",
    "judge",
    "repro_extractor",
    "repro_judge",
    "critic",
)
