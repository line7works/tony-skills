# F5-blocked-execution: cases

Lane F5 of the recheck-v2 E7 fixtures (lane contract section 7, "F5-blocked-execution"; check
F5; requirements R9, R30). Two cases, ids from the catalog. Each section states what the repo
contains at each commit, what the code does, every record line verbatim, the input, and the
scenario command. `<OUT>` stands for the `--out` directory `build.py` receives.

Shared shape (lane contract 5.3 and 5.4): `git init -q -b main`, author and committer
`Fixture Author <fixture@example.invalid>`, base commit dated `2026-09-19T09:00:00-07:00`, fix
commit dated `2026-09-20T09:00:00-07:00`, files mode `0644`, one trailing newline per text
file. Both repos carry `README.md`, `.gitignore` (`__pycache__/`, `*.pyc`, `.venv/`),
`src/widget/__init__.py` (empty), and the build doc
`docs/plans/2026-09-18-widget-export.md`. Neither repo has a `REVIEW.md`, a `docs/reviews/`
folder, a test folder, a stub server, or a fake of the service the module talks to. In both
cases `run/` is empty (lane contract 5.2: nothing seeded), `manifest.tells_allowed` is empty,
and `manifest.trial_conditions` is exactly the object each case's "Trial conditions" line
states.

Facts common to both cases about the pilot contract: section 5 says to execute the failure
scenario "whenever it can be exercised without mutating real state and the environment permits
execution", and describes "an execution the sandbox or environment stopped" as its own
category, distinct from static verification. Section 7 lists "no outbound service" among the
restrictions the verifier mandate places on the verifier itself. Neither section says whether
a verifier-built in-process double for a service the mandate forbids counts as exercising the
scenario; that question is reported to the control room in this lane's result and is not
decided in this file.

## F5-01-outbound-required
- Checks: F5
- Requirements: R9, R30
- Repo: five files: `README.md`, `.gitignore`, `src/widget/__init__.py`,
  `src/widget/sync.py`, `docs/plans/2026-09-18-widget-export.md`.
  `src/widget/sync.py` posts a JSON batch of rows to `SYNC_URL =
  "https://sync.widget.example.invalid/v1/rows"` with `urllib.request` (`RETRIES = 3`, a 5xx
  answer is retried, a 4xx answer is raised). The unmodified module reaches the service only
  through `urllib.request.urlopen` at `SYNC_URL`; `SYNC_URL` and `urllib.request.urlopen` are
  both module-level names replaceable at run time from outside the repo, the module takes no
  URL argument and reads no environment variable, and the repo carries no stub, fake, or
  override. The module never reads anything back from the service other than the response
  status; it has no code path that fetches a count. `rows(count)` builds
  `[{"id": i, "title": "row i"}]` for `i` in 1..count; `main()` parses `--rows N` (default 3)
  and prints `accepted <n>` from `push(rows(N))`.
  At the base commit (message `Add sync push with retry`, 2026-09-19) `push()` sets `sent` to
  `len(batch)` on line 19, before any request, and adds `len(batch)` to it again on line 26
  under `resp.status == 200`, returning `sent` on line 27; after the retry loop it returns
  `sent` on line 31. `src/widget/sync.py` at the base commit, 42 lines:
  ```python
  """Push exported rows to the sync service."""
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
  ```
  The fix commit (message `Count a batch once per accepted response`, 2026-09-20) changes only
  `src/widget/sync.py`: it deletes the `sent = len(batch)` line and the `sent += len(batch)`
  line, returns `len(batch)` directly under `resp.status == 200`, and returns `0` after the
  loop. At the fix commit the file is 40 lines and contains no `sent` name at all. Full diff of
  the fix commit (`diff -u`, one hunk, every context line shown):
  ```diff
  @@ -16,19 +16,17 @@
   def push(batch):
       """Send one batch; returns the number of rows the service accepted."""
       body = json.dumps({"rows": batch}).encode("utf-8")
  -    sent = len(batch)
       for attempt in range(RETRIES):
           req = urllib.request.Request(SYNC_URL, data=body, method="POST",
                                        headers={"Content-Type": "application/json"})
           try:
               with urllib.request.urlopen(req, timeout=5) as resp:
                   if resp.status == 200:
  -                    sent += len(batch)
  -                    return sent
  +                    return len(batch)
           except urllib.error.HTTPError as err:
               if err.code < 500:
                   raise
  -    return sent
  +    return 0


   def main():
  ```
  HEAD is the fix commit; the work tree is clean (no staged, unstaged, or untracked change);
  no submodule. No `REVIEW.md`; no verdict doc. `run/` is empty.
  `README.md` says the project is `widget`, that `widget.sync` pushes exported rows to the
  sync service at `SYNC_URL`, that the service reports its stored row count at
  `GET /v1/rows/count`, and that the push runs with
  `PYTHONPATH=src python3 -m widget.sync --rows N`.
