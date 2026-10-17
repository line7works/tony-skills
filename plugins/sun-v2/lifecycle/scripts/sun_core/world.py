"""The seams an invocation acts through (the contract's E16-8 and E16-12; the frame's RUN-1, SEC-2, SEC-3).

One `World` per invocation. The real one reads the session's environment, the real file system and the
real clock. A test stands other things in the same places by building a `World` itself and handing
it to `cli.main(argv, world=...)`; the core loads no code that the environment names.
"""
import datetime
import os
import secrets
import sys

from . import facts as factsmod
from . import fsio

# _CS_DARWIN_USER_TEMP_DIR: the system's own name for an account's temporary folder, the one a terminal window gives a
# shell as its TMPDIR by default (SEC-3's environment row; the owner's ruling A58)
_USER_TEMP_NAME = 65537


class Output(object):
    """Standard output and standard error. `note` tells the world's record that bytes are about to
    leave, so a test can show which reads stood before the first byte."""

    def __init__(self, note=None):
        self.note = note
        self.err_stream = None     # the caller's standard error, kept apart for the tool's own lines (`sun.py`)

    def out(self, text):
        if self.note:
            self.note("output", "stdout", len(text.encode("utf-8")))
        sys.stdout.write(text)
        sys.stdout.flush()

    def err(self, text):
        if self.note:
            self.note("output", "stderr", len(text.encode("utf-8")))
        stream = self.err_stream or sys.stderr
        stream.write(text)
        stream.flush()


def _now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _user_temp():
    """His account's own temporary folder, read from the system and not from the session (SEC-3, A58); None where the
    system gives none."""
    try:
        found = os.confstr(_USER_TEMP_NAME)
    except (ValueError, OSError, TypeError):
        return None
    return found or None


def _new_id(prefix):
    return "%s-%s" % (prefix, secrets.token_hex(8))


class World(object):
    def __init__(self):
        self.env = dict(os.environ)          # the session's environment; never handed to a child whole
        self.fs = fsio.FS()
        self.output = Output()
        self.now = _now                      # the tool's own clock
        self.new_id = _new_id                # ids the tool makes itself
        self.random_hex = secrets.token_hex  # the keying value, a run's fingerprint key
        self.transport = None                # SEC-2: set by `channels` to the real TLS transport when None
        self.cue = None                      # the cue player; None means the real one
        self.rows_root = None                # where the lanes' rows are read from; None means the plugin's
        self.invocation = None               # this invocation's own id, made at its start
        self.system_folders = tuple(factsmod.SYSTEM_FOLDERS)   # the system folders of the search list (SEC-3)
        self.user_temp = _user_temp          # his account's own temporary folder, from the system (SEC-3, A58)
        # the system's start of a process, which the runner alone calls (SEC-3): None is the system's own (`subprocess.Popen`,
        # which the runner imports, so that the first code loads none of it); a test stands its fixture's system here, which
        # gives an answer a real fixture cannot make, no process to be had (A115)
        self.start = None

    def note(self, stage, op, subject, **more):
        """A named boundary that is not a file-system act: a child starting, a request leaving."""
        if self.fs.hook is not None:
            self.fs.hook(stage, op, subject, **more)


def real():
    """The world of a real invocation. Nothing in the session's environment changes which code the
    tool runs: no variable names a file to load, and the tool loads none."""
    world = World()
    world.output = Output(lambda stage, op, size: world.note(stage, op, op, size=size))
    return world
