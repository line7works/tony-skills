#!/usr/bin/python3
"""The fakes of slice 3's four providers (the contract's E16-8). Standard library only; never the network.

    prov_fake.py <tool> <argument>...        tool: gh, vercel, psql, pg_dump, curl

`fakeprov.py` answers a fixed set of commands by its own names; these tools take the real programs' argument forms
(rows-prov section 3.0), so they have a fake of their own. A test writes a wrapper of each tool's name into a folder of
the fixture's (`provlib.programs`), which starts this file with the tool's name first.

State, one JSON file per provider under `$HOME/.fakes/<provider>/state.json`, every change one rename:

- `gh`: {"account", "things": {name: {"id", "kind": "repo", "state": "active" | "archived", "name"}}, "sets": [...]};
  each repository's commits stand in a bare repository `$HOME/.fakes/gh/remotes/<account>/<name>.git`, which a test's
  `~/.gitconfig` names in place of `https://github.com/` (so the real `git push` lands there and nowhere else).
- `vercel` (shared by the CLI fake and `VercelAPI`, the frame's own requests): {"team", "things": {slug: {"id", "kind":
  "project", "state": "active" | "paused", "name", "account", "repo"}}, "sets", "envs": {slug: [{"key", "value", "type",
  "target": [...], "custom": id or absent}]}, "custom": {slug: [{"id", "slug"}]}, "installed": bool, "resources": {name:
  {"id", "project", "connected"}}, "deployments": {slug: {"readyState"}}, "hidden": n, "next": n}.
- `pg`: {"identity", "tables": {name: [row, ...]}, "unreadable": [name, ...], "ending", "restrict_key"}; `ending` is how
  its pg_dump writes a plain dump: "unrestrict" (pg_dump 18.6's `\\restrict %s\n\n` after the header block and
  `\\unrestrict %s\n\n` after the completion block), "unrestrict-1" (the same, the binary's other `\\unrestrict %s\n`),
  "old" (neither line, the versions before 17.6); absent, `DUMP_ENDING`. `restrict_key` is the key (`RESTRICT_KEY` absent).

`calls.jsonl` beside each state holds every call's arguments and the NAMES of its environment (never a value); a plan
entry in `plan.json` (`{"tool", "command", "do": "fail" | "lose-answer" | "short" | "die", "exit", "stdout", "nth"}`) makes
one call answer otherwise; a pg_dump entry's `drop` names a table whose data section the copy leaves out, and its `tail`
is text written after the dump's end.
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse

HOME = os.environ.get("HOME", "")
GIT = "/usr/bin/git"


def root(provider, home=None):
    return os.path.join(home or HOME, ".fakes", provider)


def load(provider, home=None):
    try:
        with open(os.path.join(root(provider, home), "state.json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save(provider, state, home=None):
    os.makedirs(root(provider, home), exist_ok=True)
    path = os.path.join(root(provider, home), "state.json")
    with open(path + ".new", "w") as fh:
        json.dump(state, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(path + ".new", path)


def load_at(home, provider):
    return load(provider, home)


def save_at(home, provider, state):
    save(provider, state, home)


def note(provider, doc, home=None):
    os.makedirs(root(provider, home), exist_ok=True)
    with open(os.path.join(root(provider, home), "calls.jsonl"), "a") as fh:
        fh.write(json.dumps(doc, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def planned(provider, command, home=None):
    """The plan entry for this call of `command`, counted per command (`nth`), or {}."""
    counts_path = os.path.join(root(provider, home), "counts.json")
    try:
        with open(counts_path) as fh:
            counts = json.load(fh)
    except (OSError, ValueError):
        counts = {}
    counts[command] = nth = counts.get(command, 0) + 1
    os.makedirs(root(provider, home), exist_ok=True)
    with open(counts_path, "w") as fh:
        json.dump(counts, fh)
    try:
        with open(os.path.join(root(provider, home), "plan.json")) as fh:
            plan = json.load(fh)
    except (OSError, ValueError):
        plan = []
    found = [p for p in plan if p.get("command") == command and p.get("nth", nth) == nth]
    return found[0] if found else {}


def made_id(prefix, *parts):
    """An id the fake host issues: the same for the same thing on every fixture machine, so that the kill sweep's machines
    end byte-equal to its reference."""
    return prefix + hashlib.sha256(":".join(parts).encode()).hexdigest()[:20]


def answer(doc, code=0):
    if doc is not None:
        sys.stdout.write(json.dumps(doc) if not isinstance(doc, str) else doc)
    sys.stdout.flush()
    sys.exit(code)


def as_planned(todo):
    if todo.get("do") == "die":
        os.kill(os.getpid(), 9)
    if todo.get("do") == "fail":
        answer(todo.get("stdout", {}), int(todo.get("exit", 1)))


def remote(account, name, home=None):
    return os.path.join(root("gh", home), "remotes", account, name + ".git")


def remote_ref(account, name, ref, home=None):
    bare = remote(account, name, home)
    if not os.path.isdir(bare):
        return None
    proc = subprocess.run([GIT, "--git-dir", bare, "rev-parse", "--verify", "-q", ref + "^{commit}"], stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, env={"PATH": "/usr/bin:/bin", "HOME": home or HOME})
    return proc.stdout.decode().strip() or None if proc.returncode == 0 else None


def fields_of(args):
    """gh's `-f k=v` and `-F k=v` pairs."""
    out, i = {}, 0
    while i < len(args):
        if args[i] in ("-f", "-F") and i + 1 < len(args):
            key, _, value = args[i + 1].partition("=")
            out[key] = value
            i += 2
        else:
            i += 1
    return out


