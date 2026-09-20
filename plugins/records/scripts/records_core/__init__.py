"""The library the records CLI imports (records E12 contract section 1, ruling E12-6).

`records_core` is internal. A consumer that imports it instead of calling `scripts/records.py`
is outside the documented interface and unprotected by its version.

Slice 1 holds: `canon` (canonical bytes and the atomic write, a copy of the pilot's),
`identity` (the pilot's six-field identity plus section 8.2's excluded identity), `ids` (finding
identity, section 7), `validate` (schema loading and event validation), `events` (the log's
addresses, the chain walk, the lock, and the optimistic append). `state`, `render`, `legacy` and
`importer` arrive with slice 2.
"""
