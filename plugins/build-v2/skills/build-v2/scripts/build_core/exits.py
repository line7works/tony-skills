"""The exit codes of this CLI, in one table.

The A7a helper interface as `docs/plans/2026-09-13-recheck-v2-e8-core.md` section 6 defines it,
which the E13 lane contract cites (section 2, item 4) and which the records component's
`references/interface.md` and the recheck pilot both implement:

    0   success; an intermediate phase that has more to do
    2   usage: a missing or malformed argument, a file that is not there, a phase command
        against the wrong phase
    3   missing dependency: `jsonschema` did not import, or the records component is missing or
        speaks an interface version this station was not written against. One line on stderr,
        nothing on stdout
    4   validation: an input, a result or an example failed its schema (the validator scripts,
        and `check-input`)
    10  the run reached a terminal status — a completion or a stop alike. A refused records call
        ends the run here, carrying the component's own sentence
    1   anything else: a defect of this script, a git failure, an unreadable run directory

Lane B's brief restated the set as "(0 ok, 1 usage, 2 invalid input, 3 missing dependency, 4
validation)", which collides with the source it cites, with the records component and with the
pilot. The control room ruled on it while this lane ran (2026-09-22, question 1 of the builder's
report): "the brief was wrong and the source is right", the A7a set above governs, and a refused
records call ends the run in a terminal status, exit 10, carrying the component's own sentence.
Every code this CLI can return is named in this module.
"""

SUCCESS = 0
GENERAL = 1
USAGE = 2
MISSING_DEPENDENCY = 3
VALIDATION = 4
TERMINAL = 10

ALL = (SUCCESS, GENERAL, USAGE, MISSING_DEPENDENCY, VALIDATION, TERMINAL)

MEANING = {
    SUCCESS: "success",
    GENERAL: "anything else (a defect of this script, a git failure, an unreadable run directory)",
    USAGE: "usage (a missing or malformed argument, a file that is not there, the wrong phase)",
    MISSING_DEPENDENCY: "missing dependency (jsonschema, or the records component)",
    VALIDATION: "validation (an input, a result or an example failed its schema)",
    TERMINAL: "the run reached a terminal status (a completion or a stop)",
}
