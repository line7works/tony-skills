"""blueprint-v2's own library (lane L of E14 slice 2; not a shared file).

`scripts/blueprint.py` hands the four lane phases and the one own command to `phases.py`; the
rest is what those phases read and render:

    checks.py     record-answer's own content checks, and the view the shared refusals read
    buildoc.py    an existing build doc's structure, its protected lines, and the extension
    harvest.py    what `harvest` reads: the selections, the ledger, the architecture doc's lines
    readback.py   the BLUEPRINT: block, rendered from the result
    phases.py     harvest, record-answer, write, report, choose, and the terminal result

`references/blueprint-v2-contract.md` is the contract of every one of them. Nothing here opens the
records component, reads a v1 station's files, calls a model or touches the network.
"""
