#!/usr/bin/env python3
"""The user channel for the OpenCode adapter (recheck-v2, E9 lane Q).

Reads the session store OpenCode 1.18.31 keeps at
``<XDG_DATA_HOME>/opencode/opencode.db`` (SQLite) and prints this session's turn list as
``turn_attribution``: a map from ``turn_ref`` to ``user``, ``assistant``, or ``station``.
The ``turn_ref`` shape for this harness is::

    opencode:session <session id>:message <message id>

Nothing here is composed by a model: every id, role and timestamp is read out of the record
the harness itself wrote. Only the ``session``, ``message`` and ``part`` tables are read; the
store's ``credential`` and ``account`` tables are never opened.

Arguments
---------
--find WORDS      print, under ``found``, the user turns whose own text contains WORDS
                  verbatim (substring, case sensitive). Assistant turns holding the same
                  words are never returned.
--json            accepted and ignored: this helper always prints JSON on stdout (A7a).
--session ID      use this session id instead of resolving one (default: resolve, below).
--workspace DIR   the directory whose newest session is taken when nothing else resolves
                  (default: the current working directory).
--setup DIR       the isolated pilot setup (default: $RECHECK_OPENCODE_SETUP, else
                  ~/.local/share/skills-v2-pilot/opencode).
--db PATH         the session store file (default: derived from --setup / $XDG_DATA_HOME).
--raw             add each message's and part's raw record from the store under ``records``.
--help            this text.

How the session is resolved, in order (the chosen one is reported as ``resolved_by``):

1. ``--session``: ``explicit``.
2. ``$OPENCODE_PID`` plus the pointer file
   ``${TMPDIR}/recheck-v2/opencode/<pid>.json`` the setup's ``session-pointer.js`` plugin
   writes at ``chat.message``: ``pointer``. Measured on 1.18.31: the tool shell is given
   ``OPENCODE=1`` and ``OPENCODE_PID=<the opencode process id>`` and no session id, and the
   plugin runs in that same process, so its ``process.pid`` is that value. The payload comes
   from the harness's own hook input, never from the model.
3. the newest session in the store whose ``directory`` is the workspace:
   ``newest-in-directory``. Ambiguous when two sessions ran in one directory; the count is
   reported as ``candidates`` so the caller can see it.

Example::

    python3 turns.py --find "waive the comma one, ship it"

prints ``{"harness": "opencode", "session_id": "ses_...", "resolved_by": "pointer",
"turn_attribution": {"opencode:session ses_...:message msg_...": "user", ...},
"found": ["opencode:session ses_...:message msg_..."], ...}``.

Exit status: 0 success; 2 a usage slip; 3 a record this helper needs is absent (the session
store file, or no session for the workspace); 1 anything else. Side effects: none, the store
is opened read-only.
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


class Usage(Exception):
    pass


class Missing(Exception):
    pass


def turn_ref(session_id, message_id):
    return "opencode:session %s:message %s" % (session_id, message_id)


def store_path(setup, db):
    if db:
        return os.path.abspath(db)
    if setup:
        return os.path.join(os.path.abspath(setup), "xdg-data", "opencode", "opencode.db")
    env_setup = os.environ.get("RECHECK_OPENCODE_SETUP")
    if env_setup:
        return os.path.join(os.path.abspath(env_setup), "xdg-data", "opencode", "opencode.db")
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        return os.path.join(os.path.abspath(data_home), "opencode", "opencode.db")
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


def pointer_record():
    pid = os.environ.get("OPENCODE_PID")
    if not pid:
        return None
    path = os.path.join(
        os.environ.get("TMPDIR", "/tmp"), "recheck-v2", "opencode", "%s.json" % pid
    )
    try:
        with open(path) as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError):
        return None


def resolve_session(con, explicit, workspace):
    if explicit:
        row = con.execute(
            "select id, directory from session where id = ?", (explicit,)
        ).fetchone()
        if row is None:
            raise Missing("no session %s in the session store" % explicit)
        return row["id"], row["directory"], "explicit", 1
    pointer = pointer_record()
    if pointer and pointer.get("session_id"):
        row = con.execute(
            "select id, directory from session where id = ?", (pointer["session_id"],)
        ).fetchone()
        if row is not None:
            return row["id"], row["directory"], "pointer", 1
        sys.stderr.write(
            "turns.py: the session pointer names %s, which is not in the store; "
            "falling back to the newest session in the workspace\n" % pointer["session_id"]
        )
    target = os.path.realpath(workspace)
    rows = [
        r
        for r in con.execute("select id, directory, time_created from session")
        if r["directory"] and os.path.realpath(r["directory"]) == target
    ]
    if not rows:
        raise Missing("no session in the store ran in %s" % target)
    rows.sort(key=lambda r: r["time_created"], reverse=True)
    return rows[0]["id"], rows[0]["directory"], "newest-in-directory", len(rows)


def message_text(con, message_id):
    chunks = []
    for row in con.execute(
        "select data from part where message_id = ? order by time_created", (message_id,)
    ):
        try:
            data = json.loads(row["data"])
        except ValueError:
            continue
        if data.get("type") == "text" and isinstance(data.get("text"), str):
            chunks.append(data["text"])
    return "\n".join(chunks)


def collect(con, session_id, want_raw):
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
        role = data.get("role")
        agent = data.get("agent")
        ref = turn_ref(session_id, row["id"])
        if role not in ("user", "assistant"):
            unmapped.append(
                {"message_id": row["id"], "role": role, "why": "role is not user or assistant"}
            )
            continue
        if agent in INTERNAL_AGENTS:
            unmapped.append(
                {
                    "message_id": row["id"],
                    "role": role,
                    "why": "written by the harness's own %s agent, not a turn" % agent,
                }
            )
            continue
        text = message_text(con, row["id"])
        attribution[ref] = role
        turns.append(
            {
                "turn_ref": ref,
                "role": role,
                "message_id": row["id"],
                "agent": agent,
                "time_created": row["time_created"],
                "text_chars": len(text),
            }
        )
        if want_raw:
            parts = []
            for prow in con.execute(
                "select id, data, time_created from part where message_id = ? "
                "order by time_created",
                (row["id"],),
            ):
                try:
                    parts.append({"id": prow["id"], "data": json.loads(prow["data"])})
                except ValueError:
                    parts.append({"id": prow["id"], "data": None})
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
        "workspace": os.getcwd(),
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
            opts[arg[2:]] = argv[index + 1]
            index += 2
            continue
        raise Usage("unknown argument %s" % arg)
    return opts


def main(argv):
    try:
        opts = parse_args(argv)
    except Usage as exc:
        sys.stderr.write("turns.py: %s\nturns.py: see --help\n" % exc)
        return 2
    try:
        path = store_path(opts["setup"], opts["db"])
        con = connect(path)
        session_id, directory, resolved_by, candidates = resolve_session(
            con, opts["session"], opts["workspace"]
        )
        turns, unmapped, attribution, records = collect(con, session_id, opts["raw"])
        document = {
            "harness": HARNESS,
            "store": path,
            "session_id": session_id,
            "directory": directory,
            "resolved_by": resolved_by,
            "candidates": candidates,
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
