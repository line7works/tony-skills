"""The blind review (brief 3.7): the readers requests and the saved takes.

`requests(...)` builds one readers request per named reviewer through the shared
`station_core/readers_request.build`: the scope doc the single document, the fixed instruction
verbatim (`MANDATE`), `profile: starved`, `authorized` decided there from the input's
`owner_word` alone. The script builds and records; the executor summons `/readers`.

`take_name(...)` is the verbatim save's file name: `<YYYY-MM-DD>-architect-review-<slug>-<lane>.md`
under the repository's `docs/reviews/`, or `<slug>-review-<YYYY-MM-DD>-<lane>.md` under the
staging home's `architect-reviews/`, `-2`, `-3` appended on a same-day repeat, never overwriting.

`readers_roster(plugin_root)` finds readers' roster through the shared resolver
(`station_core/readers_roster.find`, slice 3b R9, A7 section 5): route 3a (`<plugin_root>/../readers`),
then route 3b (`<plugin_root>/../../readers/<version>`, the highest canonical version whose manifest
names `readers` and that version), each taken only when the roster file is there. This core keeps its
own `RosterMissing` and its way on: `request --roster FILE`.
"""
import os

from station_core import readers_request
from station_core import readers_roster as shared_roster

MANDATE = ("You are the architect. Read the attached precon scope doc and return your own full "
           "architecture-and-delivery take for it: the walkthrough target, a v0 drawing (component "
           "list, plain-prose data flow, one simple diagram), the poured-concrete list of one-way "
           "decisions, and the deferred list. You have no other input; do not ask for any.")
PROFILE = "starved"
LANES = {"gpt-astra": "gpt", "gpt-sol": "gpt", "gemini": "gemini", "claude-session": "claude",
         "claude-opus": "claude", "claude-fable": "claude", "claude-opus-cli": "claude"}


class RosterMissing(LookupError):
    """No readers roster beside this core; the message names every place looked and `--roster FILE`."""


def lane_of(row):
    return LANES.get(row, row)


def readers_roster(plugin_root):
    """The roster file's path as the shared resolver found and checked it (never normalized: through a
    symlinked plugin root the lexical path is another place, slice 3b round 2 R4); this core's
    `RosterMissing` otherwise."""
    try:
        return shared_roster.find(plugin_root)["roster"]
    except shared_roster.RosterMissing as exc:
        raise RosterMissing("readers' roster was not found: %s; pass --roster FILE" % exc)


def requests(rows, input_doc, roster, scope_doc, run_id, session_model=None, models=None, taken=()):
    """[(call_id, request)] for the rows named, in order, each call id new to this run."""
    out = []
    used = set(taken)
    review_run = "%s-review" % run_id
    for row in rows:
        call_id = "%s-%s" % (review_run, row)
        n = 1
        while call_id in used:
            n += 1
            call_id = "%s-%s-%d" % (review_run, row, n)
        used.add(call_id)
        req = readers_request.build(row, input_doc, roster, MANDATE, PROFILE, review_run, call_id,
                                    documents=[scope_doc], session_model=session_model,
                                    model=(models or {}).get(row))
        out.append((call_id, req))
    return out


def take_name(home, slug, lane, date, folder):
    if home == "workspace":
        stem = "%s-architect-review-%s-%s" % (date, slug, lane)
    else:
        stem = "%s-review-%s-%s" % (slug, date, lane)
    name = stem + ".md"
    n = 1
    while os.path.lexists(os.path.join(folder, name)):
        n += 1
        name = "%s-%d.md" % (stem, n)
    return name


def take_text(row, model, isolation, sidecar, body):
    return "Reader: %s · model %s · isolation %s · sidecar %s\n\n%s" % (row, model, isolation, sidecar, body)
