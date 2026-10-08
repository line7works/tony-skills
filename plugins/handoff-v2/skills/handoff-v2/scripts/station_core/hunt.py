"""Document selection, one function for the four cores (ruling E14-10).

    hunt(homes, roots, name=None) -> {"outcome": "none" | "one" | "several",
                                      "candidates": [...], "searched": [...]}

`homes` is the calling core's table, never guessed here: a list of
`{"home": <label>, "root": <key of roots>, "globs": [<pattern>, ...], "tier": <int>}`. `roots` maps
each root key to an absolute directory (`workspace`, `staging`, ...) or None when the caller has
none. A glob is relative to its root; `{name}` in it is replaced by `name` (one path segment of
lowercase letters, digits, `.`, `_`, `-`), or by `*` when no name is given.

Every home is searched and reported in `searched`, a home whose root the caller did not give
included (`given: false`). The candidates are those of the lowest tier that holds any; one of
them is `one`, two or more are `several` (listed for the owner, never picked), none is `none`.
The helper never expands `~`, never takes a relative root, and never lets a glob leave its root; a
root is taken literally, a glob metacharacter in its path escaped (`glob.escape`).

A candidate is listed as its folder spells it (E14 slice 3c, item 3.3): a case-insensitive file
system answers a literal glob (`docs/{name}-scope.md`) under the name as typed, so the file name is
taken from the folder listing when exactly one entry matches it case-insensitively; several such
entries, or none, and the path stays as found (blueprint's `_disk_spelling` rule). The `select`
envelope, `selection-<hunt>.json` and every later use of a candidate then carry the disk spelling,
and a pick named in that spelling is one of the candidates.
"""
import glob
import os
import re

NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
OUTCOMES = ("none", "one", "several")


class HuntRefused(ValueError):
    """The call itself is malformed: a bad name, a bad root, a glob that leaves its home."""


def _check_root(key, root):
    if root is None:
        return None
    if not isinstance(root, str) or not root:
        raise HuntRefused("the root %r is not a path" % key)
    if root.startswith("~"):
        raise HuntRefused("the root %r is %r: a path is passed resolved, never expanded here" % (key, root))
    if not os.path.isabs(root):
        raise HuntRefused("the root %r is %r: a root is an absolute path" % (key, root))
    return os.path.normpath(root)


def _pattern(glob_text, name):
    if os.path.isabs(glob_text) or glob_text.startswith("~"):
        raise HuntRefused("the glob %r is relative to its home" % glob_text)
    parts = glob_text.replace("\\", "/").split("/")
    if any(part in ("..", ".") for part in parts):
        raise HuntRefused("the glob %r leaves its home" % glob_text)
    return glob_text.replace("{name}", name if name is not None else "*")


def disk_spelling(path):
    """`path` with its file name as the folder listing spells it: the one entry that matches it
    case-insensitively; the path as found when the name is listed as is, or when several entries
    match, or none, or the folder cannot be listed."""
    folder, name = os.path.split(path)
    try:
        names = os.listdir(folder)
    except OSError:
        return path
    if name in names:
        return path
    same = [entry for entry in names if entry.casefold() == name.casefold()]
    return os.path.join(folder, same[0]) if len(same) == 1 else path


def hunt(homes, roots, name=None):
    if name is not None and (not isinstance(name, str) or not NAME.match(name)):
        raise HuntRefused("the name %r is not one path segment of lowercase letters, digits, "
                          "'.', '_' and '-'" % (name,))
    checked = {}
    for key, value in (roots or {}).items():
        checked[key] = _check_root(key, value)
    searched = []
    by_tier = {}
    for home in homes:
        label, key, tier = home["home"], home["root"], int(home.get("tier", 1))
        globs = list(home["globs"])
        root = checked.get(key)
        row = {"home": label, "root": key, "globs": globs, "tier": tier, "given": root is not None,
               "found": []}
        patterns = [_pattern(g, name) for g in globs]
        if root is not None:
            found = set()
            for pattern in patterns:
                # the root is escaped (a `[`, `*` or `?` in its path is literal); the pattern is not
                for path in glob.glob(os.path.join(glob.escape(root), pattern)):
                    if os.path.isfile(path) and os.path.realpath(path).startswith(
                            os.path.realpath(root).rstrip(os.sep) + os.sep):
                        found.add(disk_spelling(os.path.normpath(path)))
            row["found"] = sorted(found)
            for path in row["found"]:
                by_tier.setdefault(tier, []).append({"path": path, "home": label, "tier": tier})
        searched.append(row)
    candidates = []
    if by_tier:
        seen = set()
        for cand in by_tier[min(by_tier)]:
            if cand["path"] not in seen:
                seen.add(cand["path"])
                candidates.append(cand)
    outcome = "none" if not candidates else ("one" if len(candidates) == 1 else "several")
    return {"outcome": outcome, "candidates": candidates, "searched": searched}
