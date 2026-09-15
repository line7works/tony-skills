#!/usr/bin/env python3
"""The user channel for the OpenCode adapter (recheck-v2, E9 lane Q, ruling E9-32).

Reads the session store OpenCode 1.18.31 keeps at
``<XDG_DATA_HOME>/opencode/opencode.db`` (SQLite) and prints **this** session's turn list as
``turn_attribution``: a map from ``turn_ref`` to ``user``, ``assistant``, or ``station``.
The ``turn_ref`` shape for this harness is::

    opencode:session <session id>:message <message id>

Nothing here is composed by a model: every id, role and timestamp is read out of the record
the harness itself wrote. Only the ``session``, ``message`` and ``part`` tables are read; the
store's ``credential`` and ``account`` tables are never opened.

**Binding (ruling E9-32).** The session is located only through the harness's own record:
the pointer the setup's ``session-pointer.js`` plugin writes at the ``chat.message`` hook to
``${TMPDIR:-/tmp}/recheck-v2/opencode/<the opencode process id>.json``, read back through
``$OPENCODE_PID``, which the harness puts in every tool shell (measured on 1.18.31: the tool
shell is given ``OPENCODE=1`` and ``OPENCODE_PID`` and **no** session id of any kind). There
is no ``--session`` at run time and no newest-session fallback: a pointer that is absent,
unreadable, written by another process, or naming a session the store does not hold is exit 3
naming what is missing, never another session.

Arguments
---------
--find WORDS      print, under ``found``, the user turns whose own text contains WORDS
                  verbatim (substring, case sensitive). Assistant turns holding the same
                  words are never returned, and neither are harness-written parts.
--json            accepted and ignored: this helper always prints JSON on stdout (A7a).
--setup DIR       the isolated pilot setup (default: $RECHECK_OPENCODE_SETUP, else
                  ~/.local/share/skills-v2-pilot/opencode).
--raw             add each message's and part's raw record from the store under ``records``.
--help            this text.

Test-only arguments, accepted only with ``RECHECK_ADAPTER_TEST=1`` (the fixture interface of
ruling E9-32; at run time each is a usage error):

--session ID      use this session id instead of the bound one.
--workspace DIR   resolve the newest session whose ``directory`` is this one.
--db PATH         the session store file.

Which rows are turns of the conversation, and which are the harness's (ruling E9-22, read for
OpenCode): a ``message`` row maps only when its ``role`` is ``user`` or ``assistant``, its
``agent`` is not one of the harness's own internal agents (``compaction``, ``title``,
``summary``), the record is not marked ``synthetic``, and — for a ``user`` row — it carries at
least one text part that is itself not marked ``synthetic``. A ``user`` row that is tool-only,
synthetic, or otherwise harness-written stays out of the map, so ruling E9-1 rejects a grant
citing it as naming no turn of the session. Measured over the 26 sessions this setup's store
held on 2026-09-14: 26 ``user`` rows, every one a single non-synthetic text part, and no
``synthetic`` key anywhere in the store, so no harness-written user row was observed on
1.18.31; the rule is the trust boundary, not a convenience.

Example::

    python3 turns.py --find "waive the comma one, ship it"

prints ``{"harness": "opencode", "session_id": "ses_...", "resolved_by": "pointer",
"turn_attribution": {"opencode:session ses_...:message msg_...": "user", ...},
"found": ["opencode:session ses_...:message msg_..."], ...}``.

Exit status: 0 success; 2 a usage slip (a test-only argument at run time included); 3 a record
this helper needs is absent or unusable (``$OPENCODE_PID``, the pointer file, the session
store, the bound session, or a session record holding no attributable turn, ruling E9-29);
1 anything else. Side effects: none, the store is opened read-only.
"""

import json
import os
import sqlite3
import sys

HARNESS = "opencode"
DEFAULT_SETUP = os.path.join(
    os.path.expanduser("~"), ".local", "share", "skills-v2-pilot", "opencode"
)
# Agents the harness runs on its own behalf. A message carrying one of these is not a turn of
# the conversation and stays out of the map (E9-1: a reference absent from the map is
# rejected as naming no turn of the session).
INTERNAL_AGENTS = frozenset(["compaction", "title", "summary"])
TEST_ONLY = ("session", "workspace", "db")


class Usage(Exception):
    pass


class Missing(Exception):
    pass


def in_test():
    return os.environ.get("RECHECK_ADAPTER_TEST") == "1"


def turn_ref(session_id, message_id):
    return "opencode:session %s:message %s" % (session_id, message_id)


def store_path(setup, db=None):
    if db:
        if not in_test():
            raise Usage("--db is a test-only argument (RECHECK_ADAPTER_TEST=1)")
        return os.path.abspath(db)
    if setup:
        return os.path.join(os.path.abspath(setup), "xdg-data", "opencode", "opencode.db")
    env_setup = os.environ.get("RECHECK_OPENCODE_SETUP")
    if env_setup:
        return os.path.join(os.path.abspath(env_setup), "xdg-data", "opencode", "opencode.db")
    return os.path.join(DEFAULT_SETUP, "xdg-data", "opencode", "opencode.db")


