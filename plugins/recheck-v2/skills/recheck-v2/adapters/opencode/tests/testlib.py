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


def make_setup(root, record=None, include_constructed=False, directory=None):
    """Build a fake isolated setup holding a session store, and return its path.

    The store is created with the real schema and filled from the committed session record, so
    the tests read the same shapes `turns.py` reads in a live setup. A row is put in the
    `credential` table too, so a test can prove the helper never touches it.
    """
    setup = os.path.join(root, "setup")
    data = os.path.join(setup, "xdg-data", "opencode")
    os.makedirs(data)
    os.makedirs(os.path.join(setup, "xdg-config", "opencode"))
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


def run(helper, args, cwd=None, env=None):
    """Run an adapter helper from another working directory and capture both streams."""
    environment = dict(os.environ)
    environment.pop("OPENCODE_PID", None)
    environment.pop("RECHECK_OPENCODE_SETUP", None)
    environment.pop("XDG_DATA_HOME", None)
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
