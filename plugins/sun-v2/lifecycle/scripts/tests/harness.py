"""The test side of the seams: a fixture machine under a temporary directory, a recording file system,
a captured output, a fixed clock, ids from a counter, a cue that only records.

Nothing here is reached by the core. A test builds a `Machine`, plants what its case needs, and
drives the real command line in-process through `Machine.run(...)` (or as a child process, for the
contract of the command line itself and for a real kill). The record a test reads is `Recorder`'s:
one ordered list of every file-system act, every byte of output, every child and every request, so
"this read stood before that write" is shown from the record and not from the order of the code.
"""
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(TESTS)
LIFECYCLE = os.path.dirname(SCRIPTS)
PLUGIN = os.path.dirname(LIFECYCLE)
SUN = os.path.join(SCRIPTS, "sun.py")
FAKES = os.path.join(TESTS, "fakes")
FAKE_SYSTEM = os.path.join(FAKES, "system")      # the fixture's own system folder: its zsh (SEC-3's shortcut check)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from sun_core import fsio, journal as journalmod, keys, locks as locksmod, protected, rundir  # noqa: E402
from sun_core import facts as factsmod, texts, world as worldmod  # noqa: E402

VAULT_MARKER = "MARKER.md"
VAULT_PROJECTS = "projects"
SYNCED = "Synced"


class Killed(SystemExit):
    """Raised at a kill point of an in-process drive. Nothing of the core catches a `SystemExit` (the first code lets
    it through, `sun.start`), and the harness drops every lock the dead invocation held, as the system would."""


class Recorder(object):
    """One ordered list of every act. A kill is asked for by `kill_at`, a predicate over an event: the
    invocation dies when it is first true. A kill at a `mid` event finds a write that is not yet
    synced, and the fake file system loses it (LOG-1's test line): `Unsynced.lose` undoes it first."""

    def __init__(self, sink=None):
        self.events = []
        self.kill_at = None
        self.on_kill = None       # what dying is: raising Killed in-process, or a real SIGKILL in a child
        self.torn = False         # a cut-off append leaves half its bytes instead of none
        self.unsynced = Unsynced()
        self.sink = sink          # a file the events are also written to, one JSON line each

    def add(self, stage, op, subject, **more):
        event = {"i": len(self.events), "stage": stage, "op": op, "subject": subject}
        event.update(more)
        self.events.append(event)
        if self.sink is not None:
            os.write(self.sink, (json.dumps(event, sort_keys=True, default=str) + "\n").encode("utf-8"))
        self.unsynced.see(event)
        kill = self.kill_at
        if kill is not None and kill(event):
            self.kill_at = None
            if stage == "mid":
                self.unsynced.lose(event, self.torn)
            if self.on_kill is not None:
                self.on_kill(event)
            raise Killed(event["i"])

    def reads(self, upto=None):
        out = []
        for event in self.events:
            if upto is not None and event["i"] >= upto:
                break
            if event["stage"] == "read":
                out.append(event["subject"])
        return out

    def first_output(self):
        for event in self.events:
            if event["stage"] == "output":
                return event["i"]
        return None

    def mark(self):
        return len(self.events)

    def since(self, mark):
        return self.events[mark:]