def connect(path):
    if not os.path.isfile(path):
        raise Missing("session store not found at %s" % path)
    uri = "file:%s?mode=ro" % path.replace("?", "%3f").replace("#", "%23")
    try:
        con = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise Missing("session store unreadable at %s: %s" % (path, exc))
    con.row_factory = sqlite3.Row
    return con


def pointer_path(pid):
    return os.path.join(
        os.environ.get("TMPDIR", "/tmp"), "recheck-v2", "opencode", "%s.json" % pid
    )


def pointer_record():
    """The harness's own record of the session this shell belongs to, or a named failure.

    Keyed by the harness process: ``$OPENCODE_PID`` names the opencode process, and the
    plugin that wrote the file runs inside that same process. Nothing here falls back.
    """
    pid = os.environ.get("OPENCODE_PID")
    if not pid:
        raise Missing(
            "$OPENCODE_PID is not in this shell: this helper binds to the session through the "
            "harness's own pointer and runs only inside an OpenCode tool shell (ruling E9-32)"
        )
    path = pointer_path(pid)
    try:
        with open(path) as handle:
            record = json.load(handle)
    except (IOError, OSError) as exc:
        raise Missing(
            "no session pointer at %s for OPENCODE_PID %s (%s); the setup's "
            "session-pointer.js plugin writes it at chat.message" % (path, pid, exc.strerror)
        )
    except ValueError as exc:
        raise Missing("the session pointer at %s is not readable JSON: %s" % (path, exc))
    if not isinstance(record, dict) or not record.get("session_id"):
        raise Missing("the session pointer at %s names no session_id" % path)
    written_by = record.get("opencode_pid")
    if written_by is not None and str(written_by) != str(pid):
        raise Missing(
            "the session pointer at %s was written by process %s, not this shell's "
            "OPENCODE_PID %s: ambiguous binding, refusing to guess (ruling E9-32)"
            % (path, written_by, pid)
        )
    record["_path"] = path
    return record


def _session_row(con, session_id):
    return con.execute(
        "select id, directory from session where id = ?", (session_id,)
    ).fetchone()


def resolve_session(con, explicit=None, workspace=None):
    """(session id, directory, resolved_by, pointer record). Binds to this session only."""
    if explicit or workspace:
        if not in_test():
            raise Usage(
                "--session and --workspace are test-only arguments (RECHECK_ADAPTER_TEST=1); "
                "at run time the session is bound through the harness's own pointer (E9-32)"
            )
        if explicit:
            row = _session_row(con, explicit)
            if row is None:
                raise Missing("no session %s in the session store" % explicit)
            return row["id"], row["directory"], "explicit (test)", None
        target = os.path.realpath(workspace)
        rows = [
            r
            for r in con.execute("select id, directory, time_created from session")
            if r["directory"] and os.path.realpath(r["directory"]) == target
        ]
        if not rows:
            raise Missing("no session in the store ran in %s" % target)
        rows.sort(key=lambda r: r["time_created"], reverse=True)
        return rows[0]["id"], rows[0]["directory"], "newest-in-directory (test)", None
    pointer = pointer_record()
    row = _session_row(con, pointer["session_id"])
    if row is None:
        raise Missing(
            "the session pointer at %s names %s, which the session store does not hold; "
            "no fallback to another session (ruling E9-32)"
            % (pointer["_path"], pointer["session_id"])
        )
    return row["id"], row["directory"], "pointer", pointer


def part_rows(con, message_id):
    for row in con.execute(
        "select id, data, time_created from part where message_id = ? order by time_created",
        (message_id,),
    ):
        try:
            yield row["id"], json.loads(row["data"])
        except ValueError:
            yield row["id"], None


def message_text(con, message_id):
    """The message's own text, harness-written parts excluded (E9-22 / E9-32)."""
    chunks = []
    for _pid, data in part_rows(con, message_id):
        if not isinstance(data, dict):
            continue
        if data.get("synthetic") is True:
            continue
        if data.get("type") == "text" and isinstance(data.get("text"), str):
            chunks.append(data["text"])
    return "\n".join(chunks)


def part_census(con, message_id):
    """(types present, own text parts, synthetic text parts) for one message."""
    types = []
    own = 0
    synthetic = 0
    for _pid, data in part_rows(con, message_id):
        if not isinstance(data, dict):
            continue
        kind = data.get("type")
        types.append(kind)
        if kind == "text" and isinstance(data.get("text"), str):
            if data.get("synthetic") is True:
                synthetic += 1
            else:
                own += 1
    return types, own, synthetic


