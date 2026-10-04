"""handoff-v2's own library (E15 slice 1, hand-back 2): the phases `scripts/handoff.py` runs.

`references/handoff-contract.md` is what each phase reads, writes, prints and stops on. The script validates the
input, finds the build doc, reads it by vertical-v2's line rules (`fences.py`, a byte-for-byte copy held equal by
`tests/test_line_rules.py`), reads the cards and the open set from the records component and the branch and the
tree from git, assembles the record's own questions, holds the executor's recorded answers to the record, resolves
the next move from the record, renders and parses the forms, and makes the sanctioned writes. It never judges a
slice, a finding or the wisdom of a next move (ruling E15-4), never invokes a station and writes no trace (CR-16).
"""
