"""Shared generator library for the recheck-v2 fixture lanes (E7, lane contract section 5.8).

Standard library only, Python 3.9. Every lane's build.py locates this file relative to its own
__file__, constructs a Fixture per case, and ends with make_lane(). Git runs only inside the
throwaway repositories a Fixture creates under the output directory.

Encoding decisions this library fixes (lane contract 5.3, 5.5, 5.8; pilot contract 6 and 11):

- Git runs with GIT_CONFIG_NOSYSTEM=1, GIT_CONFIG_GLOBAL=/dev/null, a fixed author and
  committer, explicit dates per commit, and the config flags of 5.3, so two builds of one case
  produce identical commit hashes.
- identity(): commit = git rev-parse HEAD; dirty = git status --porcelain --untracked-files=all
  prints anything; tracked_diff_sha256 = SHA-256 of the exact bytes of git diff HEAD --binary;
  untracked = sorted git ls-files --others --exclude-standard; untracked_sha256 = SHA-256 of the
  concatenation of the sorted lines "<path>\\0<sha256 hex of content>", each terminated by "\\n";
  submodules = the paths git submodule status lists. The empty diff and the empty list hash the
  empty string. identity_of() runs git under the same clean configuration environment, so no
  user config can change the bytes it hashes.
- Checkpoint and receipt self = SHA-256 of canonical_json of the document with integrity.self
  removed; "<seq> <self>" is appended to the log before the rename of the document.
- tree_sha256(): SHA-256 over the sorted entries "<relative path>\\0<mode>\\0<sha256 of content>"
  joined with "\\n" and terminated by "\\n", for every file under the case directory except
  manifest.json and everything inside a .git directory or .git file (the index carries inode and
  mtime data and submodule clones record absolute paths; the commit hashes recorded in the
  manifest identity cover the history). The absolute output directory is replaced by the literal
  "<OUT>" in every file's content before hashing (5.5 names input.json; the substitution is a
  no-op for files that do not carry the path). Mode is the four-digit octal permission
  ("0644", "0755"); a symlink hashes its target string with mode "link".
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from typing import Callable, Dict, List, Optional

GIT_BASE_DATE = "2026-09-19T09:00:00-07:00"
GIT_FIX_DATE = "2026-09-20T09:00:00-07:00"
GIT_CONFIG_ARGS = [
    "-c", "core.hooksPath=/dev/null",
    "-c", "commit.gpgsign=false",
    "-c", "core.autocrlf=false",
    "-c", "core.fileMode=true",
    "-c", "protocol.file.allow=always",
]
SEP = " · "
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class GitMissing(RuntimeError):
    """Raised when no git executable is on PATH."""


class FixtureError(RuntimeError):
    """Raised for any other generator failure."""


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_env() -> Dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/"),
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "Fixture Author",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Fixture Author",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }
    return env


def _require_git() -> str:
    exe = shutil.which("git")
    if not exe:
        raise GitMissing("git is not on PATH; the fixture library needs git 2.x")
    return exe


def _git(cwd: str, args: List[str], when: Optional[str] = None, binary: bool = False):
    exe = _require_git()
    env = _git_env()
    if when is not None:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    proc = subprocess.run([exe] + GIT_CONFIG_ARGS + args, cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise FixtureError("git %s failed (%d): %s" % (" ".join(args), proc.returncode,
                                                       proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout if binary else proc.stdout.decode("utf-8")


def identity_of(workspace: str) -> dict:
    """The six-field fingerprint of pilot contract section 6."""
    commit = _git(workspace, ["rev-parse", "HEAD"]).strip()
    status = _git(workspace, ["status", "--porcelain", "--untracked-files=all"])
    diff = _git(workspace, ["diff", "HEAD", "--binary"], binary=True)
    raw = _git(workspace, ["ls-files", "--others", "--exclude-standard", "-z"], binary=True)
    untracked = sorted(p.decode("utf-8") for p in raw.split(b"\0") if p)
    lines = []
    for path in untracked:
        with open(os.path.join(workspace, path), "rb") as fh:
            lines.append(path + "\0" + sha256_hex(fh.read()) + "\n")
    lines.sort()
    submodules = []
    for line in _git(workspace, ["submodule", "status"]).splitlines():
        if line.strip():
            submodules.append(line[1:].split()[1])
    return {
        "commit": commit,
        "dirty": bool(status.strip()),
        "tracked_diff_sha256": sha256_hex(diff),
        "untracked": untracked,
        "untracked_sha256": sha256_hex("".join(lines).encode("utf-8")),
        "submodules": submodules,
    }


def _is_git_entry(name: str) -> bool:
    return name == ".git"


def tree_sha256(case_dir: str, out_dir: str) -> str:
    out_bytes = os.path.abspath(out_dir).encode("utf-8")
    entries = []
    for root, dirs, files in os.walk(case_dir):
        dirs[:] = sorted(d for d in dirs if not _is_git_entry(d))
        for name in sorted(files):
            if _is_git_entry(name):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, case_dir)
            if rel == "manifest.json":
                continue
            st = os.lstat(full)
            if os.path.islink(full):
                mode = "link"
                content = os.readlink(full).encode("utf-8")
            else:
                mode = "%04o" % (st.st_mode & 0o777)
                with open(full, "rb") as fh:
                    content = fh.read()
            if out_bytes and out_bytes in content:
                content = content.replace(out_bytes, b"<OUT>")
            entries.append(rel + "\0" + mode + "\0" + sha256_hex(content))
    entries.sort()
    return sha256_hex(("\n".join(entries) + "\n").encode("utf-8") if entries else b"")


def _next_hour(when: str) -> str:
    dt = datetime.datetime.fromisoformat(when)
    return (dt + datetime.timedelta(hours=1)).isoformat()


def opaque_case_name(case_id: str) -> str:
    """The opaque directory name for a case (ruling E7-18): 12 hex of SHA-256 over the case id."""
    return hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:12]


class Fixture:
    def __init__(self, out_dir: str, case_id: str, lane: str, checks: list, opaque: bool = False) -> None:
        _require_git()
        self.out_dir = os.path.abspath(out_dir)
        self.case_id = case_id
        self.lane = lane
        self.checks = list(checks)
        self.opaque = bool(opaque)
        # Ruling E7-18: with opaque=True the case directory is named by a digest of the case id so
        # no verifier-visible path names the lane or the case; workspace/ and run/ keep their names.
        self.case_dir = os.path.join(self.out_dir, opaque_case_name(case_id) if self.opaque else case_id)
        self.workspace = os.path.join(self.case_dir, "workspace")
        self.run_dir = os.path.join(self.case_dir, "run")
        self.sub_dir = os.path.join(self.case_dir, "_sub")
        self.last_when = None  # type: Optional[str]
        self._chains = {}  # type: Dict[str, dict]
        if os.path.lexists(self.case_dir):
            shutil.rmtree(self.case_dir)
        os.makedirs(self.workspace)
        os.makedirs(self.run_dir)
        _git(self.workspace, ["init", "-q", "-b", "main"])

    # ---- files -------------------------------------------------------------------------

    def _abs(self, rel_path: str) -> str:
        if os.path.isabs(rel_path) or rel_path.split("/")[0] == "..":
            raise FixtureError("workspace paths are relative and inside the workspace: %r" % rel_path)
        return os.path.join(self.workspace, rel_path)

    @staticmethod
    def _write_text(path: str, text: str, executable: bool = False) -> None:
        if not text.endswith("\n"):
            text += "\n"
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.chmod(path, 0o755 if executable else 0o644)

    def write(self, rel_path: str, text: str, executable: bool = False) -> None:
        self._write_text(self._abs(rel_path), text, executable)

    def write_bytes(self, rel_path: str, data: bytes) -> None:
        path = self._abs(rel_path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        os.chmod(path, 0o644)

    def remove(self, rel_path: str) -> None:
        path = self._abs(rel_path)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    def read(self, rel_path: str) -> str:
        with open(self._abs(rel_path), "r", encoding="utf-8") as fh:
            return fh.read()

    def skeleton(self, topic: str = "widget-export", date: str = "2026-09-18") -> None:
        self.write("README.md", "# widget\n\nA small export toolkit. The build plan lives at\n"
                   "docs/plans/%s-%s.md.\n\nRun modules from the repo root with PYTHONPATH=src.\n"
                   % (date, topic))
        self.write(".gitignore", "__pycache__/\n*.pyc\n.venv/\n")
        self.write("src/widget/__init__.py", '"""widget: a small export toolkit."""\n')

    # ---- build doc and ledger ----------------------------------------------------------

    def build_doc(self, topic: str, date: str, title: str, slices: list, prose: dict = None) -> str:
        prose = prose or {}
        rel = "docs/plans/%s-%s.md" % (date, topic)
        parts = ["# %s\n" % title]
        for s in slices:
            parts.append("\n## Slice %s — %s\nStatus: %s\n" % (s["name"], s["title"], s["status"]))
            text = prose.get(s["name"])
            if text:
                parts.append("\n" + text.rstrip("\n") + "\n")
        parts.append("\n## Punch list\n")
        self.write(rel, "".join(parts))
        return rel

    def _ledger_append(self, doc: str, text: str) -> None:
        """Insert text at the tail of the '## Punch list' section (or the file's end)."""
        if not text.endswith("\n"):
            text += "\n"
        content = self.read(doc)
        lines = content.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        home = None
        for i, line in enumerate(lines):
            if line.rstrip() == "## Punch list":
                home = i
                break
        nxt = None
        if home is not None:
            for j in range(home + 1, len(lines)):
                if lines[j].startswith("## "):
                    nxt = j
                    break
        if nxt is None:
            while lines and lines[-1].strip() == "":
                lines.pop()
            new = "\n".join(lines) + "\n" + text
        else:
            k = nxt
            while k > 0 and lines[k - 1].strip() == "":
                k -= 1
            head = "\n".join(lines[:k]) + "\n"
            tail = "\n".join(lines[nxt:]) + "\n"
            new = head + text + "\n" + tail
        self.write(doc, new)

    @staticmethod
    def _loc(file: str, line) -> str:
        return "%s:%s" % (file, line)

    def review_block(self, doc: str, date: str, slice_name: str, findings: list) -> None:
        rows = ["\n### %s — review: Slice %s" % (date, slice_name)]
        for f in findings:
            rows.append("- " + SEP.join([f["severity"], self._loc(f["file"], f["line"]), f["claim"],
                                         f["scenario"], f.get("found_by") or "Slice %s" % slice_name]))
        self._ledger_append(doc, "\n".join(rows) + "\n")

    def recheck_block(self, doc: str, date: str, slice_name: str, lines: list) -> None:
        rows = ["\n### %s — recheck: Slice %s" % (date, slice_name)]
        for l in lines:
            rows.append("- " + SEP.join([l["severity"], self._loc(l["file"], l["line"]),
                                         "(%s)" % l["claim"], l["disposition"], l["how"]]))
        self._ledger_append(doc, "\n".join(rows) + "\n")

    def waiver_line(self, doc: str, date: str, severity: str, file: str, line: int, claim: str,
                    words: str = None) -> None:
        fields = ["WAIVED (per user)", date, severity, self._loc(file, line), claim]
        if words is not None:
            fields.append('"%s"' % words.replace('"', "'"))
        self._ledger_append(doc, "- " + SEP.join(fields) + "\n")

    def reopen_line(self, doc: str, date: str, file: str, line: int, claim: str, words: str = None) -> None:
        fields = ["REOPENED (per user)", date, self._loc(file, line), claim]
        if words is not None:
            fields.append('"%s"' % words.replace('"', "'"))
        self._ledger_append(doc, "- " + SEP.join(fields) + "\n")

    def raw_ledger_line(self, doc: str, text: str) -> None:
        self._ledger_append(doc, text)

    def set_status(self, doc: str, slice_name: str, value: str) -> None:
        lines = self.read(doc).split("\n")
        heading = "## Slice %s —" % slice_name
        i = 0
        while i < len(lines) and not lines[i].startswith(heading):
            i += 1
        if i == len(lines):
            raise FixtureError("no heading for slice %r in %s" % (slice_name, doc))
        j = i + 1
        while j < len(lines) and not lines[j].startswith("## "):
            if lines[j].startswith("Status:"):
                lines[j] = "Status: %s" % value
                self.write(doc, "\n".join(lines))
                return
            j += 1
        raise FixtureError("no Status: line for slice %r in %s" % (slice_name, doc))

    def review_sheet(self, passes: dict, bar: list, checks: list) -> None:
        rows = ["# Review sheet", "", "## Passes"]
        for name, state in passes.items():
            if isinstance(state, bool):
                state = "on" if state else "off"
            rows.append("- %s: %s" % (name, state))
        rows += ["", "## Severity bar"] + ["- %s" % b for b in bar]
        rows += ["", "## Repo-specific checks"] + ["- %s" % c for c in checks]
        self.write("REVIEW.md", "\n".join(rows) + "\n")

    def verdict_doc(self, date: str, topic: str, slice_name: str, body: str) -> str:
        rel = "docs/reviews/%s-signoff-%s-%s.md" % (date, topic, slice_name.lower().replace(" ", "-"))
        self.write(rel, body)
        return rel

    # ---- git ---------------------------------------------------------------------------

    def commit(self, message: str, when: str) -> str:
        _git(self.workspace, ["add", "-A"])
        _git(self.workspace, ["commit", "-q", "--allow-empty", "-m", message], when=when)
        self.last_when = when
        return _git(self.workspace, ["rev-parse", "HEAD"]).strip()

    def next_when(self) -> str:
        return _next_hour(self.last_when or GIT_BASE_DATE)

    def stage(self, rel_path: str) -> None:
        _git(self.workspace, ["add", "--", rel_path])

    def untracked(self, rel_path: str, text: str) -> None:
        self.write(rel_path, text)

    def add_submodule(self, name: str) -> None:
        sub = os.path.join(self.sub_dir, name)
        os.makedirs(sub)
        _git(sub, ["init", "-q", "-b", "main"])
        self._write_text(os.path.join(sub, "README.md"), "# %s\n\nA vendored helper.\n" % name)
        self._write_text(os.path.join(sub, "%s.py" % name.replace("-", "_")),
                         "def version():\n    return \"0.1\"\n")
        _git(sub, ["add", "-A"])
        _git(sub, ["commit", "-q", "-m", "Initial %s" % name], when=GIT_BASE_DATE)
        _git(self.workspace, ["submodule", "-q", "add", "../_sub/%s" % name, name])
        self.commit("Add %s as a submodule" % name, self.next_when())

    def identity(self) -> dict:
        return identity_of(self.workspace)

    # ---- run directory -----------------------------------------------------------------

    def _run_abs(self, rel_path: str) -> str:
        return os.path.join(self.run_dir, rel_path)

    def write_input(self, doc: dict) -> None:
        inv = doc.setdefault("invocation", {})
        inv.setdefault("run_id", "%s-run" % self.case_id)
        inv.setdefault("run_dir", self.run_dir)
        doc.setdefault("workspace", self.workspace)
        self._write_json(os.path.join(self.case_dir, "input.json"), doc)

    @staticmethod
    def _write_json(path: str, doc) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        os.chmod(path, 0o644)

    def _signed_write(self, name: str, doc: dict, log: bool, seq: Optional[int],
                      prev: Optional[str], resign: bool) -> str:
        chain = self._chains.setdefault(name, {"seq": None, "self": None})
        integrity = dict(doc.get("integrity") or {})
        if resign:
            if seq is not None:
                integrity["seq"] = seq
            if prev is not None:
                integrity["prev"] = prev
            integrity.setdefault("prev", None)
            if "seq" not in integrity:
                raise FixtureError("resign needs an integrity.seq on the document or a seq argument")
        else:
            if seq is None:
                seq = 0 if chain["seq"] is None else chain["seq"] + 1
            integrity["seq"] = seq
            if prev is None:
                prev = chain["self"] if seq != 0 else None
            integrity["prev"] = prev
        integrity.pop("self", None)
        doc["integrity"] = integrity
        self_hash = sha256_hex(canonical_json(doc))
        doc["integrity"]["self"] = self_hash
        target = self._run_abs(name + ".json")
        if log and not resign:
            with open(self._run_abs(name + ".log"), "a", encoding="utf-8", newline="\n") as fh:
                fh.write("%d %s\n" % (integrity["seq"], self_hash))
        tmp = target + ".tmp"
        self._write_json(tmp, doc)
        os.replace(tmp, target)
        if not resign:
            chain["seq"] = integrity["seq"]
            chain["self"] = self_hash
        return self_hash

    def checkpoint(self, doc: dict, log: bool = True, seq: int = None, prev: str = None,
                   resign: bool = False) -> str:
        return self._signed_write("checkpoint", doc, log, seq, prev, resign)

    def receipt(self, doc: dict, log: bool = True, seq: int = None, prev: str = None) -> str:
        return self._signed_write("receipt", doc, log, seq, prev, False)

    def run_file(self, rel_path: str, text: str) -> None:
        self._write_text(self._run_abs(rel_path), text)

    def read_run_file(self, rel_path: str) -> str:
        with open(self._run_abs(rel_path), "r", encoding="utf-8") as fh:
            return fh.read()

    # ---- manifest ----------------------------------------------------------------------

    def manifest(self, input_validates: bool = True, tells_allowed: list = None,
                 trial_conditions: dict = None, notes: str = "") -> dict:
        doc = {
            "case": self.case_id,
            "lane": self.lane,
            "checks": list(self.checks),
            "workspace": "workspace",
            "run_dir": "run",
            "input": "input.json",
            "input_validates": bool(input_validates),
            "identity": self.identity(),
            "tree_sha256": tree_sha256(self.case_dir, self.out_dir),
            "tells_allowed": list(tells_allowed or []),
            "trial_conditions": dict(trial_conditions or {}),
            "notes": notes,
        }
        self._write_json(os.path.join(self.case_dir, "manifest.json"), doc)
        return doc


# ---- CLI ----------------------------------------------------------------------------------

def make_lane(lane: str, cases: Dict[str, Callable[[Fixture], None]], argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="build.py", description="Build the %s fixture cases." % lane)
    parser.add_argument("--out", metavar="DIR", help="output directory (created; existing case dirs are removed and rebuilt)")
    parser.add_argument("--case", metavar="ID", action="append", default=[], help="build only these cases (repeatable); unknown id: exit 2")
    parser.add_argument("--list", action="store_true", help="print case ids, one per line, and exit")
    parser.add_argument("--json", action="store_true", help="print a JSON summary to stdout instead of the human summary")
    parser.add_argument("--opaque", action="store_true", help="name each case directory by a digest of its case id (ruling E7-18); the summary carries the mapping")
    args = parser.parse_args(argv)

    if args.list:
        for cid in cases:
            print(cid)
        sys.exit(0)
    if not args.out:
        parser.error("--out DIR is required to build")
    unknown = [c for c in args.case if c not in cases]
    if unknown:
        sys.stderr.write("unknown case id(s): %s\n" % ", ".join(unknown))
        sys.exit(2)
    if not shutil.which("git"):
        sys.stderr.write("git is missing from PATH; the fixture library cannot build without it\n")
        sys.exit(3)
    selected = args.case or list(cases)
    os.makedirs(args.out, exist_ok=True)
    summary = []
    try:
        for cid in selected:
            # The builder receives a Fixture with checks=[]; it sets fx.checks before fx.manifest().
            # A builder that returns without writing manifest.json gets one written for it.
            fx = Fixture(args.out, cid, lane, [], opaque=args.opaque)
            cases[cid](fx)
            manifest_path = os.path.join(fx.case_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                fx.manifest()
            with open(manifest_path, "r", encoding="utf-8") as fh:
                m = json.load(fh)
            summary.append({"case": cid, "path": fx.case_dir, "tree_sha256": m["tree_sha256"], "opaque": args.opaque})
    except GitMissing as exc:
        sys.stderr.write("%s\n" % exc)
        sys.exit(3)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("%s: %s\n" % (type(exc).__name__, exc))
        sys.exit(1)
    if args.json:
        print(json.dumps({"lane": lane, "cases": summary}, indent=2))
    else:
        for row in summary:
            print("%s  %s  %s" % (row["case"], row["path"], row["tree_sha256"]))
    sys.exit(0)


def build_case(out_dir: str, case_id: str, lane: str, checks: list, builder: Callable[[Fixture], None], opaque: bool = False) -> dict:
    """Build one case outside the CLI and return its manifest (used by tests and runners)."""
    fx = Fixture(out_dir, case_id, lane, checks, opaque=opaque)
    builder(fx)
    path = os.path.join(fx.case_dir, "manifest.json")
    if not os.path.exists(path):
        return fx.manifest()
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
