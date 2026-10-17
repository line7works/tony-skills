"""sun.py: the file the start hands to the interpreter, started only by `./sun` (RUN-1, A47). See `sun --help`.

It is the head of the tool's first code (SEC-12; A50, A52): the code that runs up to the withheld read and makes
it. It loads the read's own modules and no other module of the tool, makes the read, tells the entry point that
the first code ran, and only then loads the rest of the tool (`sun_core/cli.py` and what it loads). Every line
printed from then on is passed against the read's values, the tool's own failure line among them: where a later
module is missing or broken, or a later part fails, that line is printed and nothing else of the tool's.

Where this file or a module of the read cannot be loaded, or the read itself cannot be made, the entry point has
no word from here and ends with the one fixed exit number, printing nothing (`sun`; `sun_core/exits.py`).
"""
import importlib
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The read's own modules, and through them the rest of the first code: withheld (disproofs, protected, journal,
# locks, rundir, screen, texts, fsio), facts, and the world it reads through. No other module of the tool loads here.
from sun_core import facts as factsmod, texts, withheld, world as worldmod  # noqa: E402

RAN = 3      # the descriptor the entry point reads the first code's word on
OWN_ERR = 5  # the caller's standard error, kept apart by the entry point until the first code has run


def _first_code_ran(world):
    """Tell the entry point that the first code ran, and hand the caller's standard error to the tool's own output and
    to nothing else. The interpreter's own standard error stays where the entry point put it, nowhere: a line the
    interpreter itself writes (an exception's traceback, an "Exception ignored in" line, a warning) is no line of the
    tool's code, would stand outside the withheld read (SEC-12) and could carry an exception's message (SEC-5)."""
    try:
        os.write(RAN, b"r")
        os.close(RAN)
    except OSError:
        pass
    try:
        world.output.err_stream = os.fdopen(OWN_ERR, "w", encoding="utf-8", errors="replace")
    except OSError:
        pass


def start(argv, world, ran=None):
    """The code the entry point runs for every start: the withheld read first, then the rest of the tool. A test's
    driver calls this in its own process with a world of its own (SEC-12's second fixture)."""
    view = withheld.read(world, factsmod.Facts(world.env))
    if ran is not None:
        ran()
    if view.unreadable:
        # a record of the tool's own cannot be read: every start stops here, a summons and a start that is no summons
        # alike, with the one sentence of the owner's ruling A40, passed against what the read gave, and nothing else
        line = view.line(texts.RECORD_UNREADABLE)
        if line and not view.values.holds(line + "\n"):
            world.output.out(line + "\n")
        return _exit("TERMINAL", 10)
    try:
        cli = importlib.import_module("sun_core.cli")
        return cli.main(argv, world=world, view=view)
    except SystemExit:
        raise                   # the interpreter's own way to end, which the tool's code does not raise
    except BaseException:
        # a file of the tool outside the first code is missing or broken, or a later part failed, by any exception, a
        # `BaseException` beyond `Exception` and `KeyboardInterrupt` among them: the tool's own failure line, passed
        # against the read's values, and nothing of the exception (SEC-5)
        line = view.line(texts.FAILURE)
        if line and not view.values.holds(line + "\n"):
            world.output.err(line + "\n")
        return _exit("GENERAL", 1)


def _exit(name, number):
    """An exit number of the tool's own, from `sun_core/exits.py`; the number that file gives it where that file is the
    one that cannot load."""
    try:
        return getattr(importlib.import_module("sun_core.exits"), name)
    except Exception:
        return number


if __name__ == "__main__":
    _world = worldmod.real()
    sys.exit(start(sys.argv[1:], _world, lambda: _first_code_ran(_world)))
