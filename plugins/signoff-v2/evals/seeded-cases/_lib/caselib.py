"""Shared generator library for the E13 seeded-case families (lane contract section 12).

Trimmed from the recheck-v2 pilot's `evals/fixtures/_lib/fixturelib.py` (same repository, same
owner). Standard library only, Python 3.9. Every family's build.py locates this file relative to
its own __file__, constructs a Case per case id, and ends with make_family().

Encoding decisions this library fixes, so two builds of one case are byte-identical:

- Git runs with GIT_CONFIG_NOSYSTEM=1, GIT_CONFIG_GLOBAL=/dev/null, a fixed author and
  committer, an explicit date per commit, and fixed config flags, so commit hashes repeat.
- tree_sha256(): SHA-256 over the sorted entries "<relative path>\\0<mode>\\0<sha256 of content>"
  joined with "\\n" and terminated by "\\n", for every file under the case directory except
  manifest.json and everything inside .git. The absolute output directory is replaced by the
  literal "<OUT>" in every file's content before hashing, so a case built into two directories
  hashes the same. Mode is the four-digit octal permission; a symlink hashes its target with
  mode "link".
- Nothing here reads the clock, the environment beyond PATH and HOME, or any file outside the
  output directory and the family's own answers/ directory.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from typing import Callable, Dict, List, Optional

sys.dont_write_bytecode = True

GIT_BASE_DATE = "2026-09-19T09:00:00-07:00"
GIT_WORK_DATE = "2026-09-20T09:00:00-07:00"
GIT_CONFIG_ARGS = [
    "-c", "core.hooksPath=/dev/null",
    "-c", "commit.gpgsign=false",
    "-c", "core.autocrlf=false",
    "-c", "core.fileMode=true",
]


class GitMissing(RuntimeError):
    """Raised when no git executable is on PATH."""


class CaseError(RuntimeError):
    """Raised for any other generator failure."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_env() -> Dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/"),
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "Case Author",
        "GIT_AUTHOR_EMAIL": "case@example.invalid",
        "GIT_COMMITTER_NAME": "Case Author",
        "GIT_COMMITTER_EMAIL": "case@example.invalid",
    }


def _require_git() -> str:
    exe = shutil.which("git")
    if not exe:
        raise GitMissing("git is not on PATH; the case library needs git 2.x")
    return exe


