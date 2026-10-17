#!/usr/bin/python3
"""One fake provider's tool (the contract's E16-8). Standard library only; never the network.

    fakeprov.py <tool> <command> [--name value ...]

It keeps its state in a file under `$HOME/.fakes/<tool>/`: `state.json` (what exists at the fake
provider), `calls.jsonl` (every call's arguments and the NAMES of the environment variables it was
given, and the same for any child it started), `issued.jsonl` (every value it issued, for the scan),
and `plan.json` (what the test told it to do). A plan entry is matched by command and by the number
of that command's call and tells the fake to fail, to hang, to answer late, to echo a value into
its error text (whole, in part, encoded, split across writes), to answer with a given document, to
make the thing and lose the answer, to start a child of its own, or to write a file. The fake can
be killed at any moment: every state change is one rename.

Commands (the default behaviour, where no plan entry says otherwise):
    whoami                                  the account it acts as
    create --kind K --name N                a new thing with a fresh id; exit 4 where the name is taken
    request-status --name N                 the status of the last create request for that name
    get --name N | --id-file PATH           one thing's state
    list --kind K                           the things of a kind (names and a count)
    set --name N --state S [--if S0]        a state change; with --if, refused (exit 4) unless the state is S0
    cas --ref R --new V --old V             compare-and-swap of a named value; exit 4 where it is not V
    ref --ref R                             the value of a named value
    write --out PATH [--lines N]            writes a secret-bearing file (the canary of its state) at PATH
    dump --out PATH                         writes a dump at PATH; reads the connection from the private file
    inventory                               the list of what a dump would hold, and the source's identity
    issue                                   a fresh secret in a secret field
    issued                                  whether a secret was issued
    scan --path P                           reads a path and answers whether its state's canary is in it
    scaffold --out PATH                     builds a small tree at PATH
    noop                                    answers ok
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import time

TOOL = sys.argv[1]
ARGV = sys.argv[2:]
HOME = os.environ.get("HOME", "")
ROOT = os.path.join(HOME, ".fakes", TOOL)
STATE = os.path.join(ROOT, "state.json")
CALLS = os.path.join(ROOT, "calls.jsonl")
ISSUED = os.path.join(ROOT, "issued.jsonl")
PLAN = os.path.join(ROOT, "plan.json")
COUNTS = os.path.join(ROOT, "counts.json")


SHELL_OWN = ("PWD", "SHLVL", "_", "OLDPWD", "FAKE_GIVEN")


def given():
    """The environment this fake was given, as its wrapper saw it before the interpreter started."""
    out = {}
    for line in os.environ.get("FAKE_GIVEN", "").split("\n"):
        if "=" in line:
            name, value = line.split("=", 1)
            if name not in SHELL_OWN:
                out[name] = value
    return out


def load(path, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def save_state(state):
    os.makedirs(ROOT, exist_ok=True)
    tmp = STATE + ".new"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, STATE)


def append(path, doc):
    os.makedirs(ROOT, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(doc, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def issue(state, kind):
    state["issued"] = state.get("issued", 0) + 1
    value = "issued" + hashlib.sha256(("%s:%s:%s:%d" % (HOME, TOOL, kind, state["issued"])).encode()).hexdigest()[:24]
    append(ISSUED, {"value": value, "kind": kind})
    return value


def options(args):
    out, i = {}, 0
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            out[args[i][2:]] = args[i + 1]
            i += 2
        else:
            i += 1
    return out


def answer(doc, code=0):
    sys.stdout.write(json.dumps(doc))
    sys.stdout.flush()
    sys.exit(code)


def main():
    command = ARGV[0] if ARGV else ""
    opts = options(ARGV[1:])
    state = load(STATE, {"account": "fixture-account", "things": {}, "refs": {}, "requests": {}})
    counts = load(COUNTS, {})                 # kept apart from the state, so that a read leaves the state byte-equal
    counts[command] = nth = counts.get(command, 0) + 1
    os.makedirs(ROOT, exist_ok=True)
    with open(COUNTS, "w") as fh:
        json.dump(counts, fh)
    changing = command in ("create", "set", "cas", "write", "dump", "scaffold", "issue")
    env = given()
    append(CALLS, {"tool": TOOL, "argv": ARGV, "env_names": sorted(env), "cwd": os.getcwd(), "pid": os.getpid(),
                   "changing": changing, "nth": nth, "env_values": env})
    plan = [p for p in load(PLAN, []) if p.get("command") == command and p.get("nth", nth) == nth]
    todo = plan[0] if plan else {}
    do = todo.get("do")
    if do == "die":                           # started, its call recorded, and then killed before it does anything
        os.kill(os.getpid(), 9)
    if do == "hang":
        if todo.get("child"):
            subprocess.Popen([sys.executable, "-B", os.path.abspath(__file__), TOOL, "sleep-child"])
        time.sleep(600)
    if do == "late":
        time.sleep(float(todo.get("seconds", 0.3)))
    if do == "echo":
        value = todo.get("value", "")
        raw = value.encode()
        sys.stderr.write("error: %s\n" % value)
        sys.stderr.write("part: %s\n" % value[: max(1, len(value) // 2)])
        sys.stderr.write("b64: %s\n" % base64.b64encode(raw).decode())
        for ch in value:
            sys.stderr.write(ch)
            sys.stderr.flush()
        sys.stdout.write(todo.get("stdout_text", value))
        sys.exit(int(todo.get("exit", 1)))
    if do == "log":
        append(os.path.join(ROOT, "own.log"), {"value": todo.get("value", "")})
    if do == "fail":
        answer(todo.get("stdout", {}), int(todo.get("exit", 1)))
    if do == "raw":
        sys.stdout.write(todo.get("text", ""))
        sys.exit(int(todo.get("exit", 0)))
    if do == "big":
        sys.stdout.write("x" * int(todo.get("bytes", 5000000)))
        sys.exit(0)
    if do == "child":
        subprocess.Popen([sys.executable, "-B", os.path.abspath(__file__), TOOL, "sleep-child"])
    if command == "sleep-child":
        append(os.path.join(ROOT, "children.jsonl"), {"pid": os.getpid(), "pgid": os.getpgid(0), "argv": ARGV,
                                                     "env_names": sorted(given()), "env_values": given()})
        time.sleep(600)
    if command == "whoami":
        answer(todo.get("stdout") or {"account": state.get("account")})
    if command == "create":
        things = state["things"]
        name = opts.get("name", "")
        if name in things and not todo.get("allow_duplicate"):
            answer({"kind": "conflict"}, 4)
        if do == "terms":
            answer({"kind": "terms"}, 6)
        ident = issue(state, "id")
        state["requests"][name] = {"made": True, "id": ident}
        key = name if name not in things else name + "#2"
        things[key] = {"id": ident, "kind": opts.get("kind", ""), "state": "active", "name": name}
        save_state(state)
        if do == "lose-answer":
            sys.exit(0) if todo.get("empty") else os._exit(9)
        doc = {"id": ident, "name": name, "state": "active"}
        doc.update(todo.get("extra") or {})
        for gone in todo.get("omit") or []:
            doc.pop(gone, None)
        answer(doc)
    if command == "request-status":
        request = state["requests"].get(opts.get("name", ""))
        if todo.get("stdout") is not None:
            answer(todo["stdout"])
        if request and request.get("made"):
            answer({"made": "made", "id": request["id"]})
        answer({"made": "nothing"})
    if command == "get":
        name = opts.get("name")
        if opts.get("id-file"):
            ident = open(opts["id-file"]).read().strip()
            found = [t for t in state["things"].values() if t["id"] == ident]
        else:
            found = [state["things"][name]] if name in state["things"] else []
        if todo.get("stdout") is not None:
            answer(todo["stdout"], int(todo.get("exit", 0)))
        if not found:
            answer({"kind": "not-found"}, 3)
        answer({"state": found[0]["state"], "name": todo.get("name_as", found[0]["name"]), "id": found[0]["id"], "count": len(state["things"])})
    if command == "identify":
        if not state.get("identity"):
            answer({"kind": "not-found"}, 3)
        answer({"identity": state["identity"]})
    if command == "list":
        names = sorted(t["name"] for t in state["things"].values() if not opts.get("kind") or t["kind"] == opts["kind"])
        answer(todo.get("stdout") or {"names": names, "count": len(names)})
    if command == "set":
        thing = state["things"].get(opts.get("name", ""))
        if thing is None:
            answer({"kind": "not-found"}, 3)
        if opts.get("if") is not None and thing["state"] != opts["if"]:
            answer({"kind": "conflict"}, 4)
        thing["state"] = todo.get("state_as", opts.get("state", thing["state"]))
        state.setdefault("sets", []).append({"name": thing["name"], "state": thing["state"]})
        save_state(state)
        answer({"state": thing["state"]})
    if command == "cas":
        refs = state["refs"]
        if refs.get(opts.get("ref"), "none") != opts.get("old", "none"):
            answer({"kind": "conflict"}, 4)
        refs[opts.get("ref")] = opts.get("new")
        save_state(state)
        answer({"ref": opts.get("new")})
    if command == "ref":
        answer({"ref": state["refs"].get(opts.get("ref"), "none")})
    if command == "write":
        secret = state.get("secret") or issue(state, "env")
        state["secret"] = secret
        save_state(state)
        target = opts.get("out", "")
        lines = ["FIXTURE_URL=%s" % secret, "FIXTURE_KEY=%s" % secret[::-1]]
        if do == "half":
            lines = lines[:1]
        if do == "empty":
            lines = []
        with open(target, "w") as fh:
            fh.write("\n".join(lines) + ("\n" if lines else ""))
        if todo.get("mode"):
            os.chmod(target, int(todo["mode"], 8))
        answer({"keys": ["FIXTURE_URL", "FIXTURE_KEY"][: len(lines)], "count": len(lines)})
    if command in ("dump", "inventory"):
        passfile = os.environ.get("FAKEDUMP_PASSFILE", "")
        seen = {"passfile": passfile, "passfile_mode": None, "passfile_text": None}
        if passfile and os.path.exists(passfile):
            seen["passfile_mode"] = oct(os.stat(passfile).st_mode & 0o777)
            seen["passfile_text"] = open(passfile).read()
        append(os.path.join(ROOT, "passfile.jsonl"), seen)
        source = state.get("database") or {"identity": "db-" + hashlib.sha256(HOME.encode()).hexdigest()[:10],
                                           "tables": ["alpha", "beta"]}
        state["database"] = source
        save_state(state)
        unreadable = [t for t in source["tables"] if t in (state.get("unreadable") or [])]
        if command == "inventory":
            found = {"identity": source["identity"], "tables": source["tables"], "count": len(source["tables"]),
                     "readable": "no" if unreadable else "yes"}
            if unreadable:
                found["unreadable"] = unreadable[0]      # the name of a table that cannot be read: the provider's word
            answer(found)
        if unreadable:
            answer({"kind": "other"}, 5)
        body = "".join("TABLE %s\n" % t for t in source["tables"]) + "DATA %s\n" % (state.get("secret") or "none")
        if do == "short":
            body = body[: len(body) // 2]
        with open(opts.get("out", ""), "w") as fh:
            fh.write(body)
        if todo.get("then_add_table"):
            source["tables"].append(todo["then_add_table"])
            save_state(state)
        answer({"identity": source["identity"], "tables": body.count("TABLE "), "count": int(todo.get("report_count", body.count("TABLE "))),
                "inventory": [l[6:] for l in body.splitlines() if l.startswith("TABLE ")]})
    if command == "issued":
        answer({"made": "made" if state.get("secret_issued") else "nothing"})
    if command == "issue":
        value = todo.get("value") if todo.get("value") is not None else issue(state, "secret")
        state["secret_issued"] = True
        save_state(state)
        doc = {"token": value, "state": "issued"}
        doc.update(todo.get("extra") or {})
        for gone in todo.get("omit") or []:
            doc.pop(gone, None)
        if "text" in todo:
            sys.stdout.write(todo["text"])
            sys.exit(0)
        answer(doc)
    if command == "scan":
        hit = False
        for base, _dirs, files in os.walk(opts.get("path", "")):
            for name in files:
                try:
                    hit = hit or (state.get("canary") or "\0") in open(os.path.join(base, name), errors="replace").read()
                except OSError:
                    pass
        answer({"clean": not hit})
    if command == "scaffold":
        target = opts.get("out", "")
        os.makedirs(os.path.join(target, "src"))
        for rel, text in (("README.md", "# scaffold\n"), ("src/main.txt", "main\n")):
            fd = os.open(os.path.join(target, rel), os.O_WRONLY | os.O_CREAT, int(todo.get("mode", "644"), 8))   # it asks for wider
            os.write(fd, text.encode())
            os.close(fd)
        for line in todo.get("git") or []:
            subprocess.call(["fakegit"] + line)
        answer({"files": 2})
    if command == "noop":
        answer(todo.get("stdout") or {"ok": True})
    answer({"kind": "other"}, 2)


main()
