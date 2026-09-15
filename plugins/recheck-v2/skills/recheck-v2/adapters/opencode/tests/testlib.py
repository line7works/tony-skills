"""Shared helpers for the OpenCode adapter tests (E9 lane Q, section 9.1).

Everything here is standard library and Python 3.9 syntax. The tests run from any working
directory: paths are resolved from this file, never from the process's cwd.
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTER = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")
SKILL_ROOT = os.path.dirname(os.path.dirname(ADAPTER))
SCRIPTS = os.path.join(SKILL_ROOT, "scripts")

# The store schema the adapter reads, as opencode 1.18.31 declares it (the three tables
# turns.py opens, and only those).
SCHEMA = [
    """CREATE TABLE session (
         id text PRIMARY KEY, project_id text NOT NULL, workspace_id text, parent_id text,
         slug text NOT NULL, directory text NOT NULL, path text, title text NOT NULL,
         version text NOT NULL, share_url text, summary_additions integer,
         summary_deletions integer, summary_files text, summary_diffs text, metadata text,
         cost real, tokens_input integer, tokens_output integer, tokens_reasoning integer,
         tokens_cache_read integer, tokens_cache_write integer, revert text, permission text,
         agent text, model text, time_created integer NOT NULL, time_updated integer NOT NULL,
         time_compacting integer, time_archived integer)""",
    """CREATE TABLE message (
         id text PRIMARY KEY, session_id text NOT NULL, time_created integer NOT NULL,
         time_updated integer NOT NULL, data text NOT NULL)""",
    """CREATE TABLE part (
         id text PRIMARY KEY, message_id text NOT NULL, session_id text NOT NULL,
         time_created integer NOT NULL, time_updated integer NOT NULL, data text NOT NULL)""",
    """CREATE TABLE credential (
         id text PRIMARY KEY, integration_id text, label text NOT NULL, value text NOT NULL,
         connector_id text, method_id text, active integer, time_created integer NOT NULL,
         time_updated integer NOT NULL)""",
]


def load_record():
    with open(os.path.join(FIXTURES, "session-record.json"), encoding="utf-8") as handle:
        return json.load(handle)


STANDIN = """#!/bin/sh
# A stand-in for the pinned opencode binary. It calls no model: it records its arguments, and
# on request the NAMES of the variables in its own environment (never a value, ruling E9-38),
# emits whatever the test put in $RECHECK_STANDIN_TRACE, then exits $RECHECK_STANDIN_RC.
printf '%s\\n' "$*" >> "${RECHECK_STANDIN_ARGS:-/dev/null}"
if [ -n "${RECHECK_STANDIN_ENV:-}" ]; then env | cut -d= -f1 | sort > "$RECHECK_STANDIN_ENV"; fi
if [ -n "${RECHECK_STANDIN_SLEEP:-}" ]; then sleep "$RECHECK_STANDIN_SLEEP"; fi
if [ -n "${RECHECK_STANDIN_TRACE:-}" ] && [ -f "$RECHECK_STANDIN_TRACE" ]; then
  cat "$RECHECK_STANDIN_TRACE"
fi
exit "${RECHECK_STANDIN_RC:-0}"
"""


def standin_binary(setup):
    """Install an executable stand-in at the pinned binary's path and return it."""
    path = os.path.join(setup, "npm", "node_modules", ".bin", "opencode")
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(STANDIN)
    os.chmod(path, 0o755)
    return path


def make_setup(root, record=None, include_constructed=False, directory=None, binary=False):
    """Build a fake isolated setup holding a session store, and return its path.

    The store is created with the real schema and filled from the committed session record, so
    the tests read the same shapes `turns.py` reads in a live setup. A row is put in the
    `credential` table too, so a test can prove the helper never touches it.
    """
    setup = os.path.join(root, "setup")
    data = os.path.join(setup, "xdg-data", "opencode")
    os.makedirs(data)
    os.makedirs(os.path.join(setup, "xdg-config", "opencode"))
    os.makedirs(os.path.join(setup, "xdg-cache"))
    os.makedirs(os.path.join(setup, "xdg-state"))
    if binary:
        standin_binary(setup)
    con = sqlite3.connect(os.path.join(data, "opencode.db"))
    for statement in SCHEMA:
        con.execute(statement)
    if record is not None:
        session = dict(record["session"])
        if directory is not None:
            session["directory"] = directory
        columns = ",".join(session.keys())
        marks = ",".join("?" for _ in session)
        con.execute("insert into session (%s) values (%s)" % (columns, marks),
                    list(session.values()))
        rows = list(record["messages"])
        parts = list(record["parts"])
        if include_constructed:
            rows += record["constructed"]["messages"]
            parts += record["constructed"]["parts"]
        for message in rows:
            con.execute(
                "insert into message (id, session_id, time_created, time_updated, data) "
                "values (?,?,?,?,?)",
                (message["id"], session["id"], message["time_created"],
                 message["time_updated"], message["data"]),
            )
        for part in parts:
            con.execute(
                "insert into part (id, message_id, session_id, time_created, time_updated, data) "
                "values (?,?,?,?,?,?)",
                (part["id"], part["message_id"], session["id"], part["time_created"],
                 part["time_updated"], part["data"]),
            )
    con.execute(
        "insert into credential (id, label, value, time_created, time_updated) values (?,?,?,?,?)",
        ("cred1", "openrouter", "a-value-no-test-may-print", 0, 0),
    )
    con.commit()
    con.close()
    return setup