def _git(cwd: str, args: List[str], when: Optional[str] = None) -> str:
    exe = _require_git()
    env = _git_env()
    if when is not None:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    proc = subprocess.run([exe] + GIT_CONFIG_ARGS + args, cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise CaseError("git %s failed (%d): %s" % (
            " ".join(args), proc.returncode, proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8")


def tree_sha256(case_dir: str, out_dir: str) -> str:
    out_bytes = os.path.abspath(out_dir).encode("utf-8")
    entries = []
    for root, dirs, files in os.walk(case_dir):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            if name == ".git":
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


class Case:
    """One seeded case: a git-backed workspace, an input, and an optional recorded answer."""

    def __init__(self, out_dir: str, case_id: str, family: str, answers_dir: str) -> None:
        _require_git()
        self.out_dir = os.path.abspath(out_dir)
        self.case_id = case_id
        self.family = family
        self.answers_dir = answers_dir
        self.case_dir = os.path.join(self.out_dir, case_id)
        self.workspace = os.path.join(self.case_dir, "workspace")
        self.run_dir = os.path.join(self.case_dir, "run")
        self.notes = ""
        if os.path.lexists(self.case_dir):
            shutil.rmtree(self.case_dir)
        os.makedirs(self.workspace)
        os.makedirs(self.run_dir)
        _git(self.workspace, ["init", "-q", "-b", "main"])

    # ---- files -------------------------------------------------------------------------

    def _abs(self, rel_path: str) -> str:
        if os.path.isabs(rel_path) or rel_path.split("/")[0] == "..":
            raise CaseError("workspace paths are relative and inside the workspace: %r" % rel_path)
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

    def read(self, rel_path: str) -> str:
        with open(self._abs(rel_path), "r", encoding="utf-8") as fh:
            return fh.read()

    def remove(self, rel_path: str) -> None:
        os.remove(self._abs(rel_path))

    # ---- build doc ---------------------------------------------------------------------

    def build_doc(self, rel_path: str, title: str, slices: List[dict],
                  sections: Optional[List[str]] = None) -> str:
        """Write a build doc. Each slice dict takes name, title, status, and optional
        footprint / requirements / checks / not_in_slice lists."""
        parts = ["# %s\n" % title]
        for s in slices:
            parts.append("\n## Slice %s — %s\nStatus: %s\n" % (s["name"], s["title"], s["status"]))
            if s.get("intent"):
                parts.append("\n%s\n" % s["intent"].rstrip("\n"))
            for label, key in (("Footprint", "footprint"), ("Requirements", "requirements"),
                               ("Checks", "checks"), ("Not in this slice", "not_in_slice")):
                rows = s.get(key)
                if rows:
                    parts.append("\n%s:\n" % label)
                    for row in rows:
                        parts.append("- %s\n" % row)
        for extra in (sections or []):
            parts.append("\n" + extra.rstrip("\n") + "\n")
        parts.append("\n## Punch list\n")
        self.write(rel_path, "".join(parts))
        return rel_path

    def set_status(self, doc: str, slice_name: str, value: str) -> None:
        lines = self.read(doc).split("\n")
        heading = "## Slice %s —" % slice_name
        i = 0
        while i < len(lines) and not lines[i].startswith(heading):
            i += 1
        if i == len(lines):
            raise CaseError("no heading for slice %r in %s" % (slice_name, doc))
        j = i + 1
        while j < len(lines) and not lines[j].startswith("## "):
            if lines[j].startswith("Status:"):
                lines[j] = "Status: %s" % value
                self.write(doc, "\n".join(lines))
                return
            j += 1
        raise CaseError("no Status: line for slice %r in %s" % (slice_name, doc))

    # ---- git ---------------------------------------------------------------------------

    def commit(self, message: str, when: str = GIT_BASE_DATE) -> str:
        _git(self.workspace, ["add", "-A"])
        _git(self.workspace, ["commit", "-q", "--allow-empty", "-m", message], when=when)
        return _git(self.workspace, ["rev-parse", "HEAD"]).strip()

    def tag(self, name: str) -> None:
        _git(self.workspace, ["tag", name])

    def stage(self, rel_path: str) -> None:
        _git(self.workspace, ["add", "--", rel_path])

    def head(self) -> str:
        return _git(self.workspace, ["rev-parse", "HEAD"]).strip()

    def porcelain(self) -> str:
        return _git(self.workspace, ["status", "--porcelain", "--untracked-files=all"])

    # ---- input, answer, manifest -------------------------------------------------------

    @staticmethod
    def _write_json(path: str, doc) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        os.chmod(path, 0o644)

    def write_input(self, doc: dict) -> None:
        doc = dict(doc)
        doc.setdefault("seeded_input", 1)
        doc.setdefault("case", self.case_id)
        doc.setdefault("workspace", self.workspace)
        doc.setdefault("run_dir", self.run_dir)
        doc.setdefault("report_only", False)
        self._write_json(os.path.join(self.case_dir, "input.json"), doc)

    def copy_answer(self) -> Optional[str]:
        """Copy answers/<case id>.json, when the family ships one, to <case dir>/answer.json."""
        src = os.path.join(self.answers_dir, self.case_id + ".json")
        if not os.path.exists(src):
            return None
        with open(src, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if doc.get("case") != self.case_id:
            raise CaseError("answers/%s.json names case %r" % (self.case_id, doc.get("case")))
        self._write_json(os.path.join(self.case_dir, "answer.json"), doc)
        return "answer.json"

    def manifest(self, notes: str = "") -> dict:
        answer = self.copy_answer()
        doc = {
            "case": self.case_id,
            "family": self.family,
            "workspace": "workspace",
            "run_dir": "run",
            "input": "input.json",
            "answer": answer,
            "head": self.head(),
            "notes": notes or self.notes,
            "tree_sha256": "",
        }
        # tree_sha256 covers every file except manifest.json itself, so it is computed last.
        doc["tree_sha256"] = tree_sha256(self.case_dir, self.out_dir)
        self._write_json(os.path.join(self.case_dir, "manifest.json"), doc)
        return doc


# ---- CLI ----------------------------------------------------------------------------------

def make_family(family: str, cases: Dict[str, Callable[[Case], None]],
                argv: Optional[List[str]] = None) -> None:
    here = os.path.dirname(os.path.abspath(sys.argv[0] if argv is None else sys.argv[0]))
    answers_dir = os.path.join(here, "answers")
    parser = argparse.ArgumentParser(prog="build.py",
                                     description="Build the %s seeded cases." % family)
    parser.add_argument("--out", metavar="DIR",
                        help="output directory (created; existing case dirs are rebuilt)")
    parser.add_argument("--case", metavar="ID", action="append", default=[],
                        help="build only these cases (repeatable); an unknown id exits 2")
    parser.add_argument("--list", action="store_true", help="print case ids, one per line")
    parser.add_argument("--json", action="store_true", help="print a JSON summary on stdout")
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
        sys.stderr.write("git is missing from PATH; the case library cannot build without it\n")
        sys.exit(3)
    selected = args.case or list(cases)
    os.makedirs(args.out, exist_ok=True)
    summary = []
    try:
        for cid in selected:
            case = Case(args.out, cid, family, answers_dir)
            cases[cid](case)
            path = os.path.join(case.case_dir, "manifest.json")
            if not os.path.exists(path):
                case.manifest()
            with open(path, "r", encoding="utf-8") as fh:
                m = json.load(fh)
            summary.append({"case": cid, "path": case.case_dir,
                            "tree_sha256": m["tree_sha256"], "head": m["head"]})
    except GitMissing as exc:
        sys.stderr.write("%s\n" % exc)
        sys.exit(3)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("%s: %s\n" % (type(exc).__name__, exc))
        sys.exit(1)
    if args.json:
        print(json.dumps({"family": family, "cases": summary}, indent=2, sort_keys=True))
    else:
        for row in summary:
            print("%s  %s  %s" % (row["case"], row["tree_sha256"], row["head"]))
    sys.exit(0)
