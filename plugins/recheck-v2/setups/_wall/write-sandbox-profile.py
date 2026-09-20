#!/usr/bin/env python3
"""The wall: one OS-level sandbox profile per harness launch (sealed bench, A1).

Reads a JSON spec — read roots, read files, write roots, refused roots, the loopback proxy
port — and writes the SBPL text `/usr/bin/sandbox-exec -f` takes, plus a JSON summary on
stdout. One writer for every setup: the runner builds the spec, this file turns it into a
profile, and the profile is retained in the trial record and hashed into `command.json`.

usage: write-sandbox-profile.py --out PROFILE [--spec SPEC.json]      (else the spec on stdin)
Python 3.9, standard library only. No model, no network, no subprocess.

Measured on this Mac (macOS 26.6.2, 2026-09-19) and the reason the shape is what it is:

- In SBPL the LAST matching rule wins. So the broad denials come first and the narrow allows
  after them, and a refused root that sits UNDER an allowed root is denied again at the end.
  A refused root that is an ANCESTOR of an allowed root cannot be re-denied at the end (it
  would close the allowed root with it), so it is emitted in the leading deny block instead,
  where the narrower allow legitimately reopens only the named subtree. Either way the final
  text refuses the refused root itself, which `check_profile` proves by evaluating the rules.
- `(deny file-read* ...)` does NOT stop a binary under the denied subtree from being EXECUTED:
  exec is `process-exec*`, a different operation. Measured: `uv --version` runs from
  `~/.local/bin` under a profile that denies every read of `/Users`, while `cat` on the same
  binary is refused. A harness whose executable READS its own files (a node bundle) still
  needs that install location as a read root; a static binary does not.
- `file-read-metadata` must be allowed on every ancestor of every allowed root or path
  resolution fails before it reaches the root: a shell whose cwd is inside an allowed write
  root printed `getcwd: cannot access parent directories: Operation not permitted` until the
  whole ancestor chain was allowed.
- A path is emitted in BOTH its given and its resolved form (`/tmp` is `/private/tmp`, `/var`
  is `/private/var`), because a profile matches the path the kernel resolves and a caller
  names the path a person typed.
- One FILE can be reopened inside a denied subtree without reopening its siblings: `(literal
  "<path>")` matches that path alone, where `(subpath "<dir>")` matches a whole tree. Emitted
  after the deny, it is what lets the two conditions of one setup share a single credential
  store while the rest of the other condition's home stays refused (send-back 8). `write_files`
  is that allow, read and write; `read_files` is its read-only twin.
- A second `sandbox-exec` inside the first fails (`sandbox_apply: Operation not permitted`,
  exit 71), so nothing under the wall may try to sandbox itself again.
"""
import argparse
import json
import os
import sys

# The device nodes a plain process needs to run at all. Writes are denied everywhere by
# default, and these are the exceptions every harness needs; a setup that needs more names
# them in its own `wall-needs.json`, with a reason per entry.
DEFAULT_DEVICE_NODES = (
    "/dev/null", "/dev/zero", "/dev/random", "/dev/urandom", "/dev/tty",
    "/dev/dtracehelper", "/dev/fd", "/dev/stdin", "/dev/stdout", "/dev/stderr",
    "/dev/ptmx",
)
# The user-area roots the wall closes. Everything a launch may still touch is named back in
# by the spec, and nothing else is reachable.
BROAD_DENY = ("/Users", "/private/tmp", "/tmp", "/private/var/tmp", "/Volumes")

# The two wildcard operation names, exactly as SBPL spells them. `file-write*` covers the
# mode, owner, times and flags operations as well as the data ones, so a narrower list would
# leave `chmod` and `utimes` allowed everywhere by `(allow default)`.
READ_OPS = ("file-read*",)
WRITE_OPS = ("file-write*",)
# The concrete operations the check evaluates the rules against.
CHECKED_READ = ("file-read-data", "file-read-metadata")
CHECKED_WRITE = ("file-write-data", "file-write-create", "file-write-unlink",
                 "file-write-mode", "file-write-times")


