# Answer key (E7)

One JSON file per lane, one entry per case, plus a final `_coverage` element. Written from
each lane's `CASES.md` and the pilot contract by agents that never opened a generator, the
shared library, or a built fixture. The key never enters a verifier's evidence at E10; the
checks runner and the E10 harness read it, nothing else does.

Entry shape and match forms: lane contract section 5.9. Field names inside `expected` come
from `result.schema.json`. `records_after`, `must_not`, `rationale`, and `open` are free-form
(ruling E7-8 in `../README.md`). `runs_at` is `E10` for every entry whose expected carries a
status, `E9` when the case is adapter-only, and the list `["E7", "E10"]` when the runner
also decides part of the case now (ruling E7-11): identity against a pin, an invalid-input
verdict, a checkpoint verdict.

`coverage.json` and `coverage.md` are written by `checks/run-checks.py` step 5 from every
`_coverage` element: requirement id to case ids, check code to case ids, plus the uncovered
lists. R22 (D1) points at E9; R27 (T1) is served by `trigger-set/requests.json`, not by a
fixture case (ruling E7-9).

Review record: Astra (GPT-6, max, fresh, `codex exec`, read-only) checks every entry against
the built fixtures and its own derivation from the contract, four lane groups in parallel; the
verdicts are copied into the Clerk packet under `astra-outputs/e7/` and summarized in
`../README.md` under "Build record".
