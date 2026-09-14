"""recheck_core: the library behind the recheck-v2 scripts (E8 lane contract section 6).

Standard library only, Python 3.9; the one declared exception is jsonschema==4.25.1, imported
lazily by `validate` so a missing dependency exits 3 with one line on stderr (see
`validate.require_jsonschema`). Slice 1 ships `canon` and `validate`; slice 2 adds identity,
ledger, inputs, checkpoint, receipt, verifier, result, and brief.
"""

__all__ = ["canon", "validate"]