class SpecError(ValueError):
    """The spec cannot be turned into a profile that keeps its own promises."""


def escape(text):
    """An SBPL string literal's contents: backslash and quote are the two escapes."""
    return text.replace("\\", "\\\\").replace("\"", "\\\"")


def both_forms(path):
    """The path as given and as the kernel resolves it, in order, without duplicates."""
    given = os.path.abspath(path)
    resolved = os.path.realpath(given)
    return [given] if given == resolved else [given, resolved]


def ancestors(path):
    """Every directory above `path`, `/` included."""
    out, current = [], os.path.abspath(path)
    while True:
        parent = os.path.dirname(current)
        if parent == current:
            out.append(parent)
            break
        out.append(parent)
        current = parent
    return out


def entries(spec, key):
    """`[{path, why}]` from a list of strings or of objects, with the reason kept."""
    rows = []
    for item in spec.get(key) or []:
        if isinstance(item, str):
            path, why = item, ""
        elif isinstance(item, dict):
            path, why = item.get("path"), item.get("why") or ""
        else:
            raise SpecError("%s carries %r, which is neither a path nor {path, why}"
                            % (key, item))
        if not isinstance(path, str) or not path.startswith("/"):
            raise SpecError("%s carries %r; every path must be absolute" % (key, path))
        for form in both_forms(path):
            rows.append({"given": path, "path": form, "why": why})
    out, seen = [], set()
    for row in rows:
        if row["path"] in seen:
            continue
        seen.add(row["path"])
        out.append(row)
    return out


def under(path, root):
    """Is `path` the same as `root` or inside it?"""
    root = root.rstrip("/") or "/"
    if path == root:
        return True
    return path.startswith(root + "/") if root != "/" else path != "/"


# --------------------------------------------------------------------------- the rule model
#
# One dictionary per emitted rule, in emission order, so the text and the check read the same
# list. `check_profile` evaluates a path against it with last-match-wins, which is what the
# kernel does.


def rule(effect, ops, filters, note=None):
    return {"effect": effect, "ops": list(ops), "filters": list(filters), "note": note}


def matches(filters, path):
    for kind, value in filters:
        if kind == "subpath" and under(path, value):
            return True
        if kind == "literal" and path == value:
            return True
    return False


def op_matches(rule_op, operation):
    """Does an emitted operation name cover a concrete one? `file-read*` covers every
    `file-read-...`, and `default` covers everything."""
    if rule_op == "default":
        return True
    if rule_op.endswith("*"):
        return operation.startswith(rule_op[:-1])
    return rule_op == operation


def evaluate(rules, path, operation):
    """`allow` or `deny` for one path and one operation, last matching rule wins."""
    verdict = "allow"          # `(allow default)` is the first rule of every profile
    for row in rules:
        if row["ops"] and not any(op_matches(o, operation) for o in row["ops"]):
            continue
        if row["filters"] and not matches(row["filters"], path):
            continue
        verdict = row["effect"]
    return verdict