class Unsynced(object):
    """What a kill takes with it: the one write that was made and not yet synced."""

    def __init__(self):
        self.saved = None

    def see(self, event):
        # before a swap or a removal, keep what is about to go, so that losing the unsynced act can put it back
        if event["stage"] == "pre" and event["op"] in ("swap", "remove") and os.path.isfile(event["subject"]) \
                and not os.path.islink(event["subject"]):
            with open(event["subject"], "rb") as fh:
                self.saved = (event["subject"], fh.read(), stat.S_IMODE(os.stat(event["subject"]).st_mode))
        elif event["stage"] == "pre" and event["op"] == "remove" and os.path.isdir(event["subject"]):
            self.saved = (event["subject"], None, stat.S_IMODE(os.stat(event["subject"]).st_mode))

    def lose(self, event, torn):
        op, subject = event["op"], event["subject"]
        if op == "create":
            os.remove(subject)
        elif op == "append":
            size = os.path.getsize(subject) - event.get("size", 0)
            with open(subject, "r+b") as fh:
                fh.truncate(size + (event.get("size", 0) // 2 if torn else 0))
        elif op == "mkdir":
            os.rmdir(subject)
        elif op == "rename":
            os.rename(subject, event["source"])
        elif op == "replace":
            os.remove(event["staged"])
        elif op in ("swap", "remove") and self.saved and self.saved[0] == subject:
            if op == "swap":
                os.rename(subject, event["source"])
            if self.saved[1] is None:
                os.mkdir(subject, self.saved[2])
            else:
                with open(subject, "wb") as fh:
                    fh.write(self.saved[1])
                os.chmod(subject, self.saved[2])


class RecFS(fsio.FS):
    """The real file system under the fixture, every act recorded, every lock it hands out remembered."""

    def __init__(self, recorder):
        fsio.FS.__init__(self, hook=recorder.add)
        self.lock_fds = []
        self.other_volumes = []        # path prefixes the fixture says lie on another volume

    def volume(self, path):
        for index, prefix in enumerate(self.other_volumes):
            if path == prefix or path.startswith(prefix + os.sep):
                self.note("read", "lstat", path)
                return -(index + 1)
        return fsio.FS.volume(self, path)

    def lock_exclusive(self, path, create):
        fd = fsio.FS.lock_exclusive(self, path, create)
        if fd is not None:
            self.lock_fds.append(fd)
        return fd

    def unlock(self, fd, path, remove):
        if fd in self.lock_fds:
            self.lock_fds.remove(fd)
        return fsio.FS.unlock(self, fd, path, remove)

    def drop_locks(self):
        """What the system does for a holder that died: every lock it held is released."""
        for fd in self.lock_fds:
            try:
                os.close(fd)
            except OSError:
                pass
        self.lock_fds = []


class Capture(worldmod.Output):
    def __init__(self, recorder):
        worldmod.Output.__init__(self)
        self.recorder = recorder
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def out(self, text):
        self.recorder.add("output", "stdout", "stdout", size=len(text.encode("utf-8")))
        self.stdout.write(text)

    def err(self, text):
        self.recorder.add("output", "stderr", "stderr", size=len(text.encode("utf-8")))
        self.stderr.write(text)


class Result(object):
    def __init__(self, code, out, err, events, killed=False):
        self.code = code
        self.out = out
        self.err = err
        self.events = events
        self.killed = killed
        try:
            self.doc = json.loads(out) if out.strip() else None
        except ValueError:
            self.doc = None

    @property
    def text(self):
        """Everything the invocation printed, on both streams."""
        return self.out + self.err

    @property
    def lines(self):
        return (self.doc or {}).get("lines") or []

    @property
    def ending(self):
        return (self.doc or {}).get("ending")


def tree(root):
    """{relative path: (kind, mode, sha256 or link target)} of everything under `root`."""
    out = {}
    if not os.path.lexists(root):
        return out
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            st = os.lstat(full)
            if stat.S_ISLNK(st.st_mode):
                out[rel] = ("link", 0, os.readlink(full))
            elif stat.S_ISDIR(st.st_mode):
                out[rel] = ("dir", stat.S_IMODE(st.st_mode), "")
            else:
                with open(full, "rb") as fh:
                    out[rel] = ("file", stat.S_IMODE(st.st_mode), hashlib.sha256(fh.read()).hexdigest())
    return out


class Machine(object):
    """One fixture machine: a home with a sound vault, a settings file, and nothing else."""

    def __init__(self, root, name="home", seed="a", create=True):
        self.root = os.path.realpath(root)
        self.home = os.path.join(self.root, name)
        if create:
            os.makedirs(self.home)
        self.name = name
        self.seed = seed
        self.counter = 0
        self.clock = 0
        self.recorder = Recorder()
        self.cue_calls = []
        self.env = {"HOME": self.home, "PATH": FAKES + os.pathsep + "/usr/bin:/bin", "USER": "fixture",
                    "LOGNAME": "fixture", "LANG": "xx_XX.UTF-8"}
        self.rows_root = None
        self.transport = None
        self.dev = os.path.join(self.home, "dev")
        self.archive = os.path.join(self.home, "dev", "_archive")
        self.vault = os.path.join(self.home, "vault")
        self.settings = {"settings_version": 1,
                         "vault": {"path": self.vault, "marker_file": VAULT_MARKER, "projects_dir": VAULT_PROJECTS,
                                   "synced_segments": [SYNCED]},
                         "locations": {"developer_root": self.dev, "archive_root": self.archive,
                                       "shortcut_file": os.path.join(self.home, "shortcuts.txt")},
                         "accounts": {"fakehost": ["fixture-account"], "fakegit": ["fixture-account"]},
                         "program_folders": [FAKES]}       # the fakes stand on the search list by his naming them (SEC-3)
        if create:
            os.makedirs(os.path.join(self.vault, VAULT_PROJECTS))
            with open(os.path.join(self.vault, VAULT_MARKER), "w") as fh:
                fh.write("# fixture vault\n")
            os.makedirs(self.dev)
            self.write_settings()
        self.facts = factsmod.Facts(self.env)
        self.drives = 0
        # the fixture account's own temporary folder, as the fixture's system gives it (SEC-3's environment row, A58):
        # outside the home, owner-only
        self.user_temp = os.path.join(self.root, "account-tmp-" + name)
        if create:
            os.makedirs(self.user_temp, 0o700)
            os.chmod(self.user_temp, 0o700)
        # the fixture's system folders: its own, which holds the fake zsh, then the system's (SEC-3; RK12)
        self.system_folders = (FAKE_SYSTEM,) + tuple(factsmod.SYSTEM_FOLDERS)
        self.start = None         # the fixture's system's start of a process, where a test gives one (`rowlib.refuse_start`)

    # ---- the fixture's own hands (never recorded: the owner, another actor) ----------------------
    def write_settings(self):
        path = os.path.join(self.home, factsmod.SETTINGS_REL)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(self.settings, fh, indent=2, sort_keys=True)

    def path(self, *parts):
        return os.path.join(self.home, *parts)

    def put(self, rel, text, mode=0o644):
        full = self.path(rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(text)
        os.chmod(full, mode)
        return full

    def inputs(self, name="inputs.json", **fields):
        """An inputs file of the owner's, outside the home the tool works in."""
        doc = {"input_version": 1, "description": "a fixture project", "answers": {}, "flags": {}}
        doc.update(fields)
        path = os.path.join(self.root, name)
        with open(path, "w") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
        return path

    def snapshot(self, rel=""):
        return tree(os.path.join(self.home, rel) if rel else self.home)

    # ---- the seams ------------------------------------------------------------------------------
    def next_id(self, prefix):
        self.counter += 1
        return "%s-%s" % (prefix, hashlib.sha256(("%s:%d" % (self.seed, self.counter)).encode()).hexdigest()[:16])

    def next_hex(self, nbytes):
        self.counter += 1
        return hashlib.sha256(("hex:%s:%d" % (self.seed, self.counter)).encode()).hexdigest()[:2 * nbytes].ljust(2 * nbytes, "0")

    def now(self):
        self.clock += 1
        return "2026-01-01T00:%02d:%02dZ" % (self.clock // 60 % 60, self.clock % 60)

    def world(self, env=None):
        world = worldmod.World()
        world.env = dict(self.env)
        world.env.update(env or {})
        world.fs = RecFS(self.recorder)
        world.fs.other_volumes = list(getattr(self, "other_volumes", []))
        world.output = Capture(self.recorder)
        world.now = self.now
        world.new_id = self.next_id
        world.random_hex = self.next_hex
        world.cue = lambda kind: self.cue_calls.append(kind)
        world.rows_root = self.rows_root
        world.transport = self.transport
        world.system_folders = tuple(self.system_folders)
        world.user_temp = lambda: self.user_temp
        if getattr(self, "start", None) is not None:
            # the fixture's system's start of a process, where a test has it give the answer (A115: "its pass has the
            # fixture's system give that answer"); otherwise the world's own
            world.start = self.start
        return world

    def run(self, *argv, **kw):
        """Drive the command line in-process, through the code the entry point runs (`sun.start`: the withheld read,
        then the rest of the tool). `kill` is a predicate over a recorded event: the
        invocation dies when it is first true, with its locks dropped as the system would."""
        import sun                      # the file the start hands to the interpreter: its `start` is the code it runs
        world = self.world(kw.get("env"))
        mark = self.recorder.mark()
        self.recorder.kill_at = kw.get("kill")
        killed = False
        try:
            code = sun.start([str(a) for a in argv], world)
        except Killed:
            code, killed = 137, True
            world.fs.drop_locks()
        finally:
            self.recorder.kill_at = None
        return Result(code, world.output.stdout.getvalue(), world.output.stderr.getvalue(), self.recorder.since(mark), killed)

    def drive(self, *argv, **kw):
        """Drive the command line in a child process of its own, through `tests/drive.py`, with this
        machine's seams: for a real kill. `kill_at` is the number of the write boundary the child
        dies at, by a real SIGKILL of its own PID; `events` is where it writes its record."""
        self.drives += 1
        config = {"root": self.root, "name": self.name, "seed": "%s/drive-%d" % (self.seed, self.drives),
                  "rows_root": self.rows_root, "kill_at": kw.get("kill_at"), "torn": bool(kw.get("torn")),
                  "events": kw.get("events"), "env": kw.get("env") or {}, "clock": self.clock + 1000 * self.drives}
        path = os.path.join(self.root, "drive-%s-%d.json" % (self.seed.replace("/", "_"), self.drives))
        with open(path, "w") as fh:
            json.dump(config, fh)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run([sys.executable, os.path.join(TESTS, "drive.py"), path] + [str(a) for a in argv], env=env,
                              cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        return Result(proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8"), [], proc.returncode == -9)

    def run_child(self, *argv, **kw):
        """Drive the shipped tool as a child process, by its one start: the contract of the command line itself."""
        env = dict(self.env)
        env.pop("SUN_V2_TEST", None)
        env.update(kw.get("env") or {})
        runtime = kw.get("runtime") or ["/bin/sh", os.path.join(SCRIPTS, "sun")]     # the one start (RUN-1, A47)
        proc = subprocess.run(runtime + [str(a) for a in argv], env=env, cwd=kw.get("cwd") or self.root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        return Result(proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8"), [])

    # ---- the summonses, as an executor would make them ---------------------------------------------
    def look(self, name="demo", kind="sunrise", also=(), inputs=None, caps=None, **kw):
        argv = ["look", "--kind", kind, "--name", name, "--inputs", inputs or self.inputs()]
        for more in also:
            argv += ["--also", more]
        if caps is not None:
            argv += ["--capabilities", self.capabilities(caps)]
        return self.run(*argv, **kw)

    def go(self, looked, name="demo", kind="sunrise", also=(), caps=None, **kw):
        argv = ["go", "--kind", kind, "--name", name, "--run", looked.doc["run"], "--manifest-sha256", looked.doc["manifest_sha256"]]
        for more in also:
            argv += ["--also", more]
        if caps is not None:
            argv += ["--capabilities", self.capabilities(caps)]
        return self.run(*argv, **kw)

    def summon(self, command, name="demo", *more, **kw):
        argv = [command, "--name", name] + list(more)
        if kw.get("caps") is not None:
            argv += ["--capabilities", self.capabilities(kw.pop("caps"))]
        for other in kw.pop("also", ()):
            argv += ["--also", other]
        return self.run(*argv, **kw)

    def resume(self, name="demo", position=None, *more, **kw):
        if position is None:
            position = self.summon("status", name, **dict(kw)).doc.get("position")
        if not any(m in ("--done", "--leave", "--answer") for m in more):
            more = ("--word", "go on") + tuple(more)
        return self.summon("resume", name, "--position", position, *more, **kw)

    def started(self, name="demo", kind="sunrise", **kw):
        """A look and its go: (the look's result, the go's result)."""
        looked = self.look(name, kind, **kw)
        assert looked.doc and looked.doc.get("manifest_sha256"), looked.text
        return looked, self.go(looked, name, kind, **dict((k, v) for k, v in kw.items() if k in ("also", "caps", "kill", "env")))

    def capabilities(self, names):
        path = os.path.join(self.root, "capabilities-%s.json" % self.seed)
        with open(path, "w") as fh:
            json.dump({"capabilities": sorted(names)}, fh)
        return path

    # ---- the fakes' own records -----------------------------------------------------------------
    def fake(self, tool, name, default=None):
        path = os.path.join(self.home, ".fakes", tool, name)
        if not os.path.exists(path):
            return default
        with open(path) as fh:
            return json.load(fh) if name.endswith(".json") else [json.loads(line) for line in fh if line.strip()]

    def calls(self, tool="fakehost", command=None):
        found = self.fake(tool, "calls.jsonl", []) or []
        return [c for c in found if command is None or (c["argv"] and c["argv"][0] == command)]

    def plan_fake(self, tool, *entries):
        folder = os.path.join(self.home, ".fakes", tool)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "plan.json"), "w") as fh:
            json.dump(list(entries), fh)

    def set_fake(self, tool, **fields):
        folder = os.path.join(self.home, ".fakes", tool)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "state.json")
        state = self.fake(tool, "state.json") or {"account": "fixture-account", "things": {}, "refs": {}, "requests": {}}
        state.update(fields)
        with open(path, "w") as fh:
            json.dump(state, fh, indent=1, sort_keys=True)

    def statuses(self, run_id):
        """{operation: final status} as the journal has it, by the core's own reading of it."""
        out = {}
        for record in self.journal(run_id):
            if record["kind"] == "completion":
                out[record["op"]] = "done"
            elif record["kind"] == "status":
                out[record["op"]] = record["status"]
            elif record["kind"] == "attempt":
                out[record["op"]] = record["answer"]
        return out

    # ---- reading what the tool wrote ------------------------------------------------------------
    def open_runs(self):
        try:
            with open(self.facts.open_runs_file) as fh:
                return json.load(fh)["open"]
        except OSError:
            return {}

    def lock_names(self):
        try:
            return sorted(n for n in os.listdir(self.facts.locks_dir) if n.endswith(".lock"))
        except OSError:
            return []

    def run_ids(self):
        try:
            return sorted(os.listdir(self.facts.runs_root))
        except OSError:
            return []

    def journal(self, run_id):
        out = []
        try:
            with open(os.path.join(self.facts.run_dir(run_id), "journal.jsonl")) as fh:
                for line in fh:
                    if line.endswith("\n"):
                        out.append(json.loads(line))
        except OSError:
            pass
        return out

    def fingerprint(self, name):
        with open(self.facts.keying_file) as fh:
            return keys.fingerprint(fh.read().strip(), keys.fold(name))

    def hold_lock(self, name, run_id=""):
        """Another invocation holding the lock of `name`'s key: returns a closer."""
        import fcntl
        os.makedirs(self.facts.locks_dir, exist_ok=True)
        path = self.facts.lock_file(self.fingerprint(name))
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.ftruncate(fd, 0)
        os.pwrite(fd, json.dumps({"fingerprint": self.fingerprint(name), "run": run_id}).encode(), 0)

        def close():
            os.remove(path)
            os.close(fd)
        return close


class Case(unittest.TestCase):
    """A test case with one temporary directory, removed afterwards."""
    maxDiff = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sunv2-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def machine(self, name="home", seed="a"):
        return Machine(self.tmp, name, seed)

    def assertNowhere(self, needle, result, where=""):
        self.assertTrue(needle, "an empty needle proves nothing")
        self.assertNotIn(needle, result.out, "in standard output %s" % where)
        self.assertNotIn(needle, result.err, "in standard error %s" % where)


def canary(tag):
    """A marked canary, built at run time: never a literal a scanner would read as a key."""
    return "sunv2canary" + hashlib.sha256(("%s:%d" % (tag, os.getpid())).encode()).hexdigest()[:20]
