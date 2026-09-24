"""This station's use of the records component: the station name, the hook, and the refusal map.

`records_client.py` beside this file is the pilot's file byte for byte (see its header). Two
module constants in that copy are the PILOT's and are never read here: `STATION`
(`recheck-v2`) and `NO_RECORDS_HOOK` (`RECHECK_TEST_NO_RECORDS`). This module holds build-v2's
own, so the copy can stay byte-identical and the events this station writes still carry its own
name.

What the build core asks the component for (the records assessment for build, lane contract
section 9: question 2 yes, so the read commands and the card event only):

    import-legacy [--dry-run]   CR-1: level the log with the document before its records are read
    state                       the slice's open set and its cards
    verify                      the head, to pin it and to expect it on an append
    events --kind card_set      what this run already appended, on a settle
    identity                    the six-field source identity the card event carries
    append                      the ONE card event a run makes

Build raises nothing and clears nothing, so no `disposition`, `waived`, `reopened`,
`finding_raised` or `defect_raised` event is ever built here.

The refusal map. A refusal the component RETURNED is definitive: it is persisted and never
retried (pilot contract Appendix B, Revision 7). Each exit code becomes one of this core's own
terminal statuses:

| component                   | build-v2 status | why |
|---|---|---|
| exit 4 `invalid`            | `stopped`       | the event this core built was refused; nothing landed |
| exit 5 `ambiguous_identity` | `stopped`       | a record the importer cannot place; the user decides |
| exit 6 `stale_source`       | `stopped`       | the workspace moved under the run |
| exit 7 `conflict`           | `stopped`       | a moved head or a live lock; never retried, never merged |

Every one is a STOP in this core's vocabulary: the tool could not proceed. A failing check is
not one of these — that is a named completion (lane contract amendment A3 item 1).
"""
import os

from . import records_client as rcl
from .records_client import ComponentUnavailable, RecordsRefusal  # noqa: F401  (re-exported)

STATION = "build-v2"                       # actor.station on every event this station writes
NO_RECORDS_HOOK = "BUILD_TEST_NO_RECORDS"  # gated by BUILD_TEST=1
TEST_FLAG = "BUILD_TEST"

# The one place the mapping lives.
REFUSAL_REASON = {4: "records_invalid", 5: "records_ambiguous", 6: "records_stale_source",
                  7: "records_conflict"}


def refusal_tag(code):
    """The stop reason tag a component exit code maps to."""
    return REFUSAL_REASON.get(code, "records_failed")


def refusal_sentence(refusal, what):
    """The component's own explanation, wrapped in what this core was doing."""
    return "%s: the records component refused `%s` (exit %s, %s): %s" % (
        what, refusal.command, refusal.exit_code, refusal.error or "-", refusal.sentence())


def hooked_off(environ=None):
    """The test hook: behave as if no component were installed anywhere. Gated by BUILD_TEST=1."""
    environ = os.environ if environ is None else environ
    return environ.get(TEST_FLAG) == "1" and environ.get(NO_RECORDS_HOOK) == "1"


def plugin_root():
    """`plugins/build-v2` from this file: build_core -> scripts -> skills/build-v2 -> skills -> the plugin."""
    return rcl.station_plugin_root()


def open_client(records_root=None, environ=None, python=None):
    """Resolve the component, confirm interface version 2, and return the client.

    Raises `ComponentUnavailable` with the interface's own one-line message when nothing is
    found or the version is not one this station knows.
    """
    environ = os.environ if environ is None else environ
    station = plugin_root()
    if hooked_off(environ):
        raise ComponentUnavailable(
            "missing dependency: records component (looked in: %s (%s=1))" % (station, NO_RECORDS_HOOK))
    return rcl.open_client(records_root=records_root, environ=environ, python=python,
                           plugin_root=station)


def actor(run_id, harness):
    """`actor` on every event this station writes.

    `run_id` is the RUN's id, unique per run, which is what `actor.run_id` means everywhere else
    in the loop: the pilot renders and reconciles a run's events by it, and the other stations
    read it the same way. The brief's line "record the answer's session_id as actor.run_id" was
    withdrawn by the control room in the lane's first check round. The executor's session is not
    lost: it is in the result (`answer.session_id`), in the receipt's append block, and in the
    checkpoint's stored answer.
    """
    return {"station": STATION, "run_id": run_id, "harness": harness}


def card_event(document, slice_name, before, after, run_id, harness, at, identity):
    """The ONE event kind this station writes: the card move it made."""
    return {"v": 1, "at": at, "ledger_doc": document,
            "actor": actor(run_id, harness),
            "origin": {"kind": "native"},
            "source": {"known": True, "identity": dict(identity)},
            "kind": "card_set", "slice": slice_name, "before": before, "after": after}