def build_rules(spec):
    """Every rule of the profile, in order, and the summary the caller records."""
    read_roots = entries(spec, "read_roots")
    read_files = entries(spec, "read_files")
    write_roots = entries(spec, "write_roots")
    # send-back 8: ONE named file, readable AND writable, and nothing else in the directory it
    # sits in. The Codex install keeps one credential store and links every derived home's
    # `auth.json` to it, so the `absent` condition reaches its credential through a link into a
    # root this profile refuses. A subpath allow would reopen the whole of that other home; a
    # literal reopens exactly the one file, after the deny, where last-match-wins gives it to
    # the launch. Writable because Codex rewrites the store on a token refresh, and a store
    # readable in one condition and writable in the other would be a with/without difference.
    write_files = entries(spec, "write_files")
    refused = entries(spec, "refused_roots")
    devices = spec.get("device_nodes")
    devices = list(DEFAULT_DEVICE_NODES) if devices is None else list(devices)
    allowed_paths = [r["path"] for r in read_roots + read_files + write_roots + write_files]

    for row in refused:
        for allowed in allowed_paths:
            if row["path"] == allowed:
                raise SpecError(
                    "%s is named both as a refused root and as an allowed root; a profile "
                    "cannot do both" % row["path"])

    # A refused root that is an ANCESTOR of something the launch may reach goes in the
    # leading deny block, where a narrower allow reopens only the named subtree. Everything
    # else is re-denied after the allows, so no allow can reopen it.
    pre, post = [], []
    for row in refused:
        if any(under(allowed, row["path"]) for allowed in allowed_paths):
            pre.append(row)
        else:
            post.append(row)

    metadata = set()
    for path in allowed_paths:
        metadata.update(ancestors(path))
    # An ancestor that is itself inside an allowed root needs no separate rule.
    metadata = sorted(p for p in metadata
                      if not any(under(p, root["path"]) for root in read_roots + write_roots))

    rules = [rule("allow", ["default"], [], "(allow default)")]
    rules.append(rule("deny", list(WRITE_OPS), [],
                      "every write, everywhere, before anything is named back"))
    rules.append(rule("deny", list(READ_OPS) + list(WRITE_OPS),
                      [("subpath", p) for p in BROAD_DENY],
                      "the user area, the temporary roots and removable volumes"))
    if pre:
        rules.append(rule("deny", list(READ_OPS) + list(WRITE_OPS),
                          [("subpath", r["path"]) for r in pre],
                          "refused roots that contain something this launch may reach"))
    if metadata:
        rules.append(rule("allow", ["file-read-metadata"],
                          [("literal", p) for p in metadata],
                          "path resolution: every ancestor of every allowed root"))
    if read_roots:
        rules.append(rule("allow", list(READ_OPS),
                          [("subpath", r["path"]) for r in read_roots], "read roots"))
    if read_files:
        rules.append(rule("allow", list(READ_OPS),
                          [("literal", r["path"]) for r in read_files], "read files"))
    if write_roots:
        rules.append(rule("allow", list(READ_OPS) + list(WRITE_OPS),
                          [("subpath", r["path"]) for r in write_roots], "write roots"))
    if write_files:
        rules.append(rule("allow", list(READ_OPS) + list(WRITE_OPS),
                          [("literal", r["path"]) for r in write_files],
                          "write files: one named file each, never the directory it sits in"))
    if devices:
        rules.append(rule("allow", list(READ_OPS) + list(WRITE_OPS),
                          [("literal", p) for p in devices], "the device nodes a process needs"))
    if post:
        rules.append(rule("deny", list(READ_OPS) + list(WRITE_OPS),
                          [("subpath", r["path"]) for r in post],
                          "refused roots, denied after every allow"))
    return {"rules": rules, "read_roots": read_roots, "read_files": read_files,
            "write_roots": write_roots, "write_files": write_files,
            "refused_roots": refused, "devices": devices,
            "refused_before_the_allows": [r["path"] for r in pre],
            "refused_after_the_allows": [r["path"] for r in post],
            "metadata_ancestors": metadata}


def check_profile(built):
    """Every refused root is refused and every allowed root is allowed, by evaluation.

    A refused root that CONTAINS an allowed root keeps `file-read-metadata`: the ancestor
    chain of an allowed root has to stay stat-able or path resolution fails before it reaches
    the root. Metadata is not a listing (that is `file-read-data` on the directory) and not a
    read of any file, and the exception is recorded here rather than assumed.

    Send-back 8: the contents check runs on EVERY refused root, the ones that contain an
    allowed root included. `<root>/a-file-under-the-refused-root` is never a path any spec
    names, so it is a fair stand-in for the sibling of a reopened literal - the file the Codex
    credential fix must leave refused. It used to be skipped whenever the root contained
    anything allowed, which is exactly the case a one-file allow creates.
    """
    rules = built["rules"]
    allowed = (built["read_roots"] + built["read_files"] + built["write_roots"]
               + built["write_files"])
    problems = []
    for row in built["refused_roots"]:
        contains_an_allowed_root = any(under(a["path"], row["path"]) for a in allowed)
        checked = ("file-read-data",) + CHECKED_WRITE if contains_an_allowed_root \
            else CHECKED_READ + CHECKED_WRITE
        for operation in checked:
            if evaluate(rules, row["path"], operation) != "deny":
                problems.append("%s is not refused for %s" % (row["path"], operation))
        inside = os.path.join(row["path"], "a-file-under-the-refused-root")
        for operation in CHECKED_READ + CHECKED_WRITE:
            if evaluate(rules, inside, operation) != "deny":
                problems.append("%s is refused but its contents are not (%s)"
                                % (row["path"], operation))
    for row in built["read_roots"] + built["read_files"]:
        for operation in CHECKED_READ:
            if evaluate(rules, row["path"], operation) != "allow":
                problems.append("%s is named as readable and is not (%s)"
                                % (row["path"], operation))
    for row in built["write_roots"] + built["write_files"]:
        for operation in CHECKED_READ + CHECKED_WRITE:
            if evaluate(rules, row["path"], operation) != "allow":
                problems.append("%s is named as writable and is not (%s)"
                                % (row["path"], operation))
    return problems


