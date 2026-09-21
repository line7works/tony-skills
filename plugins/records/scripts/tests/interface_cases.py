"""Every response shape this CLI can produce, driven through the CLI itself.

Slice 3's coverage test (`test_interface.py`) reads this and `references/interface.md` and holds
the two in step: every field the code returns is documented, and every field the document names
is returned by some case here. The same list is what a reader of `interface.md` is promised.

Nothing here asserts on behaviour. It builds fixtures under a temporary directory, runs
`records.py`, and hands back `[{case, command, argv, exit, body, stderr}]`. Every case is a real
run: no response is hand-written, so a field that quietly appears in the code appears here too.

`field_paths` turns one response into dotted paths: `spec.doc`, `findings[].id`,
`slices[].open.BLOCKER`. A node the document marks `X.*` (a map whose keys are data, or a whole
event described by `event.schema.json`) is recorded as `X` and `X.*` and not descended into, so
the document decides where description stops rather than the walk.
"""
import copy
import json
import os
import shutil

import testlib

testlib.add_scripts_to_path()

from records_core import canon, events as events_mod, identity as identity_mod  # noqa: E402

DOC = testlib.DOC
FIXTURE_DOC = "docs/plans/2026-05-12-history.md"
AMBIGUOUS_DOC = "docs/plans/2026-05-03-join-ambiguous-shared.md"
MIRRORS_DOC = "docs/plans/2026-05-14-mirrors.md"
OTHER_COMMIT = "1f0c9b7a4d2e6f80315c8ab4d9e2071c6b35a8f4"
CHANGED_FROM = "the loading list is not sorted · a heavy crate"
CHANGED_TO = "the loading list is not sorted at all · a heavy crate"


def _run(cases, name, command, argv, expect=None):
    code, body, err = testlib.run_json(argv)
    cases.append({"case": name, "command": command, "argv": argv, "exit": code,
                  "body": body, "stderr": err})
    if expect is not None and code != expect:
        raise AssertionError("case %s: exit %s, expected %s (%s %s)" % (name, code, expect, body, err))
    return body


def _batch(parent, events, name):
    return testlib.events_file(parent, events, name=name)


