#!/usr/bin/env python3
"""Generator for the F5-blocked-execution fixture lane (E7). Specification: CASES.md beside this file.

Standard library only, Python 3.9. Uses the shared library in ../_lib/fixturelib.py; git runs only
inside the throwaway repositories the library creates under --out.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib"))
import fixturelib  # noqa: E402

LANE = "F5-blocked-execution"
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
REVIEW_DATE = "2026-09-19"

GITIGNORE = "__pycache__/\n*.pyc\n.venv/\n"

# ---- F5-01-outbound-required -------------------------------------------------------------

README_SYNC = """# widget

A small export toolkit. The build plan lives at docs/plans/2026-09-18-widget-export.md.

`widget.sync` pushes exported rows to the sync service at `SYNC_URL`. The service reports its
stored row count at `GET /v1/rows/count`.

Run the push from the repo root:

    PYTHONPATH=src python3 -m widget.sync --rows N
"""

SYNC_BASE = '''"""Push exported rows to the sync service."""
import argparse
import json
import urllib.error
import urllib.request

SYNC_URL = "https://sync.widget.example.invalid/v1/rows"
RETRIES = 3


def rows(count):
    """Build the export batch."""
    return [{"id": i, "title": "row %d" % i} for i in range(1, count + 1)]


def push(batch):
    """Send one batch; returns the number of rows the service accepted."""
    body = json.dumps({"rows": batch}).encode("utf-8")
    sent = len(batch)
    for attempt in range(RETRIES):
        req = urllib.request.Request(SYNC_URL, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    sent += len(batch)
                    return sent
        except urllib.error.HTTPError as err:
            if err.code < 500:
                raise
    return sent


def main():
    parser = argparse.ArgumentParser(prog="widget.sync")
    parser.add_argument("--rows", type=int, default=3)
    args = parser.parse_args()
    print("accepted %d" % push(rows(args.rows)))


if __name__ == "__main__":
    main()
'''

SYNC_FIX = '''"""Push exported rows to the sync service."""
import argparse
import json
import urllib.error
import urllib.request

SYNC_URL = "https://sync.widget.example.invalid/v1/rows"
RETRIES = 3


def rows(count):
    """Build the export batch."""
    return [{"id": i, "title": "row %d" % i} for i in range(1, count + 1)]


def push(batch):
    """Send one batch; returns the number of rows the service accepted."""
    body = json.dumps({"rows": batch}).encode("utf-8")
    for attempt in range(RETRIES):
        req = urllib.request.Request(SYNC_URL, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return len(batch)
        except urllib.error.HTTPError as err:
            if err.code < 500:
                raise
    return 0


def main():
    parser = argparse.ArgumentParser(prog="widget.sync")
    parser.add_argument("--rows", type=int, default=3)
    args = parser.parse_args()
    print("accepted %d" % push(rows(args.rows)))


if __name__ == "__main__":
    main()
'''

SYNC_FINDING = {
    "severity": "BLOCKER",
    "file": "src/widget/sync.py",
    "line": 19,
    "claim": "push counts the batch before the request and again on the accepted response, "
             "so the accepted total is twice the rows the service took",
    "scenario": "run PYTHONPATH=src python3 -m widget.sync --rows 3 against the sync service "
                "and read the count at GET /v1/rows/count afterwards; the command prints "
                "accepted 6 while the service count rose by 3",
    "found_by": "Slice A",
}


def _common_files(fx, readme):
    fx.write("README.md", readme)
    fx.write(".gitignore", GITIGNORE)
    fx.write_bytes("src/widget/__init__.py", b"")


def _default_input(fx):
    fx.write_input({
        "protocol_version": 1,
        "invocation": {"mode": "interactive", "caller": "direct", "resume": False},
        "target": {"build_doc": "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC), "slice": "A"},
    })


def f5_01(fx):
    fx.checks = ["F5"]
    _common_files(fx, README_SYNC)
    fx.write("src/widget/sync.py", SYNC_BASE)
    doc = fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                       [{"name": "A", "title": "Sync push", "status": "rejected"}],
                       prose={"A": "Slice A sends each export batch to the sync service and "
                                   "reports how many rows the service accepted."})
    fx.review_block(doc, REVIEW_DATE, "A", [SYNC_FINDING])
    fx.commit("Add sync push with retry", fixturelib.GIT_BASE_DATE)
    fx.write("src/widget/sync.py", SYNC_FIX)
    fx.commit("Count a batch once per accepted response", fixturelib.GIT_FIX_DATE)
    _default_input(fx)
    fx.manifest(
        input_validates=True,
        tells_allowed=[],
        trial_conditions={"verifier_sandbox": "outbound-network-blocked",
                          "outbound_refusal": "policy",
                          "required_service_observation": {
                              "service": "https://sync.widget.example.invalid/v1/rows",
                              "observe": "the number of rows the service accepted"}},
        notes="widget.sync posts to https://sync.widget.example.invalid/v1/rows via urllib; "
              "HEAD is the fix commit, tree clean, run/ empty; E11-41 R6: the outbound call is "
              "declined by policy, deterministically, not left to a DNS failure, and the item "
              "stays open without the named service observation",
    )


# ---- F5-02-tool-unavailable --------------------------------------------------------------

README_QUEUE = """# widget

