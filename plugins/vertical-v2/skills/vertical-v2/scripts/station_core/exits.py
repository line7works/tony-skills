"""The exit codes of the front cores' phase drivers, in one table (station-loop.md section 2).

The A7a set the E13 cores use, plus 5 for a recorded answer refused on its content (E14-11):

    0   success; an intermediate phase that has more to do
    1   anything else: a defect of the script, an unreadable run directory
    2   usage: a missing or malformed argument, a file that is not there or not JSON, a phase
        command against the wrong phase, an unknown hunt, a malformed name
    3   missing dependency: jsonschema, or (inspect-v2) the records component missing or at another
        interface version. One line on stderr, nothing on stdout
    4   validation: a supplied file failed its schema; nothing is written
    5   refused: the recorded answer on its content (E14-11), or an input, a path or a run artifact
        a core's own rule refuses (a file outside its home, a run artifact outside the run); nothing
        is written
    10  the run reached a terminal status, a completion or a stop alike
"""

SUCCESS = 0
GENERAL = 1
USAGE = 2
MISSING_DEPENDENCY = 3
VALIDATION = 4
REFUSED = 5
TERMINAL = 10

ALL = (SUCCESS, GENERAL, USAGE, MISSING_DEPENDENCY, VALIDATION, REFUSED, TERMINAL)
