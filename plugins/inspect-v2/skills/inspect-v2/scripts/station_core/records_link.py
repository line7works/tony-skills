"""A front core's use of the records component: the station name, the hook, and the refusal map.

Copied from build-v2's `build_core/records_link.py` with the station name made a parameter (E14
slice 1, brief 3.4): every function that needs the station takes it from the caller, and the test
hook's names derive from it, so the four front cores share one byte-identical file.
`records_client.py` beside this file is build-v2's copy of the recheck pilot's client byte for
byte (see its header); its module constants `STATION` (`recheck-v2`) and `NO_RECORDS_HOOK` are the
pilot's and are never read here.

Only inspect-v2 opens the component (ruling E14-9): it raises each surviving finding as a
`finding_raised` event and appends what the component renders. precon-v2, architect-v2 and
blueprint-v2 never call this module.

The refusal map. A refusal the component RETURNED is definitive: it is persisted and never retried
(pilot contract Appendix B, Revision 7). Each exit code becomes one stop reason tag:

| component                   | tag |
|---|---|
| exit 4 `invalid`            | `records_invalid` |
| exit 5 `ambiguous_identity` | `records_ambiguous` |
| exit 6 `stale_source`       | `records_stale_source` |
| exit 7 `conflict`           | `records_conflict` |

A front core that carries these to its result uses the shared stop tag `records-refused` with the
component's own sentence (station-loop.md section 7); the tags above name the component's exit.
"""
import os
import re

from . import records_client as rcl
from .records_client import ComponentUnavailable, RecordsRefusal  # noqa: F401  (re-exported)

# The one place the mapping lives.
REFUSAL_REASON = {4: "records_invalid", 5: "records_ambiguous", 6: "records_stale_source",
                  7: "records_conflict"}


def prefix_of(station):
    """`PRECON_V2` for `precon-v2`: the prefix of the station's test hooks."""
    return re.sub(r"[^A-Z0-9]", "_", station.upper())


def hook_names(station):
    """(the test flag, the no-records hook) for this station: `<PREFIX>_TEST`, `<PREFIX>_TEST_NO_RECORDS`."""
    prefix = prefix_of(station)
    return prefix + "_TEST", prefix + "_TEST_NO_RECORDS"


def refusal_tag(code):
    """The stop reason tag a component exit code maps to."""
    return REFUSAL_REASON.get(code, "records_failed")


def refusal_sentence(refusal, what):
    """The component's own explanation, wrapped in what this core was doing."""
    return "%s: the records component refused `%s` (exit %s, %s): %s" % (
        what, refusal.command, refusal.exit_code, refusal.error or "-", refusal.sentence())


def hooked_off(station, environ=None):
    """The test hook: behave as if no component were installed anywhere. Gated by <PREFIX>_TEST=1."""
    environ = os.environ if environ is None else environ
    flag, hook = hook_names(station)
    return environ.get(flag) == "1" and environ.get(hook) == "1"


def plugin_root():
    """This core's plugin root from this file: station_core -> scripts -> skills/<core> -> skills -> the plugin."""
    return rcl.station_plugin_root()


def open_client(station, records_root=None, environ=None, python=None):
    """Resolve the component, confirm interface version 2, and return the client.

    Raises `ComponentUnavailable` with the interface's own one-line message when nothing is found
    or the version is not one this station knows.
    """
    if not station:
        raise ValueError("the station name is required")
    environ = os.environ if environ is None else environ
    root = plugin_root()
    if hooked_off(station, environ):
        raise ComponentUnavailable(
            "missing dependency: records component (looked in: %s (%s=1))" % (root, hook_names(station)[1]))
    return rcl.open_client(records_root=records_root, environ=environ, python=python, plugin_root=root)


def actor(station, run_id, harness):
    """`actor` on every event this station writes: the station's own name, the RUN's id, the harness."""
    if not station:
        raise ValueError("the station name is required")
    return {"station": station, "run_id": run_id, "harness": harness}