def native_cases(scratch, cases):
    """The commands a station drives on a native log: verify, events, identity, append, state,
    render, component-identity, and the refusals each of them can answer with."""
    workspace = testlib.make_workspace(scratch, doc=DOC)
    batches = os.path.join(scratch, "batches")
    os.makedirs(batches)
    identity = identity_mod.source_identity(workspace)
    ws = ["--workspace", workspace, "--doc", DOC]

    _run(cases, "verify-a-log-that-does-not-exist", "verify", ["verify"] + ws, 0)
    _run(cases, "component-identity", "component-identity", ["component-identity"], 0)
    _run(cases, "identity", "identity", ["identity", "--workspace", workspace], 0)

    first = _batch(batches, [testlib.opened(identity), testlib.raised(identity=identity)], "open.json")
    head = _run(cases, "append-a-batch", "append",
                ["append"] + ws + ["--events", first, "--expect-head", testlib.ZERO], 0)["head"]
    finding = _run(cases, "events-of-one-kind", "events",
                   ["events"] + ws + ["--kind", "finding_raised"], 0)["results"][0]["event"]["finding"]

    _run(cases, "verify-a-log-that-exists", "verify", ["verify"] + ws, 0)
    _run(cases, "events-every-filter", "events",
         ["events"] + ws + ["--finding", finding, "--kind", "finding_raised", "--from", "0"], 0)

    head = _run(cases, "append-a-clear", "append",
                ["append"] + ws + ["--events", _batch(batches, [testlib.disposition(finding, identity)],
                                                      "clear.json"),
                                   "--expect-head", head], 0)["head"]

    _run(cases, "state", "state", ["state"] + ws, 0)
    _run(cases, "state-of-one-slice", "state", ["state"] + ws + ["--slice", "A"], 0)
    at_source = testlib.write_json(os.path.join(scratch, "identity.json"), identity)
    _run(cases, "state-at-a-source", "state", ["state"] + ws + ["--at-source", at_source], 0)
    _run(cases, "render", "render", ["render"] + ws + ["--run-id", testlib.STATION["run_id"]], 0)
    _run(cases, "render-a-run-with-nothing-in-it", "render",
         ["render"] + ws + ["--run-id", "no-such-run"], 0)

    # the refusals
    _run(cases, "append-a-wrong-head", "append",
         ["append"] + ws + ["--events", first, "--expect-head", "a" * 64], 7)
    seq_carried = dict(testlib.raised(claim="another claim", identity=identity), seq=9)
    _run(cases, "append-an-event-the-schema-refuses", "append",
         ["append"] + ws + ["--events", _batch(batches, [seq_carried], "seq.json"),
                            "--expect-head", head], 4)
    unknown = testlib.disposition("f1:0123456789abcdef0123", identity)
    _run(cases, "append-naming-a-finding-the-log-does-not-hold", "append",
         ["append"] + ws + ["--events", _batch(batches, [unknown], "unknown.json"),
                            "--expect-head", head], 5)
    _run(cases, "append-a-second-raise-of-one-identity", "append",
         ["append"] + ws + ["--events", _batch(batches, [testlib.raised(identity=identity)], "again.json"),
                            "--expect-head", head], 5)
    second = testlib.raised(claim="the second finding", identity=identity, at="2026-04-01T09:00:02Z")
    head = _run(cases, "append-a-second-finding", "append",
                ["append"] + ws + ["--events", _batch(batches, [second], "second.json"),
                                   "--expect-head", head], 0)["head"]
    second_id = _run(cases, "events-from-a-seq", "events", ["events"] + ws + ["--from", "3"],
                     0)["results"][0]["event"]["finding"]
    stale = copy.deepcopy(identity)
    stale["commit"] = OTHER_COMMIT
    _run(cases, "append-a-clear-against-another-revision", "append",
         ["append"] + ws + ["--events", _batch(batches, [testlib.disposition(second_id, stale)], "stale.json"),
                            "--expect-head", head], 6)
    legacy = testlib.native("finding_raised", slice="A", severity="MINOR",
                            location=testlib.location("src/widget.py:5", "src/widget.py", 5),
                            claim="a legacy claim", scenario="it broke", raised_by="A")
    legacy["origin"] = testlib.legacy_origin()
    _run(cases, "append-a-legacy-record-from-a-station", "append",
         ["append"] + ws + ["--events", _batch(batches, [legacy], "legacy.json"),
                            "--expect-head", head], 4)

    lock = events_mod.lock_path(events_mod.log_path(workspace, DOC))
    testlib.write(lock, json.dumps({"pid": os.getpid(), "pid_start": "not this process",
                                    "command": "append"}) + "\n")
    try:
        _run(cases, "append-while-the-lock-is-held", "append",
             ["append"] + ws + ["--events", first, "--expect-head", head], 7)
        testlib.write(lock, "this lock file is not JSON\n")
        _run(cases, "append-while-a-lock-nobody-can-read-is-there", "append",
             ["append"] + ws + ["--events", first, "--expect-head", head], 7)
        # A pid that is not running, rather than this one under another start time: telling a
        # recycled pid from a live one needs `ps`, and a sandbox that denies `ps` would then
        # turn this response corpus into a module setup error rather than one skipped test.
        # `test_append.Locks` covers the recycled-pid rule itself, and skips when `ps` is denied.
        testlib.write(lock, json.dumps({"pid": 999999, "pid_start": "Wed Apr  1 09:00:00 2026",
                                        "command": "append"}) + "\n")
        after_break = testlib.raised(claim="after the break", identity=identity,
                                     at="2026-04-01T09:00:03Z")
        broke = _run(cases, "append-breaking-a-stale-lock", "append",
                     ["append"] + ws + ["--events", _batch(batches, [after_break], "broke.json"),
                                        "--expect-head", head, "--break-lock"], 0)
        # Send-back 1: a lock file nobody can read is broken the same way, and `broke_lock` then
        # carries `unreadable` with a null pid and no command. Without this case the corpus never
        # returns `broke_lock.unreadable`, and interface.md would name a field no run produces.
        testlib.write(lock, "this lock file is not JSON either\n")
        after_unreadable = testlib.raised(claim="after the unreadable lock", identity=identity,
                                          at="2026-04-01T09:00:04Z")
        _run(cases, "append-breaking-a-lock-nobody-can-read", "append",
             ["append"] + ws + ["--events",
                                _batch(batches, [after_unreadable], "broke-unreadable.json"),
                                "--expect-head", broke["head"], "--break-lock"], 0)
    finally:
        if os.path.isfile(lock):
            os.unlink(lock)

    # a workspace `identity` refuses: not a work tree (exit 2), and one with a submodule (exit 1)
    plain = os.path.join(scratch, "not-a-work-tree")
    os.makedirs(plain)
    _run(cases, "identity-of-a-directory-that-is-not-a-work-tree", "identity",
         ["identity", "--workspace", plain], 2)
    _run(cases, "identity-of-a-workspace-holding-a-submodule", "identity",
         ["identity", "--workspace", _with_submodule(scratch)], 1)

    # a log `append` could not have written: a clear naming a finding nothing raised. A merge can
    # leave one, and `render` has to say so rather than guess.
    unrendered = os.path.join(scratch, "unrendered")
    os.makedirs(unrendered)
    _handwritten_log(unrendered, DOC, [
        testlib.opened(identity),
        dict(testlib.disposition("f1:0123456789abcdef0123", identity), **{
            "actor": {"station": "signoff", "run_id": "a-run", "harness": "claude-code"}}),
    ])
    _run(cases, "render-a-run-naming-a-finding-the-log-never-raised", "render",
         ["render", "--workspace", unrendered, "--doc", DOC, "--run-id", "a-run"], 4)

    # a log the chain walk refuses, and one the schema refuses, in copies of the workspace
    broken = _corrupt(scratch, workspace, "chain",
                      lambda lines: lines[:1] + [lines[1].replace(b'"seq":1', b'"seq":7')] + lines[2:])
    _run(cases, "verify-a-broken-chain", "verify", ["verify", "--workspace", broken, "--doc", DOC], 7)
    unparsable = _corrupt(scratch, workspace, "line",
                          lambda lines: lines[:1] + [b"{not json"] + lines[2:])
    _run(cases, "verify-a-line-that-does-not-parse", "verify",
         ["verify", "--workspace", unparsable, "--doc", DOC], 4)

    def _rewrite(index, **fields):
        def change(lines):
            event = json.loads(lines[index].decode("utf-8"))
            event.update(fields)
            return lines[:index] + [canon.canonical_json(event)] + lines[index + 1:]
        return change

    # a chain break at `prev` rather than at `seq`, and a line naming another document
    # (amendment A8), so that every field those two refusals carry is exercised
    bad_prev = _corrupt(scratch, workspace, "prev", _rewrite(1, prev="f" * 64))
    _run(cases, "verify-a-line-whose-prev-is-wrong", "verify",
         ["verify", "--workspace", bad_prev, "--doc", DOC], 7)
    foreign = _corrupt(scratch, workspace, "ledger-doc",
                       _rewrite(1, ledger_doc="docs/plans/another.md"))
    _run(cases, "verify-a-line-naming-another-document", "verify",
         ["verify", "--workspace", foreign, "--doc", DOC], 7)

    # usage errors: no JSON body at all, one line on stderr
    _run(cases, "a-doc-outside-the-workspace", "verify",
         ["verify", "--workspace", workspace, "--doc", "../elsewhere.md"], 2)
    _run(cases, "an-events-file-that-is-not-there", "append",
         ["append"] + ws + ["--events", os.path.join(scratch, "no-such-batch.json"),
                            "--expect-head", testlib.ZERO], 2)
    return workspace


