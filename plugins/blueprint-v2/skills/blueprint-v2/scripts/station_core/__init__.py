"""The shared library of the four front cores (E14 slice 1, the frame).

Identical, file for file, in precon-v2, architect-v2, blueprint-v2 and inspect-v2
(`references/shared-files.txt`; `scripts/tests/test_shared_equal.py`). A library only: no module
here has a `__main__`. Each core's phase driver, `scripts/<station>.py`, calls `driver.main` with
its own station name, its hunt table and the phases its lane has built. The interface a caller
writes against is that driver, the schemas under `references/`, and `references/station-loop.md`.
"""
