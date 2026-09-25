"""A v2 sibling plugin's root, resolved the way the records component is (ruling E14-7).

    resolve(name, plugin_root, argument=None) -> {"root", "route", "looked"}
    skill_file(root, name) -> <root>/skills/<name>/SKILL.md

inspect-v2's code book is `blueprint-v2`'s installed `SKILL.md`; this is how it is found, never
through a v1 folder and never through a personal path:

    argument   an explicit folder (a test hook): taken only when its manifest names `name`
    route 3a   `<plugin_root>/../<name>`, the checkout sibling, when its manifest names `name`
    route 3b   `<plugin_root>/../../<name>/<version>`, the installed shape: the highest dotted
               version whose folder name equals its manifest's version and whose manifest names
               `name`

`name` must be a v2 plugin name (`<word>[-<word>...]-v2`, lowercase); anything else, a v1
station's name included, is refused before any folder is looked at (`SiblingRefused`). A folder
whose manifest names a plugin other than `name` is never taken, so a v1 plugin cannot stand in for
its v2 sibling. Nothing found raises `LookupError` naming every place looked.
"""
import json
import os
import re

V2_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-v2$")
MANIFEST = os.path.join(".claude-plugin", "plugin.json")
DIGITS = "0123456789"


class SiblingRefused(ValueError):
    """A name or a folder that is not a v2 sibling."""


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


def resolve(name, plugin_root, argument=None):
    if not isinstance(name, str) or not V2_NAME.match(name):
        raise SiblingRefused("%r is not a v2 plugin name: a code book or any other sibling is a -v2 "
                             "plugin, never a v1 station" % (name,))
    looked = []
    if argument:
        body = _manifest(argument)
        if body is None or body.get("name") != name:
            raise SiblingRefused("the folder %s holds %s, not the v2 plugin %s" % (
                argument, "no plugin manifest" if body is None else "the plugin %r" % body.get("name"), name))
        return {"root": argument, "route": "argument", "looked": [argument]}
    beside = os.path.join(plugin_root, os.pardir, name)
    looked.append(beside)
    body = _manifest(beside)
    if body is not None and body.get("name") == name:
        return {"root": beside, "route": "3a", "looked": looked}
    if body is not None:
        looked[-1] = "%s (its manifest names %r)" % (beside, body.get("name"))
    base = os.path.join(plugin_root, os.pardir, os.pardir, name)
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
            elif body.get("name") != name:
                looked.append("%s (its manifest names %r)" % (folder, body.get("name")))
            elif body.get("version") != entry:
                looked.append("%s (name differs from version %s)" % (folder, body.get("version")))
            elif _version_key(entry) is None:
                looked.append("%s (version not dotted integers)" % folder)
            else:
                accepted.append((_version_key(entry), folder))
        if accepted:
            return {"root": max(accepted)[1], "route": "3b", "looked": looked}
    raise LookupError("missing sibling: %s (looked in: %s)" % (name, ", ".join(looked)))


def skill_file(root, name):
    path = os.path.join(root, "skills", name, "SKILL.md")
    if not os.path.isfile(path):
        raise LookupError("missing sibling file: %s" % path)
    return path