def _with_submodule(scratch):
    """A workspace holding one initialized submodule: the identity the pilot refuses (exit 1).

    Both repositories are throwaway, built here under a temporary directory; the submodule is
    added over a local path with `protocol.file.allow`, so nothing reaches the network.
    """
    inner = os.path.join(scratch, "inner-repo")
    os.makedirs(inner)
    testlib.write(os.path.join(inner, "README.md"), "# inner\n")
    testlib.git(inner, "init", "-q", ".")
    testlib.git(inner, "add", "-A")
    testlib.git(inner, "commit", "-qm", "the inner repository")
    outer = testlib.make_workspace(os.path.join(scratch, "with-submodule"), doc=DOC)
    testlib.git(outer, "-c", "protocol.file.allow=always", "submodule", "add", "-q", inner, "vendor")
    testlib.git(outer, "add", "-A")
    testlib.git(outer, "commit", "-qm", "vendor the inner repository")
    return outer


def _handwritten_log(workspace, doc, events):
    """Write a valid, chained log directly, without `append`.

    `append` refuses a clear naming a finding the log never raised (section 7), so the only way
    to reach `render`'s refusal is a log written some other way: a git merge that joined two
    tails is the real case.
    """
    testlib.add_scripts_to_path()
    from records_core import canon
    path = events_mod.log_path(workspace, doc)
    os.makedirs(os.path.dirname(path))
    prev = events_mod.ZERO_HEAD
    out = []
    for seq, event in enumerate(events):
        line = canon.canonical_json(dict(event, seq=seq, prev=prev))
        out.append(line + b"\n")
        prev = events_mod.line_hash(line)
    with open(path, "wb") as fh:
        fh.write(b"".join(out))
    return path


