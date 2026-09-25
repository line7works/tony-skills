"""Constants and small helpers of architect-v2's library."""
import datetime
import os
import re

STATION = "architect-v2"
PREFIX = "ARCHITECT_V2"
D = "\u2014"     # the dash of the v1 forms: carried by the renderers, never typed
M = "·"     # the middle dot of the walkthrough line and the read-back
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
# the URL a publish returns: https, a host of dot-separated labels, an optional port and path, no space
LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
URL = re.compile(r"^https://%s(?:\.%s)*(?::[0-9]{1,5})?(?:/\S*)?\Z" % (LABEL, LABEL))
ALLOWED_TRACES = ("ledger", "repo_path", "question", "assumed")
HEADER_LABELS = ("Scope doc:", "Docless:", "Blind review:", "Artifact:")


def today(environ=None):
    """The run's date: the machine's local calendar date. Under `ARCHITECT_V2_TEST=1` the test
    hook `ARCHITECT_V2_TEST_TODAY` pins it (a date, YYYY-MM-DD); outside a test it is ignored."""
    environ = os.environ if environ is None else environ
    if environ.get(PREFIX + "_TEST") == "1":
        pinned = environ.get(PREFIX + "_TEST_TODAY")
        if pinned and DATE.match(pinned):
            return pinned
    return datetime.date.today().isoformat()


def inside(path, root):
    if not path or not root:
        return False
    real, base = os.path.realpath(path), os.path.realpath(root)
    return real == base or real.startswith(base.rstrip(os.sep) + os.sep)


def display(path, workspace):
    """A path as the doc names it: workspace-relative when inside the workspace, else absolute."""
    if workspace and inside(path, workspace):
        return os.path.relpath(os.path.realpath(path), os.path.realpath(workspace))
    return path


def blank(value):
    return not isinstance(value, str) or not value.strip()


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()
