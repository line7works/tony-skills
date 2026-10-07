#!/usr/bin/env python3
"""The tripwire of the trace proof (the E15 lane contract, ruling E15-7 and section 11): v1 plugins that leave a
marker when any file of theirs is read or run.

    build_copy(source, dest, markers) -> dest     a v1 plugin copied as a tripwire
    write_hook(folder) -> path of sitecustomize.py the audit hook a proof puts first on its own PYTHONPATH
    markers(folder) -> [marker]                    every marker left, in order
    armed(folder) -> [line]                        every process the hook was loaded into
    verdict(marks) -> {"verdict": PASS | FAIL, "markers": n, "why"}

THE COPY. A v1 plugin is copied whole into `dest`, then every file in it is replaced: its manifest stays as it was
(so the harness installs it beside its v2, under its own name and version), its `SKILL.md` keeps its frontmatter and
its body becomes one tripwire notice, every other file becomes a notice, and a v1 entry script is added at the place a
caller that took the v1 station for a v2 one would run it (`skills/<name>/scripts/<name>.py`, the v2 layout). That
entry, run by any interpreter in any mode (`-I` included, where no hook can load), appends a `ran` marker to the
markers folder named in it at build time and exits 1. The six v1 back-half plugins carry no script of their own, so
the added entry is the only thing in them that can run; a read is caught by the hook.

THE HOOK. `sitecustomize.py`, loaded by every Python process that has the hook's folder first on `PYTHONPATH` (and
is not started isolated): it records that it armed (`armed.log`), then `sys.addaudithook` watches the events that
read or run a file: `open`, `os.listdir`, `os.scandir`, `subprocess.Popen`, `os.exec`, `os.posix_spawn`,
`os.system`. A path argument (any argv element, for a launch) that sits under a root named in `TRIPWIRE_ROOTS`
(`os.pathsep`-separated; compared as given, absolute and resolved, without regard to letter case, and inside a shell
string only where the root ends at a separator, a quote, a space or the string's end, so a `<v1>-v2` folder beside a
watched `<v1>` is not under it) appends a marker
naming the event, the path and the process. A process started isolated (`-I`) or by another runtime is not hooked: a
read there is not seen, and a run of a v1 entry is still caught by the entry itself, and the launch by the hooked
parent's `subprocess.Popen` event.

THE VERDICT. Any marker is FAIL. Standard library only, Python 3.9.
"""
import json
import os
import shutil
import stat

NOTICE = "This file is a tripwire of the E15 trace proof: a read or a run of it leaves a marker.\n"
ENTRY = '''#!/usr/bin/env python3
"""A tripwire entry of the E15 trace proof: running it leaves a marker and fails."""
import json, os, sys, time
with open(os.path.join(%(markers)r, "markers.jsonl"), "a") as fh:
    fh.write(json.dumps({"event": "ran", "path": os.path.abspath(sys.argv[0]), "argv": sys.argv[1:],
                         "pid": os.getpid(), "at": time.time()}) + "\\n")
sys.stderr.write("a v1 tripwire entry ran: %%s\\n" %% os.path.abspath(sys.argv[0]))
sys.exit(1)
'''
HOOK = '''"""The E15 trace proof's audit hook (setups/tripwire.py writes this file; see its docstring)."""
import json
import os
import sys
import time


def _forms(path):
    out = set()
    for form in (os.path.abspath(path), os.path.realpath(path)):
        out.add(form.casefold().rstrip(os.sep))
    return out


_ROOTS = set()
for _root in (os.environ.get("TRIPWIRE_ROOTS") or "").split(os.pathsep):
    if _root:
        _ROOTS |= _forms(_root)
_MARKERS = os.environ.get("TRIPWIRE_MARKERS") or ""
_BUSY = [False]
_EVENTS = ("open", "os.listdir", "os.scandir", "subprocess.Popen", "os.exec", "os.posix_spawn", "os.system")


def _under(value):
    try:
        if isinstance(value, (bytes, os.PathLike)):
            value = os.fsdecode(os.fspath(value))
        if not isinstance(value, str) or not value:
            return False
        for form in _forms(value):
            for root in _ROOTS:
                if form == root or form.startswith(root + os.sep):
                    return True
        folded = value.casefold()
        for root in _ROOTS:
            start = folded.find(root)
            while start != -1:
                end = start + len(root)
                if end == len(folded) or folded[end] in (os.sep, " ", "\t", "'", '"', ";", "&", "|", ")"):
                    return True
                start = folded.find(root, start + 1)
    except Exception:
        return False
    return False


def _write(name, line):
    with open(os.path.join(_MARKERS, name), "a") as fh:
        fh.write(json.dumps(line, default=str) + "\\n")


def _hook(event, args):
    if _BUSY[0] or event not in _EVENTS or not _ROOTS or not _MARKERS:
        return
    _BUSY[0] = True
    try:
        values = []
        for arg in args or ():
            if isinstance(arg, (list, tuple)):
                values.extend(arg)
            else:
                values.append(arg)
        hits = [v for v in values if _under(v)]
        if hits:
            _write("markers.jsonl", {"event": event, "path": os.fsdecode(hits[0]) if isinstance(hits[0], bytes)
                                     else str(hits[0]), "pid": os.getpid(), "argv": sys.argv[:3], "at": time.time()})
    except Exception:
        pass
    finally:
        _BUSY[0] = False


if _ROOTS and _MARKERS:
    try:
        _BUSY[0] = True
        _write("armed.log", {"pid": os.getpid(), "executable": sys.executable, "argv": sys.argv[:3]})
    except Exception:
        pass
    finally:
        _BUSY[0] = False
    sys.addaudithook(_hook)
'''


def _frontmatter(text):
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[:end + 5]
    return ""


def build_copy(source, dest, markers):
    """`source` (a v1 plugin folder) copied to `dest` as a tripwire (module docstring, THE COPY); returns dest."""
    os.makedirs(markers, exist_ok=True)
    shutil.copytree(source, dest, symlinks=False)
    name = os.path.basename(os.path.normpath(source))
    for base, dirs, files in os.walk(dest):
        for leaf in files:
            path = os.path.join(base, leaf)
            rel = os.path.relpath(path, dest)
            if rel == os.path.join(".claude-plugin", "plugin.json"):
                continue
            if leaf == "SKILL.md":
                with open(path, "r", encoding="utf-8") as fh:
                    head = _frontmatter(fh.read())
                body = head + "\n# Tripwire\n\n" + NOTICE
            else:
                body = NOTICE
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
    entry = os.path.join(dest, "skills", name, "scripts", name + ".py")
    os.makedirs(os.path.dirname(entry), exist_ok=True)
    with open(entry, "w", encoding="utf-8") as fh:
        fh.write(ENTRY % {"markers": os.path.abspath(markers)})
    os.chmod(entry, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    return dest


def write_hook(folder):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "sitecustomize.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HOOK)
    return path


def _lines(path):
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if raw:
                try:
                    out.append(json.loads(raw))
                except ValueError:
                    out.append({"event": "unreadable marker line", "path": raw})
    return out


def markers(folder):
    return _lines(os.path.join(folder, "markers.jsonl"))


def armed(folder):
    return _lines(os.path.join(folder, "armed.log"))


def verdict(marks):
    if marks:
        return {"verdict": "FAIL", "markers": len(marks),
                "why": "a v1 file was read or run: %s %s" % (marks[0].get("event"), marks[0].get("path"))}
    return {"verdict": "PASS", "markers": 0, "why": "no v1 file was read or run"}