# ---- gh ----------------------------------------------------------------------------------------------------------
def gh(args):
    state = load("gh")
    state.setdefault("account", "fixture-account")
    state.setdefault("things", {})
    given = fields_of(args)
    if args[:2] == ["api", "graphql"] and "viewer{login}" in given.get("query", ""):
        command = "whoami"
    elif args[:2] == ["api", "graphql"]:
        command = "repo-read"
    elif args[:4] == ["api", "-X", "POST", "user/repos"]:
        command = "create"
    elif args[:3] == ["api", "-X", "PATCH"]:
        command = "archive-set"
    else:
        command = "other"
    note("gh", {"command": command, "argv": args, "env_names": sorted(os.environ)})
    todo = planned("gh", command)
    as_planned(todo)
    account = state["account"]
    if command == "whoami":
        answer({"data": {"viewer": {"login": account}}})
    if command == "repo-read":
        thing = state["things"].get(given.get("name", ""))
        if thing is None:
            answer({"data": {"viewer": {"repository": None}}})
        head = remote_ref(account, thing["name"], given.get("ref", ""))
        answer({"data": {"viewer": {"repository": {"id": thing["id"], "isArchived": thing["state"] == "archived",
                                                   "name": thing["name"], "ref": {"target": {"oid": head}} if head else None}}}})
    if command == "create":
        name = given.get("name", "")
        if name in state["things"]:
            sys.stderr.write("HTTP 422: name already exists on this account\n")
            answer(None, 1)
        ident = made_id("R_", "repo", name)
        state["things"][name] = {"id": ident, "kind": "repo", "state": "active", "name": name, "private": given.get("private") == "true"}
        bare = remote(account, name)
        os.makedirs(os.path.dirname(bare), exist_ok=True)
        subprocess.run([GIT, "init", "-q", "--bare", bare], env={"PATH": "/usr/bin:/bin", "HOME": HOME}, check=True)
        save("gh", state)
        if todo.get("do") == "lose-answer":
            answer(None, 1)
        answer({"node_id": ident, "name": name, "owner": {"login": account}, "private": given.get("private") == "true"})
    if command == "archive-set":
        owner, _, name = args[3].partition("repos/")[2].partition("/")
        thing = state["things"].get(name)
        if thing is None or owner != account:
            sys.stderr.write("HTTP 404\n")
            answer(None, 1)
        thing["state"] = "archived" if given.get("archived") == "true" else "active"
        state.setdefault("sets", []).append({"name": name, "state": thing["state"]})
        save("gh", state)
        answer({"archived": thing["state"] == "archived", "name": name})
    answer(None, 1)


# ---- vercel (the CLI) ------------------------------------------------------------------------------------------------
def option(args, name):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else None


def team_ok(state, args):
    return option(args, "--scope") == state.get("team", "fixture-team") and "--non-interactive" in args


def dotenv_line(key, value):
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '%s="%s"\n' % (key, escaped)


