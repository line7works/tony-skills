#!/usr/bin/python3
"""Slice 4's fakes (the contract's E16-8): the machine's schedule tools and the harness adapter, as fixtures. Standard
library only; never the network, never the real launchd, crontab or harness.

    set_tools.py <tool> <arguments...>

The tool is one of `plutil`, `launchctl`, `crontab` and `sun-adapter`. A
test's wrappers, named `fixture-<tool>`, start this file; no real program of those names is ever on a test's search list
(the tests rename the declarations' tools so). State lives in `$HOME/.fakes/<tool>/state.json`, every call in
`calls.jsonl`; every state change is one rename.

    plutil -extract Label json -o - FILE     the file's own `Label` as JSON text; exit 1 where it has none
    launchctl list LABEL                     exit 0 (a text answer, as the real one prints) where loaded, else 113
    launchctl unload FILE | load FILE        the file's Label taken out of, or put into, the loaded list; exit 0 always
                                             (the real one "will only return a non-zero exit code due to improper usage")
    crontab -l                               the table; exit 1 where there is none
    crontab FILE                             the table replaced by the file's text
    sun-adapter routines --holding T --format json      {"routines": [ids of the routines whose text holds T]}
    sun-adapter routine --id-file F --out O             {"state": ...}; the definition written to O; exit 3 where unknown
    sun-adapter routine-disable|routine-enable --id-file F   the routine's state set; the same id kept
    sun-adapter canary --in DIR              {"match": "same"} where DIR/AGENTS.md stands, else exit 1 (the adapter's canary,
                                             which a sunrise of the join's whole sequence asks of this one adapter)
"""
import hashlib
import json
import os
import re
import sys

TOOL = sys.argv[1]
ARGV = sys.argv[2:]
ROOT = os.path.join(os.environ.get("HOME", ""), ".fakes", TOOL)
STATE = os.path.join(ROOT, "state.json")


def load():
    try:
        with open(STATE) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save(state):
    os.makedirs(ROOT, exist_ok=True)
    with open(STATE + ".new", "w") as fh:
        json.dump(state, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(STATE + ".new", STATE)


def record(**more):
    os.makedirs(ROOT, exist_ok=True)
    doc = {"argv": ARGV}
    doc.update(more)
    with open(os.path.join(ROOT, "calls.jsonl"), "a") as fh:
        fh.write(json.dumps(doc, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def label_of(path):
    try:
        with open(path) as fh:
            found = re.search(r"<key>Label</key>\s*<string>([^<]*)</string>", fh.read())
    except OSError:
        return None
    return found.group(1) if found else None


def after(flag):
    return ARGV[ARGV.index(flag) + 1] if flag in ARGV and ARGV.index(flag) + 1 < len(ARGV) else None


def main():
    state = load()
    if TOOL == "plutil":
        record()
        label = label_of(ARGV[-1])
        if label is None:
            return 1
        sys.stdout.write(json.dumps(label) + "\n")
        return 0
    if TOOL == "launchctl":
        loaded = state.setdefault("loaded", [])
        if ARGV[:1] == ["list"]:
            record()
            if ARGV[1] in loaded:
                sys.stdout.write('{\n\t"Label" = "%s";\n};\n' % ARGV[1])
                return 0
            return 113
        label = label_of(ARGV[1])
        record(label=label)
        if label is not None:
            if ARGV[0] == "unload" and label in loaded:
                loaded.remove(label)
            elif ARGV[0] == "load" and label not in loaded:
                loaded.append(label)
            state.setdefault("sets", []).append({"do": ARGV[0], "label": label})
            save(state)
        return 0
    if TOOL == "crontab":
        if ARGV == ["-l"]:
            record()
            if state.get("table") is None:
                return 1
            sys.stdout.write(state["table"])
            return 0
        with open(ARGV[0]) as fh:
            given = fh.read()
        record(text=given, mode=oct(os.stat(ARGV[0]).st_mode & 0o777))
        state["table"] = given
        state.setdefault("sets", []).append({"do": "replace", "table": hashlib.sha256(given.replace(os.environ.get("HOME", ""), "<home>").encode("utf-8")).hexdigest()[:16]})
        save(state)
        return 0
    if TOOL == "sun-adapter":
        routines = state.setdefault("routines", {})
        if ARGV[:1] == ["canary"]:
            record()
            if not os.path.isfile(os.path.join(after("--in") or "", "AGENTS.md")):
                return 1
            sys.stdout.write(json.dumps({"match": "same"}))
            return 0
        if ARGV[:1] == ["routines"]:
            record()
            holding = after("--holding") or ""
            sys.stdout.write(json.dumps({"routines": sorted(i for i, r in routines.items() if holding in r.get("text", ""))}))
            return 0
        with open(after("--id-file")) as fh:
            rid = fh.read().strip()
        record(id=rid)
        if rid not in routines:
            return 3
        if ARGV[0] == "routine":
            out = after("--out")
            if out and out != os.devnull:
                with open(out, "w") as fh:
                    fh.write(routines[rid].get("definition", ""))
            sys.stdout.write(json.dumps({"state": routines[rid]["state"]}))
            return 0
        routines[rid]["state"] = "disabled" if ARGV[0] == "routine-disable" else "active"
        state.setdefault("sets", []).append({"do": ARGV[0], "id": rid})
        save(state)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