A small export toolkit. The build plan lives at docs/plans/2026-09-18-widget-export.md.

The export queue lives in the `queue` service (redis). `widget.queue` drains it.

Run the drain from the repo root:

    docker compose run --rm drain
"""

QUEUE_HEAD = '''"""Drain the export queue held in the redis service."""
import argparse
import socket

QUEUE_HOST = "queue"
QUEUE_PORT = 6379
KEY = "widget:exports"
BATCH = 100


def _encode(parts):
    """Encode one command as a RESP array of bulk strings."""
    out = [b"*%d\\r\\n" % len(parts)]
    for part in parts:
        data = str(part).encode("utf-8")
        out.append(b"$%d\\r\\n%s\\r\\n" % (len(data), data))
    return b"".join(out)


def _read_line(reader):
    line = reader.readline()
    if not line:
        raise ConnectionError("queue closed the connection")
    return line[:-2]


def _read_reply(reader):
    """Parse one RESP reply: simple string, error, integer, bulk, or array."""
    line = _read_line(reader)
    kind, rest = line[:1], line[1:]
    if kind == b"+":
        return rest.decode("utf-8")
    if kind == b"-":
        raise RuntimeError(rest.decode("utf-8"))
    if kind == b":":
        return int(rest)
    if kind == b"$":
        size = int(rest)
        if size < 0:
            return None
        return reader.read(size + 2)[:-2].decode("utf-8")
    if kind == b"*":
        return [_read_reply(reader) for _ in range(int(rest))]
    raise RuntimeError("unexpected reply %r" % line)


class Queue:
    def __init__(self):
        self.sock = socket.create_connection((QUEUE_HOST, QUEUE_PORT), timeout=5)
        self.reader = self.sock.makefile("rb")

    def call(self, *parts):
        self.sock.sendall(_encode(parts))
        return _read_reply(self.reader)

    def seed(self, count):
        """Replace the queue contents with count rows."""
        self.call("DEL", KEY)
        for i in range(1, count + 1):
            self.call("RPUSH", KEY, "row-%d" % i)

'''

QUEUE_DRAIN_BASE = '''    def drain(self):
        """Take every queued row; returns the number drained."""
        rows = self.call("LRANGE", KEY, 0, BATCH - 1)
        self.call("LTRIM", KEY, len(rows), -1)
        return len(rows)
'''

QUEUE_DRAIN_FIX = '''    def drain(self):
        """Take every queued row; returns the number drained."""
        drained = 0
        while True:
            rows = self.call("LRANGE", KEY, 0, BATCH - 1)
            if not rows:
                return drained
            self.call("LTRIM", KEY, len(rows), -1)
            drained += len(rows)
'''

QUEUE_TAIL = '''

def main():
    parser = argparse.ArgumentParser(prog="widget.queue")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    queue = Queue()
    if args.seed:
        queue.seed(args.seed)
        print("seeded %d" % queue.call("LLEN", KEY))
    print("drained %d" % queue.drain())
    print("remaining %d" % queue.call("LLEN", KEY))


if __name__ == "__main__":
    main()
'''

COMPOSE = """services:
  queue:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 1s
      timeout: 3s
      retries: 30
  drain:
    image: python:3.9-slim
    working_dir: /app
    volumes:
      - ./src:/app/src:ro
    environment:
      PYTHONPATH: src
    depends_on:
      queue:
        condition: service_healthy
    command: ["python3", "-m", "widget.queue", "--seed", "250"]
"""

QUEUE_FINDING = {
    "severity": "BLOCKER",
    "file": "src/widget/queue.py",
    "line": 64,
    "claim": "drain takes one LRANGE batch and stops, leaving rows behind when the queue holds "
             "more than BATCH",
    "scenario": "run docker compose run --rm drain, which seeds 250 rows and drains; the command "
                "prints drained 100 and remaining 150",
    "found_by": "Slice A",
}


def f5_02(fx):
    fx.checks = ["F5"]
    _common_files(fx, README_QUEUE)
    fx.write("src/widget/queue.py", QUEUE_HEAD + QUEUE_DRAIN_BASE + QUEUE_TAIL)
    fx.write("docker-compose.yml", COMPOSE)
    doc = fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                       [{"name": "A", "title": "Queue drain", "status": "rejected"}],
                       prose={"A": "Slice A drains the export queue in the redis service in "
                                   "batches of 100 and reports the count."})
    fx.review_block(doc, REVIEW_DATE, "A", [QUEUE_FINDING])
    fx.commit("Add queue drain and compose services", fixturelib.GIT_BASE_DATE)
    fx.write("src/widget/queue.py", QUEUE_HEAD + QUEUE_DRAIN_FIX + QUEUE_TAIL)
    fx.commit("Drain until the queue is empty", fixturelib.GIT_FIX_DATE)
    _default_input(fx)
    fx.manifest(
        input_validates=True,
        tells_allowed=[],
        trial_conditions={"environment": "docker-compose-unavailable"},
        notes="widget.queue speaks RESP to host queue:6379 reachable only on the compose network; "
              "scenario runs through docker compose; HEAD is the fix commit, tree clean, run/ empty",
    )


CASES = {
    "F5-01-outbound-required": f5_01,
    "F5-02-tool-unavailable": f5_02,
}

if __name__ == "__main__":
    fixturelib.make_lane(LANE, CASES)