def vercel(args):
    state = load("vercel")
    words = [a for a in args if not a.startswith("--")]
    command = {("api",): "cli-team", ("env", "pull"): "env-pull", ("integration", "installations"): "db-installed",
               ("integration", "add"): "db-add", ("integration", "list"): "db-list",
               ("integration", "resource"): "db-connect"}.get(tuple(words[:1]) if words[:1] == ["api"] else tuple(words[:2]), "other")
    note("vercel", {"command": command, "argv": args, "env_names": sorted(os.environ)})
    todo = planned("vercel", command)
    as_planned(todo)
    if not team_ok(state, args):
        sys.stderr.write("Error: the scope is not one this session can act for\n")
        answer(None, 1)
    if command == "cli-team":
        # `vercel api <path>`: the team read answers only on the path of the team the scope names (G24-2)
        if words[1:2] != ["/v2/teams/" + state.get("team", "fixture-team")]:
            sys.stderr.write("Error: not found\n")
            answer(None, 1)
        answer({"slug": state.get("team", "fixture-team")})
    if command == "env-pull":
        out, env, cwd = words[2] if len(words) > 2 else "", option(args, "--environment"), option(args, "--cwd")
        try:
            with open(os.path.join(cwd or "", ".vercel", "project.json")) as fh:
                linked = json.load(fh).get("projectId")
        except (OSError, ValueError, TypeError, AttributeError):
            linked = None
        slugs = [s for s, t in (state.get("things") or {}).items() if t.get("id") == linked and t.get("kind") == "project"]
        if not slugs:
            sys.stderr.write("Error: the folder is not linked\n")
            answer(None, 1)
        slug = slugs[0]
        lines = []
        for item in (state.get("envs") or {}).get(slug, []):
            if item.get("custom") or env not in item.get("target", []):
                continue
            # a Sensitive value is never returned: the pull writes its key with an empty placeholder (D10)
            value = "" if item.get("type") == "sensitive" else item["value"]
            # a pull that wrote a value's line break raw (a plan's `raw-break`): the value runs onto a line of its own
            lines.append("%s=%s\n" % (item["key"], value) if todo.get("do") == "raw-break" else dotenv_line(item["key"], value))
        if todo.get("do") == "short":
            lines = lines[:1]
        with open(out, "w") as fh:
            fh.write("# Created by the fake vercel CLI\n" + "".join(lines))
        if todo.get("then_add"):
            (state.setdefault("envs", {}).setdefault(slug, [])).append(todo["then_add"])
            save("vercel", state)
        answer(None, 0)
    if command == "db-installed":
        answer({"installed": bool(state.get("installed", True))})
    if command == "db-add":
        name = option(args, "--name")
        resources = state.setdefault("resources", {})
        key = name if name not in resources else name + "#2"
        resources[key] = {"id": made_id("res_", name, str(len(resources))), "project": None, "connected": False}
        state.setdefault("things", {})[key] = {"kind": "database", "state": "made", "name": name}
        save("vercel", state)
        if todo.get("do") == "lose-answer":
            answer(None, 1)
        answer({"resource": {"id": resources[key]["id"], "name": name}})
    if command == "db-list":
        slug = words[2] if len(words) > 2 else ""
        found = (state.get("resources") or {}).get(slug + "-db")
        answer({"resource": {"id": found["id"], "connected": found["connected"]}} if found else {})
    if command == "db-connect":
        name, slug = words[3], words[4]
        found = (state.get("resources") or {}).get(name)
        if found is None:
            answer(None, 1)
        found["connected"], found["project"] = True, slug
        state.setdefault("sets", []).append({"name": name, "state": "connected"})
        save("vercel", state)
        answer({"connected": True})
    answer(None, 1)


