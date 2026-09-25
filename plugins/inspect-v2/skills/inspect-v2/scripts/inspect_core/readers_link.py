"""readers' roster, found the way the records component is found (contract section 6).

`packet` and `request` need to know whether the row the owner named is a Claude row (provider
`anthropic`) or an outside row, and `readers_request.build` needs the roster to decide
`authorized`. The roster is `<readers root>/skills/readers/assets/roster.json`, the root found by:

    --readers-root   an explicit folder, taken only when its manifest names `readers`
    route 3a         `<plugin root>/../readers`, the checkout sibling, when its manifest names `readers`
    route 3b         `<plugin root>/../../readers/<version>`, the installed shape: the highest dotted
                     version whose folder name equals its manifest's `version`

Nothing found is exit 3 (a missing dependency, like the records component), one line on stderr
naming every place looked. The script reads the roster and never runs readers: the executor
summons it (ruling E14-4).
"""
import json
import os

from station_core.records_client import ComponentUnavailable

NAME = "readers"
MANIFEST = os.path.join(".claude-plugin", "plugin.json")
ROSTER = os.path.join("skills", "readers", "assets", "roster.json")
DIGITS = "0123456789"


def _manifest(folder):
    try:
        with open(os.path.join(folder, MANIFEST), encoding="utf-8") as fh:
            body = json.load(fh)
        return body if isinstance(body, dict) else None
    except (OSError, ValueError):
        return None


def _version_key(name):
    parts = name.split(".")
    for part in parts:
        if not part or [ch for ch in part if ch not in DIGITS] or (len(part) > 1 and part[0] == "0"):
            return None
    return tuple(int(part) for part in parts)


def _usable(folder):
    body = _manifest(folder)
    return body is not None and body.get("name") == NAME and os.path.isfile(os.path.join(folder, ROSTER))


def resolve(plugin_root, argument=None):
    """{"root", "route", "roster"}; ComponentUnavailable (exit 3) naming every place looked."""
    looked = []
    if argument:
        looked.append(argument)
        if _usable(argument):
            return {"root": argument, "route": "argument", "roster": os.path.join(argument, ROSTER)}
    beside = os.path.join(plugin_root, os.pardir, NAME)
    looked.append(beside)
    if _usable(beside):
        return {"root": beside, "route": "3a", "roster": os.path.join(beside, ROSTER)}
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
            body = _manifest(folder)
            if body is None:
                looked.append("%s (no plugin.json)" % folder)
            elif body.get("version") != entry or _version_key(entry) is None:
                looked.append("%s (name differs from version %s)" % (folder, body.get("version")))
            elif not _usable(folder):
                looked.append("%s (no roster)" % folder)
            else:
                accepted.append((_version_key(entry), folder))
        if accepted:
            root = max(accepted)[1]
            return {"root": root, "route": "3b", "roster": os.path.join(root, ROSTER)}
    raise ComponentUnavailable("missing dependency: readers component (looked in: %s)" % ", ".join(looked))


def load(plugin_root, argument=None):
    found = resolve(plugin_root, argument)
    try:
        with open(found["roster"], encoding="utf-8") as fh:
            roster = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ComponentUnavailable("missing dependency: readers component at %s has no readable roster (%s)"
                                   % (found["root"], exc))
    return found, roster


def provider(roster, row):
    for entry in (roster or {}).get("rows") or []:
        if isinstance(entry, dict) and entry.get("id") == row:
            return entry.get("provider")
    return None