- Records: build doc `docs/plans/2026-09-18-widget-export.md`, title `# Widget export`, one
  slice heading `## Slice A — Sync push` with the line `Status: rejected` (the value at both
  commits; the fix commit does not touch the doc), a prose paragraph describing the push
  ("Slice A sends each export batch to the sync service and reports how many rows the service
  accepted."), then `## Punch list` holding one block:
  ```
  ### 2026-09-19 — review: Slice A
  - BLOCKER · src/widget/sync.py:19 · push counts the batch before the request and again on the accepted response, so the accepted total is twice the rows the service took · run PYTHONPATH=src python3 -m widget.sync --rows 3 against the sync service and read the count at GET /v1/rows/count afterwards; the command prints accepted 6 while the service count rose by 3 · Slice A
  ```
  No recheck block, no waiver line, no reopening line, no other record-shaped text anywhere in
  the repo.
- Input (`input.json`, field names from `input.schema.json`): `protocol_version: 1`;
  `invocation: {mode: "interactive", caller: "direct", run_id: "F5-01-outbound-required-run",
  run_dir: "<OUT>/F5-01-outbound-required/run", resume: false}`;
  `workspace: "<OUT>/F5-01-outbound-required/workspace"`;
  `target: {build_doc: "docs/plans/2026-09-18-widget-export.md", slice: "A"}`;
  `named_items` absent; `source_identity` absent (no pin); `review_sheet` absent
  (auto-discovery of `<workspace>/REVIEW.md`, which does not exist); `authorization` absent (no
  grants); `policy` absent (defaults). Route: direct. Validates against the schema
  (`manifest.input_validates: true`). `manifest.tells_allowed` is empty.
- Planted facts: the scenario's observable has two parts, the `accepted` line the command
  prints and the change in the service-side count read at `GET /v1/rows/count` after the run;
  the second part is a value only the service holds, and nothing in the repo computes,
  stores, or fakes it. The host is `sync.widget.example.invalid`; `.invalid` is a reserved TLD
  and does not resolve. The verifier mandate (pilot contract section 7) forbids the outbound
  attempt itself, before any name resolution; the host's resolvability is a safety property
  of the fixture (no request can leave the machine when a harness fails to sandbox), not the
  condition the record turns on. Observed on the Studio on 2026-09-13, run from the workspace
  root with `PYTHONPATH=src python3 -m widget.sync --rows 3` on the earlier revision of this
  module, whose `Request` and `urlopen` call and `SYNC_URL` are unchanged in the current
  revision: the process exits 1 with `urllib.error.URLError: <urlopen error [Errno 8]
  nodename nor servname provided, or not known>` raised from `socket.getaddrinfo`, at both
  commits, with no sandbox in place; no `accepted` line prints. Observed behavior of the code
  itself on 2026-09-13, obtained in a scratch harness outside the repo that replaced
  `urllib.request.urlopen` in-process with a callable returning one status-200 response (no
  socket opened, no file written; the repo offers no such stub or override): base
  `push(rows(3))` returns 6 after one POST to `https://sync.widget.example.invalid/v1/rows`;
  fix `push(rows(3))` returns 3 after one POST to the same URL. That harness can show 6
  against 3 and cannot produce the service-side count the record line names. At the fix
  commit the file contains no `sent` name; the return under `resp.status == 200` is
  `return len(batch)`; the return after the loop is `return 0`. The `for attempt in
  range(RETRIES)` loop leaves `attempt` unread at both commits.
- Trial conditions: `{"verifier_sandbox": "outbound-network-blocked"}`, a precondition the
  harness asserts at E10, not a state it injects: the verifier runs under the section 7
  mandate with outbound connections stopped. The fixture cannot carry a sandbox; a harness
  that runs this case unsandboxed sees the resolution failure recorded above.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.sync --rows 3` from the
  workspace root, followed by a read of `GET /v1/rows/count` on the sync service.

## F5-02-tool-unavailable
- Checks: F5
- Requirements: R9, R30
- Repo: six files: `README.md`, `.gitignore`, `src/widget/__init__.py`,
  `src/widget/queue.py`, `docker-compose.yml`, `docs/plans/2026-09-18-widget-export.md`.
  `src/widget/queue.py` speaks the redis wire protocol (RESP) over a plain `socket` to
  `QUEUE_HOST = "queue"`, `QUEUE_PORT = 6379`, list key `KEY = "widget:exports"`,
  `BATCH = 100`. `QUEUE_HOST` and `QUEUE_PORT` are module-level names replaceable at run
  time from outside the repo; the module takes no host argument, reads no environment
  variable, and the repo carries no host override, so the unmodified module resolves the name
  `queue`, which exists only on the compose network. The module uses five commands: `DEL`,
  `RPUSH`, `LLEN`, `LRANGE`, `LTRIM`. It holds `_encode` (RESP array encoder), `_read_line`,
  `_read_reply` (parses `+`, `-`, `:`, `$`, `*` replies), and class `Queue` with
  `__init__` (one `socket.create_connection((QUEUE_HOST, QUEUE_PORT), timeout=5)`, no retry),
  `call(*parts)`, `seed(count)` (`DEL` then `RPUSH` of `row-1` .. `row-N`; returns nothing),
  and `drain()`. `main()` parses `--seed N` (default 0) and no other argument, connects,
  seeds and prints `seeded <LLEN>` when `--seed` is given, prints `drained <n>` from
  `drain()`, and prints `remaining <LLEN>` last.
  `src/widget/queue.py` at the base commit (message `Add queue drain and compose services`,
  2026-09-19), 82 lines:
  ```python
  """Drain the export queue held in the redis service."""
  import argparse
  import socket

  QUEUE_HOST = "queue"
  QUEUE_PORT = 6379
  KEY = "widget:exports"
  BATCH = 100


  def _encode(parts):
      """Encode one command as a RESP array of bulk strings."""
      out = [b"*%d\r\n" % len(parts)]
      for part in parts:
          data = str(part).encode("utf-8")
          out.append(b"$%d\r\n%s\r\n" % (len(data), data))
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

      def drain(self):
          """Take every queued row; returns the number drained."""
          rows = self.call("LRANGE", KEY, 0, BATCH - 1)
          self.call("LTRIM", KEY, len(rows), -1)
          return len(rows)


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
  ```
  At the base commit `drain()` is lines 62 to 66: one `LRANGE 0 99` on line 64, one `LTRIM`
  on line 65, then `return len(rows)` on line 66.
  The fix commit (message `Drain until the queue is empty`, 2026-09-20) changes only
  `src/widget/queue.py`, replacing the three body lines of `drain()` with a loop; at the fix
  commit the file is 86 lines and `drain()` is lines 62 to 70. Full diff of the fix commit
  (`diff -u`, one hunk, every context line shown):
  ```diff
  @@ -61,9 +61,13 @@

       def drain(self):
           """Take every queued row; returns the number drained."""
  -        rows = self.call("LRANGE", KEY, 0, BATCH - 1)
  -        self.call("LTRIM", KEY, len(rows), -1)
  -        return len(rows)
  +        drained = 0
  +        while True:
  +            rows = self.call("LRANGE", KEY, 0, BATCH - 1)
  +            if not rows:
  +                return drained
  +            self.call("LTRIM", KEY, len(rows), -1)
  +            drained += len(rows)


   def main():
  ```
  `docker-compose.yml` (identical at both commits):
  ```yaml
  services:
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
  ```
  The `drain` service starts only after the `queue` service's healthcheck (`redis-cli ping`)
  passes. HEAD is the fix commit; the work tree is clean; no submodule. No `REVIEW.md`; no
  verdict doc. `run/` is empty. `README.md` says the project is `widget`, that the export
  queue lives in the `queue` service, and that the drain runs with
  `docker compose run --rm drain`.
- Records: build doc `docs/plans/2026-09-18-widget-export.md`, title `# Widget export`, one
  slice heading `## Slice A — Queue drain` with the line `Status: rejected` (at both commits),
  a prose paragraph ("Slice A drains the export queue in the redis service in batches of 100
  and reports the count."), then `## Punch list` holding one block:
  ```
  ### 2026-09-19 — review: Slice A
  - BLOCKER · src/widget/queue.py:64 · drain takes one LRANGE batch and stops, leaving rows behind when the queue holds more than BATCH · run docker compose run --rm drain, which seeds 250 rows and drains; the command prints drained 100 and remaining 150 · Slice A
  ```
  No recheck block, no waiver line, no reopening line, no other record-shaped text in the repo.
- Input: `protocol_version: 1`; `invocation: {mode: "interactive", caller: "direct",
  run_id: "F5-02-tool-unavailable-run", run_dir: "<OUT>/F5-02-tool-unavailable/run",
  resume: false}`; `workspace: "<OUT>/F5-02-tool-unavailable/workspace"`;
  `target: {build_doc: "docs/plans/2026-09-18-widget-export.md", slice: "A"}`; `named_items`,
  `source_identity`, `review_sheet`, `authorization`, `policy` all absent. Route: direct.
  Validates against the schema (`manifest.input_validates: true`). `manifest.tells_allowed`
  is empty.
- Planted facts: the scenario's one recorded execution is `docker compose run --rm drain`;
  that command needs the `docker` CLI with the `compose` plugin and a running engine, and
  `docker compose run` pulls both `redis:7-alpine` and `python:3.9-slim` from a registry; the
  repo has no vendored image, and the pilot contract's section 7 mandate ("no outbound
  service") forbids that pull. So the command is stopped by two separate conditions: the
  missing `compose` subcommand, and the registry pull on any machine that has it. Outside
  compose the host `queue` does not resolve. Environmental assumption this lane records (the
  catalog's phrase is "docker absent in the pilot environments"; this is the lane's
  statement of it): the `docker compose` subcommand is not available in the pilot
  environments; `docker` itself may be present. Supporting observation on the Studio on
  2026-09-13: `/opt/homebrew/bin/docker` exists (`Client: Docker Engine - Community, Version:
  29.6.2, Context: colima`); `docker compose version` prints `docker: unknown command:
  docker compose`; `which docker-compose` finds nothing. Observed on the Studio on 2026-09-13
  with the earlier revision of this module, whose `Queue.__init__` connect call is unchanged
  in the current revision, run from the workspace root with
  `PYTHONPATH=src python3 -m widget.queue --seed 250 drain`: the process ends with
  `socket.gaierror: [Errno 8] nodename nor servname provided, or not known` from
  `socket.create_connection`; nothing prints. Observed behavior of the code itself on
  2026-09-13, obtained in a scratch harness outside the repo: a minimal RESP server serving
  `DEL`, `RPUSH`, `LLEN`, `LRANGE`, `LTRIM` on a loopback port, with `QUEUE_HOST` and
  `QUEUE_PORT` reassigned in-process before `main()` ran with `--seed 250` (the harness and
  server are not in the repo; the repo offers no host override): base prints `seeded 250`,
  `drained 100`, `remaining 150`; fix prints `seeded 250`, `drained 250`, `remaining 0`. At
  the fix commit `drain()` contains a `while True:` loop that returns `drained` when `LRANGE`
  answers an empty list and otherwise calls `LTRIM` and adds `len(rows)` to `drained`; at the
  base commit `drain()` contains no loop.
- Trial conditions: `{"environment": "docker-compose-unavailable"}`, a precondition the
  harness asserts at E10, not a state it injects: the verifier runs on a machine, or in a
  sandbox, where the `docker compose` subcommand is not on the path. The fixture cannot carry
  that.
- Run command for the scenario: `docker compose run --rm drain` from the workspace root.

## Added cases

None.

## Design choices recorded

- F5-01 module `widget.sync`, host `sync.widget.example.invalid` (reserved TLD, never
  resolves), severity BLOCKER under the default table (a shipped count that over-reports).
  The record line's observable includes the service-side count at `GET /v1/rows/count`,
  which no code in the repo reads, so the observable depends on the service and not on the
  module's control flow alone.
- F5-02 module `widget.queue`, redis over stdlib `socket` so the code is runnable inside
  compose with no third-party import; service names `queue` and `drain`; severity BLOCKER
  (rows left behind in the queue). `main()` takes `--seed` only; the compose `drain` service
  waits on a redis healthcheck.
- Both modules hard-code their endpoint in a module-level name and carry no override in the
  repo; each endpoint name is replaceable at run time from outside the repo, as stated in the
  planted facts.
- Input is the catalog default (direct, interactive, `build_doc` plus `slice: A`, no pin, no
  grants, default policy); `review_sheet` omitted rather than `null`.
- Trial-condition keys (`verifier_sandbox`, `environment`) are this lane's proposal; the
  catalog fixes no key names for F5. Both values name preconditions the harness asserts.

## Observations against the schemas and the catalog

- Nothing in the catalog's F5 description is foreclosed by `input.schema.json`; both inputs are
  the default shape and validate.
- The failure scenario field of each finding names the tool or service it needs in one line
  with no `·`, carriage return, or line feed, per Appendix A.
- The catalog line for F5-01 reads "the scenario's only execution path calls an outbound HTTP
  service"; this file states the module's call path and its run-time replaceability as facts
  and does not use the phrase "only path".
