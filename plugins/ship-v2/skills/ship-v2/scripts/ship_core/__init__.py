"""ship-v2's own library (E15 slice 2): the phases `scripts/ship.py` runs.

`references/ship-contract.md` is what each phase reads, writes, prints and stops on. The script validates the input,
finds the build doc by the narrowed hunt, reads it twice (vertical-v2's line rules and its second, CommonMark reading,
byte-for-byte copies held equal by `tests/test_doc_reading.py`; CR-27), records the adapter's hook reading, resolves
each station it visits by allowlist identity and reads its `skill-identity` through the station's own CLI before the
visit (`stations.py`), writes the trace, validates the station's own result, keeps the lap counter, holds the fixes
to the slice's footprint, passes a station's question through, records the owner's waiver or reopening as its event,
and renders the `SHIP:` block. It never judges code, a finding, a fix or a slice (ruling E15-4), never runs a
station's phases, never answers the owner's question, and never runs a git command that changes anything.
"""
