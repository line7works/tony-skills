"""precon-v2's own library (lane P of E14 slice 2): the station's phases over the shared frame.

Not shared with the other front cores. `phases.py` holds the handlers `scripts/precon.py` hands
to `station_core.driver.main`; `scopedoc.py` plans every document write from the harvest and the
recorded answer; `rules.py` holds precon's own refusals of a recorded answer; `exit_test.py`
holds the cold read (the readers requests and the cold-read doc); `run.py` holds the run
directory's files, the phase gate and the result. `references/precon-v2-contract.md` is the
statement of what each does.
"""