def profile_text(spec, built):
    """The SBPL text."""
    port = spec.get("proxy_port")
    host = spec.get("proxy_host") or "localhost"
    lines = ["(version 1)",
             ";; the wall: one profile for one harness launch. Written by",
             ";; setups/_wall/write-sandbox-profile.py; the last matching rule wins.",
             "(allow default)"]
    for row in built["rules"][1:]:
        if row["note"]:
            lines.append(";; %s" % row["note"])
        ops = " ".join(row["ops"])
        if not row["filters"]:
            lines.append("(%s %s)" % (row["effect"], ops))
            continue
        filters = " ".join('(%s "%s")' % (kind, escape(value))
                           for kind, value in row["filters"])
        lines.append("(%s %s %s)" % (row["effect"], ops, filters))
    lines.append(";; no network but the loopback proxy the runner started outside the wall")
    lines.append("(deny network*)")
    if port:
        lines.append('(allow network-outbound (remote ip "%s:%d"))'
                     % (escape(str(host)), int(port)))
    for extra in spec.get("extra_network_allow") or []:
        lines.append('(allow network-outbound (remote ip "%s"))' % escape(str(extra)))
    return "\n".join(lines) + "\n"


def build(spec):
    """The profile text and its summary, or a SpecError."""
    built = build_rules(spec)
    problems = check_profile(built)
    if problems:
        raise SpecError("the profile would not keep its own promises: %s"
                        % "; ".join(problems))
    text = profile_text(spec, built)
    return text, {
        "label": spec.get("label"),
        "read_roots": built["read_roots"],
        "read_files": built["read_files"],
        "write_roots": built["write_roots"],
        "write_files": built["write_files"],
        "refused_roots": built["refused_roots"],
        "refused_before_the_allows": built["refused_before_the_allows"],
        "refused_after_the_allows": built["refused_after_the_allows"],
        "metadata_ancestors": built["metadata_ancestors"],
        "device_nodes": built["devices"],
        "broad_deny": list(BROAD_DENY),
        "proxy_port": spec.get("proxy_port"),
        "proxy_host": spec.get("proxy_host") or "localhost",
        "rules": len(built["rules"]),
        "bytes": len(text.encode("utf-8")),
        "checked": "every refused root evaluates to deny and every allowed root to allow, "
                   "by last-match-wins over the emitted rules",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", help="the spec JSON; stdin when absent")
    parser.add_argument("--out", required=True, help="where the SBPL text goes")
    args = parser.parse_args(argv)
    try:
        if args.spec:
            with open(args.spec, "r", encoding="utf-8") as handle:
                spec = json.load(handle)
        else:
            spec = json.load(sys.stdin)
    except (IOError, OSError, ValueError) as exc:
        sys.stderr.write("write-sandbox-profile.py: the spec does not read: %s\n" % exc)
        return 2
    try:
        text, summary = build(spec)
    except SpecError as exc:
        sys.stderr.write("write-sandbox-profile.py: %s\n" % exc)
        return 2
    directory = os.path.dirname(os.path.abspath(args.out))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(text)
    summary["profile"] = os.path.abspath(args.out)
    sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