def why_unmapped(con, message_id, data):
    """The reason this row is not a turn of the conversation, or None when it is."""
    role = data.get("role")
    if role not in ("user", "assistant"):
        return "role is not user or assistant"
    if data.get("agent") in INTERNAL_AGENTS:
        return "written by the harness's own %s agent, not a turn" % data.get("agent")
    if data.get("synthetic") is True:
        return "the harness marked the record synthetic, so it is not the user's turn (E9-22)"
    if role == "user":
        types, own, synthetic = part_census(con, message_id)
        if own == 0:
            if synthetic:
                return (
                    "every text part of this user row is marked synthetic: the harness wrote "
                    "it, not the user (E9-22)"
                )
            return (
                "this user row carries no text part of its own (parts: %s): a tool result or "
                "another harness-written record, not the user's turn (E9-22)"
                % (",".join(sorted(set(t for t in types if t))) or "none")
            )
    return None


def collect(con, session_id, want_raw=False):
    turns = []
    unmapped = []
    attribution = {}
    records = []
    for row in con.execute(
        "select id, data, time_created from message where session_id = ? "
        "order by time_created, id",
        (session_id,),
    ):
        try:
            data = json.loads(row["data"])
        except ValueError:
            unmapped.append(
                {"message_id": row["id"], "role": None, "why": "record is not JSON"}
            )
            continue
        reason = why_unmapped(con, row["id"], data)
        if reason is not None:
            unmapped.append(
                {"message_id": row["id"], "role": data.get("role"), "why": reason}
            )
            continue
        role = data.get("role")
        ref = turn_ref(session_id, row["id"])
        text = message_text(con, row["id"])
        attribution[ref] = role
        turns.append(
            {
                "turn_ref": ref,
                "role": role,
                "message_id": row["id"],
                "agent": data.get("agent"),
                "time_created": row["time_created"],
                "text_chars": len(text),
            }
        )
        if want_raw:
            parts = []
            for pid, pdata in part_rows(con, row["id"]):
                parts.append({"id": pid, "data": pdata})
            records.append({"message_id": row["id"], "data": data, "parts": parts})
    return turns, unmapped, attribution, records


def find_words(con, session_id, turns, words):
    hits = []
    for turn in turns:
        if turn["role"] != "user":
            continue
        if words in message_text(con, turn["message_id"]):
            hits.append(turn["turn_ref"])
    return hits


def parse_args(argv):
    opts = {
        "find": None,
        "session": None,
        "workspace": None,
        "setup": None,
        "db": None,
        "raw": False,
    }
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in ("-h", "--help"):
            sys.stdout.write(__doc__)
            raise SystemExit(0)
        if arg == "--json":
            index += 1
            continue
        if arg == "--raw":
            opts["raw"] = True
            index += 1
            continue
        if arg in ("--find", "--session", "--workspace", "--setup", "--db"):
            if index + 1 >= len(argv):
                raise Usage("%s needs a value" % arg)
            name = arg[2:]
            if name in TEST_ONLY and not in_test():
                raise Usage(
                    "%s is a test-only argument (RECHECK_ADAPTER_TEST=1): at run time the "
                    "session is bound through the harness's own pointer (ruling E9-32)" % arg
                )
            opts[name] = argv[index + 1]
            index += 2
            continue
        raise Usage("unknown argument %s" % arg)
    if opts["find"] is not None and not opts["find"].strip():
        raise Usage("--find needs words to look for")
    return opts


def main(argv):
    try:
        opts = parse_args(argv)
    except Usage as exc:
        sys.stderr.write("turns.py: %s\nturns.py: see --help\n" % exc)
        return 2
    try:
        path = store_path(opts["setup"], opts["db"])
    except Usage as exc:
        sys.stderr.write("turns.py: %s\nturns.py: see --help\n" % exc)
        return 2
    try:
        con = connect(path)
        session_id, directory, resolved_by, pointer = resolve_session(
            con, opts["session"], opts["workspace"]
        )
        turns, unmapped, attribution, records = collect(con, session_id, opts["raw"])
        if not attribution:
            raise Missing(
                "the record of session %s holds no turn this helper can attribute (%d row(s), "
                "all harness-written or unreadable); an unusable session record is a failure, "
                "never an empty map (ruling E9-29)" % (session_id, len(unmapped))
            )
        document = {
            "harness": HARNESS,
            "store": path,
            "session_id": session_id,
            "directory": directory,
            "resolved_by": resolved_by,
            "bound_by": (
                "the harness's session pointer at %s (OPENCODE_PID %s)"
                % (pointer["_path"], os.environ.get("OPENCODE_PID"))
                if pointer
                else "a test-only override (RECHECK_ADAPTER_TEST=1)"
            ),
            "turn_ref_shape": "opencode:session <session id>:message <message id>",
            "turn_attribution": attribution,
            "turns": turns,
            "unmapped": unmapped,
        }
        if opts["find"] is not None:
            document["find"] = opts["find"]
            document["found"] = find_words(con, session_id, turns, opts["find"])
        if opts["raw"]:
            document["records"] = records
        con.close()
    except Usage as exc:
        sys.stderr.write("turns.py: %s\nturns.py: see --help\n" % exc)
        return 2
    except Missing as exc:
        sys.stderr.write("turns.py: %s\n" % exc)
        return 3
    except sqlite3.Error as exc:
        sys.stderr.write("turns.py: session store error: %s\n" % exc)
        return 1
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