def store_of(setup):
    return os.path.join(setup, "xdg-data", "opencode", "opencode.db")


def add_session(setup, session_id, directory, message_id, text, model=None):
    """Put a second, complete session in a fake setup's store (the other-session case)."""
    record = load_record()
    session = dict(record["session"])
    session["id"] = session_id
    session["directory"] = directory
    session["slug"] = session_id
    if model is not None:
        session["model"] = json.dumps(model)
    con = sqlite3.connect(store_of(setup))
    columns = ",".join(session.keys())
    marks = ",".join("?" for _ in session)
    con.execute("insert into session (%s) values (%s)" % (columns, marks),
                list(session.values()))
    con.execute(
        "insert into message (id, session_id, time_created, time_updated, data) values (?,?,?,?,?)",
        (message_id, session_id, 1, 1,
         json.dumps({"role": "user", "time": {"created": 1}, "agent": "build"})),
    )
    con.execute(
        "insert into part (id, message_id, session_id, time_created, time_updated, data) "
        "values (?,?,?,?,?,?)",
        (message_id + "-part", message_id, session_id, 1, 1,
         json.dumps({"type": "text", "text": text})),
    )
    con.commit()
    con.close()
    return "opencode:session %s:message %s" % (session_id, message_id)


def append_user_row(setup, session_id, message_id, text, when=10 ** 13):
    """Append a `user` row to an existing session, the way the session itself could.

    Ruling E9-32: OpenCode applies no sandbox to the executor's own tools, so the store stays
    writable by the session. This is the limit the profile declares, not a defect the adapter
    can close; the test records it.
    """
    con = sqlite3.connect(store_of(setup))
    con.execute(
        "insert into message (id, session_id, time_created, time_updated, data) values (?,?,?,?,?)",
        (message_id, session_id, when, when,
         json.dumps({"role": "user", "time": {"created": when}, "agent": "build"})),
    )
    con.execute(
        "insert into part (id, message_id, session_id, time_created, time_updated, data) "
        "values (?,?,?,?,?,?)",
        (message_id + "-part", message_id, session_id, when, when,
         json.dumps({"type": "text", "text": text})),
    )
    con.commit()
    con.close()
    return "opencode:session %s:message %s" % (session_id, message_id)


def write_pointer(root, pid, session_id, command="run", opencode_pid=None):
    """The harness's own session pointer, as `session-pointer.js` writes it."""
    pointer_dir = os.path.join(root, "tmp", "recheck-v2", "opencode")
    if not os.path.isdir(pointer_dir):
        os.makedirs(pointer_dir)
    record = {
        "session_id": session_id,
        "message_id": "msg_x",
        "role": "user",
        "agent": "build",
        "opencode_pid": pid if opencode_pid is None else opencode_pid,
        "cli_command": command,
        "mode": {"run": "headless", "tui": "interactive"}.get(command, "unknown"),
        "written_at": "2026-09-14T00:00:00.000Z",
    }
    with open(os.path.join(pointer_dir, "%s.json" % pid), "w", encoding="utf-8") as handle:
        json.dump(record, handle)
    return {"OPENCODE_PID": str(pid), "TMPDIR": os.path.join(root, "tmp")}


def run(helper, args, cwd=None, env=None):
    """Run an adapter helper from another working directory and capture both streams."""
    environment = dict(os.environ)
    environment.pop("OPENCODE_PID", None)
    environment.pop("RECHECK_OPENCODE_SETUP", None)
    environment.pop("XDG_DATA_HOME", None)
    environment.pop("RECHECK_ADAPTER_TEST", None)
    environment.pop("RECHECK_ADAPTER_CANNED", None)
    if env:
        environment.update(env)
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ADAPTER, helper)] + list(args),
        cwd=cwd or tempfile.gettempdir(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    out, err = proc.communicate()
    return proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def run_core(args, env=None):
    """Run the core CLI through uv (it declares jsonschema in a PEP 723 block)."""
    environment = dict(os.environ)
    if env:
        environment.update(env)
    proc = subprocess.Popen(
        ["uv", "run", os.path.join(SCRIPTS, "recheck.py")] + list(args),
        cwd=tempfile.gettempdir(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    out, err = proc.communicate()
    return proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def git_workspace(path):
    """A minimal committed git work tree, so the core's identity helper has something real."""
    os.makedirs(path, exist_ok=True)
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"})
    subprocess.check_call(["git", "init", "-q", path], env=env)
    with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as handle:
        handle.write("# widget\n")
    subprocess.check_call(["git", "-C", path, "add", "-A"], env=env)
    subprocess.check_call(["git", "-C", path, "commit", "-qm", "base"], env=env)
    return path


def cleanup(path):
    shutil.rmtree(path, ignore_errors=True)
