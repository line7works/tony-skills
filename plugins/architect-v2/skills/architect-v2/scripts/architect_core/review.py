"""The blind review (brief 3.7): the readers requests and the saved takes.

`requests(...)` builds one readers request per named reviewer through the shared
`station_core/readers_request.build`: the scope doc the single document, the fixed instruction
verbatim (`MANDATE`), `profile: starved`, `authorized` decided there from the input's
`owner_word` alone. The script builds and records; the executor summons `/readers`.

`take_name(...)` is the verbatim save's file name: `<YYYY-MM-DD>-architect-review-<slug>-<lane>.md`
under the repository's `docs/reviews/`, or `<slug>-review-<YYYY-MM-DD>-<lane>.md` under the
staging home's `architect-reviews/`, `-2`, `-3` appended on a same-day repeat, never overwriting.

`readers_roster(plugin_root)` finds readers' roster the way the records component is found:
route 3a (`<plugin_root>/../readers`), then route 3b (`<plugin_root>/../../readers/<version>`,
the highest dotted version whose manifest names `readers` and that version). `sibling.py` resolves
v2 siblings only, and readers is not one, so this is architect-v2's own lookup of the same shape.
"""
import json
import os

from station_core import readers_request

MANDATE = ("You are the architect. Read the attached precon scope doc and return your own full "
           "architecture-and-delivery take for it: the walkthrough target, a v0 drawing (component "
           "list, plain-prose data flow, one simple diagram), the poured-concrete list of one-way "
           "decisions, and the deferred list. You have no other input; do not ask for any.")
PROFILE = "starved"
LANES = {"gpt-astra": "gpt", "gpt-sol": "gpt", "gemini": "gemini", "claude-session": "claude",
         "claude-opus": "claude", "claude-fable": "claude", "claude-opus-cli": "claude"}
ROSTER = os.path.join("skills", "readers", "assets", "roster.json")


class RosterMissing(LookupError):
    pass


def lane_of(row):
    return LANES.get(row, row)


def _manifest_name(folder):
    try:
        with open(os.path.join(folder, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            body = json.load(fh)
        return body.get("name"), body.get("version")
    except (OSError, ValueError, AttributeError):
        return None, None


def _version_key(text):
    parts = text.split(".")
    if not all(p.isdigit() and (p == "0" or not p.startswith("0")) for p in parts):
        return None
    return tuple(int(p) for p in parts)


def readers_roster(plugin_root):
    looked = []
    beside = os.path.normpath(os.path.join(plugin_root, os.pardir, "readers"))
    looked.append(beside)
    if _manifest_name(beside)[0] == "readers" and os.path.isfile(os.path.join(beside, ROSTER)):
        return os.path.join(beside, ROSTER)
    base = os.path.normpath(os.path.join(plugin_root, os.pardir, os.pardir, "readers"))
    looked.append(base)
    accepted = []
    if os.path.isdir(base):
        for entry in sorted(os.listdir(base)):
            folder = os.path.join(base, entry)
            name, version = _manifest_name(folder)
            if name == "readers" and version == entry and _version_key(entry) and \
                    os.path.isfile(os.path.join(folder, ROSTER)):
                accepted.append((_version_key(entry), folder))
    if accepted:
        return os.path.join(max(accepted)[1], ROSTER)
    raise RosterMissing("readers' roster was not found (looked in: %s); pass --roster FILE" % ", ".join(looked))


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