class VercelAPI(object):
    """The frame's own requests to `api.vercel.com`, answered from the shared state; every request recorded with its method,
    path and query, and whether it carried a token, never the token."""

    HOST = "api.vercel.com"

    def __init__(self, home, token=None):
        self.home, self.token = home, token

    def request(self, host, method, path, headers, timeout, body=None):
        home = self.home
        state = load("vercel", home)
        split = urllib.parse.urlsplit(path)
        parts = [urllib.parse.unquote(p) for p in split.path.strip("/").split("/")]
        query = dict(urllib.parse.parse_qsl(split.query))
        authorized = bool(self.token) and headers.get("Authorization") == "Bearer " + self.token
        note("vercel", home=home, doc={"request": method, "path": parts, "query": sorted(query), "token": authorized,
                        "body": json.loads(body.decode()) if body else None})
        if host != self.HOST:
            return 404, b"{}"
        if not authorized:
            return 403, b"{}"
        team = state.get("team", "fixture-team")
        name = (method,) + tuple(parts[:2])
        todo = planned("vercel", "%s %s" % (method, "/".join(parts[:2])), home)
        if todo.get("do") == "fail":
            return int(todo.get("status", 500)), json.dumps(todo.get("stdout", {})).encode()
        if parts[:2] == ["v2", "teams"]:
            return (200, json.dumps({"slug": team}).encode()) if parts[2:] == [team] else (404, b"{}")
        if query.get("slug") != team:
            return 403, b"{}"
        projects = state.setdefault("things", {})
        if name == ("POST", "v11", "projects"):
            doc = json.loads(body.decode())
            slug = doc.get("name")
            if slug in projects:
                return 409, json.dumps({"error": {"code": "conflict"}}).encode()
            ident = made_id("prj_", slug).replace("-", "_")
            projects[slug] = {"id": ident, "kind": "project", "state": "active", "name": slug, "account": "team_" + ident[4:14],
                              "repo": (doc.get("gitRepository") or {}).get("repo", "").partition("/")[2]}
            state.setdefault("deployments", {})[slug] = {"readyState": "READY"}
            save("vercel", state, home)
            if todo.get("do") == "lose-answer":
                return 500, b""
            return 200, json.dumps({"id": ident, "name": slug, "accountId": projects[slug]["account"]}).encode()
        if parts[:2] == ["v9", "projects"] and len(parts) == 3 and method == "GET":
            # the path takes the project's id or its name (`idOrName`)
            thing = projects.get(parts[2]) or ([t for t in projects.values() if t.get("id") == parts[2]] or [None])[0]
            if thing is None:
                return 404, b"{}"
            doc = {"id": thing["id"], "accountId": thing["account"], "name": thing["name"], "paused": thing["state"] == "paused"}
            if thing.get("repo"):
                doc["link"] = {"type": "github", "repo": thing["repo"]}
            return 200, json.dumps(doc).encode()
        if parts[:2] == ["v1", "projects"] and len(parts) == 4 and method == "POST":
            # a thing of another kind (the database resource `db-add` records, with no id) is no project (the join's sequence
            # holds both on one host)
            found = [t for t in projects.values() if t.get("kind") == "project" and t.get("id") == parts[2]]
            if not found:
                return 404, b"{}"
            found[0]["state"] = "paused" if parts[3] == "pause" else "active"
            state.setdefault("sets", []).append({"name": found[0]["name"], "state": found[0]["state"]})
            save("vercel", state, home)
            return 200, b"{}"
        if parts[:2] == ["v13", "deployments"] and len(parts) == 3:
            slug = parts[2][: -len(".vercel.app")] if parts[2].endswith(".vercel.app") else None
            thing = projects.get(slug)
            if thing is None:
                return 404, b"{}"
            head = None
            try:
                with open(os.path.join(root("gh", home), "state.json")) as fh:
                    account = json.load(fh).get("account", "fixture-account")
                head = remote_ref(account, thing.get("repo") or "", "refs/heads/main", home)
            except (OSError, ValueError):
                pass
            doc = {"readyState": (state.get("deployments") or {}).get(slug, {}).get("readyState", "READY")}
            if head:
                doc["gitSource"] = {"sha": head}
            return 200, json.dumps(doc).encode()
        if parts[:2] == ["v9", "projects"] and parts[3:] == ["custom-environments"]:
            if parts[2] not in projects:
                return 404, b"{}"
            return 200, json.dumps({"environments": (state.get("custom") or {}).get(parts[2], [])}).encode()
        if parts[:2] == ["v10", "projects"] and parts[3:] == ["env"]:
            if parts[2] not in projects:
                return 404, b"{}"
            envs = (state.get("envs") or {}).get(parts[2], [])
            if "customEnvironmentId" in query:
                listed = []
                for item in envs:
                    if item.get("custom") != query["customEnvironmentId"]:
                        continue
                    member = {"key": item["key"], "type": item.get("type", "encrypted")}
                    if item.get("type") != "sensitive" and query.get("decrypt") == "true":
                        member["value"] = item["value"]
                    listed.append(member)
                return 200, json.dumps({"envs": listed, "pagination": {"count": len(listed), "next": state.get("next")}}).encode()
            listed = [{"key": i["key"], "type": i.get("type", "encrypted"), "target": i.get("target", [])} for i in envs
                      if not i.get("custom")]
            doc = {"envs": listed, "pagination": {"count": len(listed), "next": state.get("next")}}
            if "hidden" in state:
                doc["hiddenProductionEnvCount"] = state["hidden"]
            return 200, json.dumps(doc).encode()
        return 404, b"{}"


