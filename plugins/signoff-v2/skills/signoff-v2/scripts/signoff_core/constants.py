"""What this station is, and the numbers every response carries.

`records_client.py` is the pilot's file byte for byte (the copy test holds it there), so its
`STATION` constant reads `recheck-v2` and its test hook is named for the pilot. This station's
own name lives here and nothing reads the copy's.
"""

STATION = "signoff-v2"                 # actor.station on every event this station writes
INTERFACE_VERSION = 1                  # this station's CLI interface version, in every response
KNOWN_RECORDS_VERSIONS = (1,)          # records interface versions this station was written against

# A7a (docs/plans/2026-09-13-recheck-v2-e8-core.md section 6), the pilot's set.
EXIT_OK = 0
EXIT_OTHER = 1
EXIT_USAGE = 2
EXIT_MISSING_DEPENDENCY = 3
EXIT_VALIDATION = 4
EXIT_TERMINAL = 10

MISSING_JSONSCHEMA = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"

# The prefix the records component owns and the identity excludes (CR-2, CR-3).
RECORDS_PREFIX = "docs/records/"

# Severity to verdict (v1 signoff, "Severity -> verdict"; unchanged under pick P5).
SEVERITIES = ("BLOCKER", "MAJOR", "MINOR")
VERDICT_SIGNED_OFF = "signed off"
VERDICT_WITH_CONDITIONS = "signed off with conditions"
VERDICT_REJECTED = "rejected"
VERDICTS = (VERDICT_SIGNED_OFF, VERDICT_WITH_CONDITIONS, VERDICT_REJECTED)

EVIDENCE_KINDS = ("executed", "read", "reasoned")

# The build doc's own sections that are the builder's working record, never spec and never
# evidence (v1 signoff Step 2; brief, "Independence", S3-04).
BUILDER_SECTIONS = ("Build assumptions", "Deviations", "Discovered", "Handoffs")