def _corrupt(scratch, workspace, name, change):
    """A copy of a workspace whose log has been damaged; returns the copy's path."""
    target = os.path.join(scratch, "corrupt-" + name)
    shutil.copytree(workspace, target)
    path = events_mod.log_path(target, DOC)
    with open(path, "rb") as fh:
        lines = fh.read().split(b"\n")[:-1]
    with open(path, "wb") as fh:
        fh.write(b"".join(line + b"\n" for line in change(lines)))
    return target


def legacy_cases(scratch, cases):
    """The commands section 11 adds: import-legacy (dry, landed, refused), mirrors, survey."""
    workspace = testlib.fixture_workspace(scratch)
    ws = ["--workspace", workspace, "--doc", FIXTURE_DOC]
    _run(cases, "survey", "survey", ["survey", "--workspace", workspace], 0)
    _run(cases, "mirrors", "mirrors", ["mirrors", "--workspace", workspace, "--doc", MIRRORS_DOC], 0)
    _run(cases, "import-legacy-dry-run", "import-legacy", ["import-legacy"] + ws + ["--dry-run"], 0)
    landed = _run(cases, "import-legacy", "import-legacy", ["import-legacy"] + ws, 0)
    _run(cases, "import-legacy-a-second-time", "import-legacy", ["import-legacy"] + ws, 0)
    _run(cases, "state-of-an-imported-log", "state", ["state"] + ws, 0)
    _run(cases, "render-an-import-run", "render", ["render"] + ws + ["--run-id", landed["run_id"]], 0)
    _run(cases, "events-of-an-imported-log", "events", ["events"] + ws, 0)

    ambiguous = ["--workspace", workspace, "--doc", AMBIGUOUS_DOC]
    _run(cases, "import-legacy-stopped-by-an-ambiguous-line", "import-legacy",
         ["import-legacy"] + ambiguous, 5)
    answers = testlib.write_json(os.path.join(scratch, "answers.json"), {
        "answered_by": "the owner", "answered_on": "2026-05-20",
        "answers": [{"line": 4096, "raw": "a line this document does not hold", "skip": True,
                     "why": "it was never asked"}]})
    _run(cases, "import-legacy-with-a-rejected-resolution", "import-legacy",
         ["import-legacy"] + ambiguous + ["--resolutions", answers], 4)
    malformed = testlib.write_json(os.path.join(scratch, "malformed.json"), {"answers": []})
    _run(cases, "import-legacy-with-a-resolutions-file-the-schema-refuses", "import-legacy",
         ["import-legacy"] + ambiguous + ["--resolutions", malformed], 4)

    # section 11.5: one ambiguous line takes one answer. Two answers for it are refused before
    # the pass plans anything, so this is its own response shape (verification item N1).
    stop = _run(cases, "import-legacy-stopped-again-for-its-question", "import-legacy",
                ["import-legacy"] + ambiguous + ["--dry-run"], 5)["ambiguities"][0]
    twice = testlib.write_json(os.path.join(scratch, "twice.json"), {
        "answered_by": "the owner", "answered_on": "2026-05-20", "doc": AMBIGUOUS_DOC,
        "answers": [{"line": stop["line"], "raw": stop["raw"], "finding": candidate["finding"]}
                    for candidate in stop["candidates"][:2]]})
    _run(cases, "import-legacy-with-two-answers-for-one-line", "import-legacy",
         ["import-legacy"] + ambiguous + ["--resolutions", twice], 4)

    # a document whose imported lines changed, and one that grew above its imported tail:
    # section 11.7's two exit-7 refusals
    path = os.path.join(workspace, *FIXTURE_DOC.split("/"))
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if CHANGED_FROM not in text:
        raise AssertionError("the history fixture no longer holds the line this case changes")
    testlib.write(path, text.replace(CHANGED_FROM, CHANGED_TO, 1))
    _run(cases, "import-legacy-after-an-imported-line-changed", "import-legacy",
         ["import-legacy"] + ws, 7)

    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith("### 2026-05-13"):
            if lines[index - 1] != "":
                raise AssertionError("the history fixture's shape moved")
            lines[index - 1] = ("- MINOR · src/list.py:9 · the list header is not printed · "
                                "a loader guesses · Slice A review")
            break
    else:
        raise AssertionError("no recheck heading in the history fixture")
    testlib.write(path, "\n".join(lines))
    _run(cases, "import-legacy-after-a-record-appeared-above-the-tail", "import-legacy",
         ["import-legacy"] + ws, 7)
    testlib.write(path, text)

    lock = events_mod.lock_path(events_mod.log_path(workspace, FIXTURE_DOC))
    testlib.write(lock, json.dumps({"pid": os.getpid(), "pid_start": "not this process",
                                    "command": "import-legacy"}) + "\n")
    try:
        _run(cases, "import-legacy-while-the-lock-is-held", "import-legacy",
             ["import-legacy"] + ws, 7)
    finally:
        if os.path.isfile(lock):
            os.unlink(lock)
    return workspace