# ---- postgres --------------------------------------------------------------------------------------------------------
def service():
    """The one section of the private service file `PGSERVICEFILE` names, by `PGSERVICE`: {key: value}."""
    path, name = os.environ.get("PGSERVICEFILE", ""), os.environ.get("PGSERVICE", "")
    out, inside = {}, False
    try:
        with open(path) as fh:
            for line in fh.read().split("\n"):
                if line.startswith("["):
                    inside = line == "[%s]" % name
                elif inside and "=" in line:
                    key, _, value = line.partition("=")
                    out[key] = value
    except OSError:
        return None
    return out


# How the fake's pg_dump writes a plain dump where the state names no `ending`: as the real tool does since 17.6 (part J3b).
DUMP_ENDING = "unrestrict"
RESTRICT_KEY = "FixtureRestrictKey1"       # letters and digits, pg_dump's alphabet; synthetic, its length a test's choice


def postgres(tool, args):
    state = load("pg")
    section = service()
    note("pg", {"command": tool, "argv": args, "env_names": sorted(os.environ),
                "service_mode": oct(os.stat(os.environ["PGSERVICEFILE"]).st_mode & 0o777) if os.environ.get("PGSERVICEFILE") and
                os.path.exists(os.environ["PGSERVICEFILE"]) else None,
                "service_keys": sorted(section) if section else None})
    todo = planned("pg", tool)
    as_planned(todo)
    if not section or section.get("password") != state.get("password"):
        sys.stderr.write("fe_sendauth: no password supplied\n")
        answer(None, 2 if tool == "psql" else 1)
    tables = state.get("tables") or {}
    unreadable = [t for t in state.get("unreadable") or [] if t in tables]
    if tool == "psql":
        answer({"identity": state.get("identity", "7000000000000000001"), "tables": len(tables), "unreadable": len(unreadable)})
    if unreadable:
        sys.stderr.write("pg_dump: error: permission denied for table\n")
        answer(None, 1)
    out = args[args.index("-f") + 1]
    ending = state.get("ending") or DUMP_ENDING
    key = state.get("restrict_key") or RESTRICT_KEY
    restrict = ending in ("unrestrict", "unrestrict-1")
    lines = ["--", "-- PostgreSQL database dump", "--", ""] + (["\\restrict " + key, ""] if restrict else [])
    for name in sorted(tables):
        lines += ["CREATE TABLE public.%s (" % name, "    v text", ");", ""]
    for name in sorted(tables):
        if name == todo.get("drop"):
            continue                    # a plan's `drop`: this table's data section left out of the copy
        lines += ["COPY public.%s (v) FROM stdin;" % name] + list(tables[name]) + ["\\.", ""]
    lines += ["--", "-- PostgreSQL database dump complete", "--", "", ""]
    if restrict:
        lines[-1:] = ["\\unrestrict " + key] + (["", ""] if ending == "unrestrict" else [""])
    text = "\n".join(lines) + todo.get("tail", "")
    if todo.get("do") == "short":
        text = text[: len(text) // 2]
    with open(out, "w") as fh:
        fh.write(text)
    answer(None, 0)


# ---- curl ------------------------------------------------------------------------------------------------------------
def curl(args):
    state = load("vercel")
    url = args[-1]
    note("web", {"command": "status", "argv": args, "env_names": sorted(os.environ)})
    todo = planned("web", "status")
    as_planned(todo)
    host = urllib.parse.urlsplit(url).hostname or ""
    slug = host[: -len(".vercel.app")] if host.endswith(".vercel.app") else None
    thing = (state.get("things") or {}).get(slug)
    ready = (state.get("deployments") or {}).get(slug, {}).get("readyState") == "READY"
    code = "200" if thing and thing.get("state") == "active" and ready else "404"
    answer(args[args.index("-w") + 1].replace("%{http_code}", code))


def main():
    tool, args = sys.argv[1], sys.argv[2:]
    if tool == "gh":
        gh(args)
    if tool == "vercel":
        vercel(args)
    if tool in ("psql", "pg_dump"):
        postgres(tool, args)
    if tool == "curl":
        curl(args)
    answer(None, 2)


if __name__ == "__main__":
    main()
