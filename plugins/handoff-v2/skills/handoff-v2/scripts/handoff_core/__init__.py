"""handoff-v2's own library (E15 slice 1, hand-back 2): the phases `scripts/handoff.py` runs.

`references/handoff-contract.md` is what each phase reads, writes, prints and stops on. The script validates the
input, finds the build doc, reads it by vertical-v2's line rules (`fences.py`, a byte-for-byte copy held equal by
`tests/test_line_rules.py`) and then by its second, CommonMark reading (`two_readings.py` over byte-for-byte copies
of vertical-v2's `commonmark.py`, `readings.py`, `spec.py` and `notes.py` and its vendored reader, held equal by
`tests/test_two_readings.py`; the E15 lane contract A25), reads the cards and the open set from the records component and the branch and the
tree from git, assembles the record's own questions, holds the executor's recorded answers to the record, resolves
the next move from the record, renders and parses the forms, and makes the sanctioned writes. It never judges a
slice, a finding or the wisdom of a next move (ruling E15-4), never invokes a station and writes no trace (CR-16).
"""
