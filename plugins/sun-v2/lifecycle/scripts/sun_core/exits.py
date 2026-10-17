"""The exit codes of every sun-v2 command, in one table (the A7a helper interface; the contract's E16-15).

    0   success: the command did what it was asked and the run has more to do (a preview awaiting
        his go; a validator that found nothing)
    1   anything else: a defect of the script
    2   usage: a missing or malformed argument, a file that is not there or is not JSON
    3   the start could not run the tool's own first code (the frame's RUN-1 and SEC-12; the owner's
        ruling A50): nothing was printed on either output stream. Its one place is the entry point
        `sun` (its line `FAILED_START=`), which ends with it where the interpreter could not run
        `sun.py` and the modules of the withheld read, this file among the things that may be
        missing; no name here holds it and no path of the tool's own code ends with it. He runs the
        start line by hand to see why.
    4   validation: a supplied file, a row or a manifest failed its schema or its build; nothing of
        it is written
    10  the invocation reached an ending the frame names: `refused`, `waiting`, `stopped`,
        `complete`, `ended with exceptions` or `closed`
"""

SUCCESS = 0
GENERAL = 1
USAGE = 2
VALIDATION = 4
TERMINAL = 10

ALL = (SUCCESS, GENERAL, USAGE, VALIDATION, TERMINAL)      # the start's fixed number is the entry point's (above)