def dependency_cases(scratch, cases):
    """With jsonschema unimportable: exit 3 and one line on stderr for every command that
    validates something, and a normal answer from `component-identity`, which validates nothing
    and is what a station runs to confirm the root it picked (section 12.1, amendment A6)."""
    stub = testlib.stub_without_jsonschema(os.path.join(scratch, "nodep"))
    workspace = testlib.make_workspace(os.path.join(scratch, "nodep-ws"), doc=DOC)
    argv = {
        "verify": ["verify", "--workspace", workspace, "--doc", DOC],
        "events": ["events", "--workspace", workspace, "--doc", DOC],
        "identity": ["identity", "--workspace", workspace],
        "append": ["append", "--workspace", workspace, "--doc", DOC, "--events",
                   testlib.events_file(scratch, [testlib.opened()], "dep.json"),
                   "--expect-head", testlib.ZERO],
        "component-identity": ["component-identity"],
        "state": ["state", "--workspace", workspace, "--doc", DOC],
        "render": ["render", "--workspace", workspace, "--doc", DOC, "--run-id", "r"],
        "import-legacy": ["import-legacy", "--workspace", workspace, "--doc", DOC, "--dry-run"],
        "mirrors": ["mirrors", "--workspace", workspace, "--doc", DOC],
        "survey": ["survey", "--workspace", workspace],
    }
    for command in sorted(argv):
        code, out, err = testlib.run_cli(argv[command], env={"PYTHONPATH": stub})
        cases.append({"case": "without-jsonschema-" + command, "command": command,
                      "argv": argv[command], "exit": code,
                      "body": json.loads(out) if out.strip() else None, "stderr": err})
    return workspace


def every_case(scratch):
    """Every response this CLI can produce, in one list. The caller owns `scratch`."""
    cases = []
    native_cases(os.path.join(scratch, "native"), cases)
    legacy_cases(os.path.join(scratch, "legacy"), cases)
    dependency_cases(os.path.join(scratch, "dep"), cases)
    return cases


def field_paths(value, stops, prefix=""):
    """The dotted field paths of one response body; `stops` holds the `X.*` the document marks."""
    out = set()
    if isinstance(value, dict):
        if prefix and (prefix + ".*") in stops:
            out.add(prefix + ".*")
            return out
        for key in sorted(value):
            path = "%s.%s" % (prefix, key) if prefix else key
            out.add(path)
            out |= field_paths(value[key], stops, path)
    elif isinstance(value, list):
        path = prefix + "[]"
        if value:
            out.add(path)
        for item in value:
            if isinstance(item, (dict, list)):
                out |= field_paths(item, stops, path)
    return out


def documented_stops(text):
    """The `X.*` entries a document names, so the walk knows where description stops."""
    import re
    return set(m.group(1) for m in re.finditer(r"`([A-Za-z0-9_\[\]. ]+\.\*)`", text))
