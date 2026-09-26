"""readers' roster, found one way for every core (slice 3a's design, section 5; ruling E14-3).

    find(plugin_root, argument=None) -> {"root", "route", "roster", "looked"}
    load(plugin_root, argument=None) -> (found, roster)

The roster is `<readers root>/skills/readers/assets/roster.json`; the root is found the way the
records component and a v2 sibling are (`sibling.py`), and a folder counts only when its manifest
names `readers` AND the roster file is there:

    argument   an explicit folder (a test hook): taken only when it is usable; otherwise it is
               named in `looked` with the reason and the routes below are tried
    route 3a   `<plugin_root>/../readers`, the checkout sibling
    route 3b   `<plugin_root>/../../readers/<version>`, the installed shape: the highest dotted
               version whose folder name equals its manifest's `version`, canonical digits only
               (`sibling.version_key`: `01.2` is no version)

Nothing found raises `RosterMissing` (a `LookupError`) naming every place looked, with the reason
each one was passed over. A core keeps its own stop by catching it (inspect-v2 raises its
`ComponentUnavailable`, exit 3). The script reads the roster and never runs readers: the executor
summons it (ruling E14-4).
"""
import json
import os

from .sibling import manifest, version_key

NAME = "readers"
ROSTER = os.path.join("skills", "readers", "assets", "roster.json")


class RosterMissing(LookupError):
    """No usable readers component, or its roster cannot be read; the message names every place looked."""


def _why_not(folder):
    """None when `folder` is a usable readers root, else the reason it is not."""
    body = manifest(folder)
    if body is None:
        return "no plugin.json" if os.path.isdir(folder) else "no such directory"
    if body.get("name") != NAME:
        return "its manifest names %r" % (body.get("name"),)
    if not os.path.isfile(os.path.join(folder, ROSTER)):
        return "no roster"
    return None


def _found(root, route, looked):
    return {"root": root, "route": route, "roster": os.path.join(root, ROSTER), "looked": looked}


def find(plugin_root, argument=None):
    looked = []
    if argument:
        why = _why_not(argument)
        if why is None:
            return _found(argument, "argument", looked + [argument])
        looked.append("%s (%s)" % (argument, why))
    beside = os.path.join(plugin_root, os.pardir, NAME)
    why = _why_not(beside)
    if why is None:
        return _found(beside, "3a", looked + [beside])
    looked.append("%s (%s)" % (beside, why))
    base = os.path.join(plugin_root, os.pardir, os.pardir, NAME)
    if not os.path.isdir(base):
        looked.append("%s (no such directory)" % base)
    else:
        looked.append(base)
        accepted = []
        for entry in sorted(os.listdir(base)):
            folder = os.path.join(base, entry)
            if not os.path.isdir(folder):
                continue
            body = manifest(folder)
            if body is None:
                looked.append("%s (no plugin.json)" % folder)
            elif body.get("name") != NAME:
                looked.append("%s (its manifest names %r)" % (folder, body.get("name")))
            elif body.get("version") != entry:
                looked.append("%s (name differs from version %s)" % (folder, body.get("version")))
            elif version_key(entry) is None:
                looked.append("%s (version not dotted integers)" % folder)
            elif not os.path.isfile(os.path.join(folder, ROSTER)):
                looked.append("%s (no roster)" % folder)
            else:
                accepted.append((version_key(entry), folder))
        if accepted:
            return _found(max(accepted)[1], "3b", looked)
    raise RosterMissing("missing dependency: readers component (looked in: %s)" % ", ".join(looked))


def load(plugin_root, argument=None):
    found = find(plugin_root, argument)
    try:
        with open(found["roster"], encoding="utf-8") as fh:
            roster = json.load(fh)
    except (OSError, ValueError) as exc:
        raise RosterMissing("missing dependency: readers component at %s has no readable roster (%s)"
                            % (found["root"], exc))
    if not isinstance(roster, dict):
        raise RosterMissing("missing dependency: readers component at %s has a roster that is not a JSON object"
                            % found["root"])
    return found, roster
