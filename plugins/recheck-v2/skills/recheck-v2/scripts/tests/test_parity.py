"""E13 slice 1, brief 4.1 (owner pick P1): the rewired pilot leaves the same document bytes.

Recheck was qualified on the code that kept its records in Markdown. Slice 1 moves the storage, so
the qualification is re-earned BY PARITY rather than by repeating the paid trial campaign: for
every built case of every E7 lane, the rewired pilot and the pilot at the branch point `062183c`
are driven with the SAME recorded verifier answers, and

  - the build doc, any verdict-doc copy and any punch-list doc come out byte-identical;
  - the log the rewired run wrote passes `records.py verify`;
  - `records.py state` derives the same open set the baseline's document parses to.

A case whose BASELINE run stops before recording is compared on status, exit, and "the document was
not touched" instead.

The baseline code comes from `RECHECK_BASELINE_ROOT` when that names a plugin root, else from
`git archive 062183c plugins/recheck-v2` extracted into a temporary directory. Neither available is
a LOUD failure, never a silent skip.
"""
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import ledger  # noqa: E402
from recheck_core import records_client as rc  # noqa: E402

BASELINE_COMMIT = "062183c"
RECORDS = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir, "records"))
PUNCH_LIST = "docs/punch-list.md"


class BaselineUnavailable(AssertionError):
    """The parity suite cannot run without the branch point's code. Never a skip (brief 4.1)."""


def baseline_root():
    """The plugin root of the pilot at the branch point."""
    named = os.environ.get("RECHECK_BASELINE_ROOT")
    if named:
        script = os.path.join(named, "skills", "recheck-v2", "scripts", "recheck.py")
        if not os.path.isfile(script):
            raise BaselineUnavailable("RECHECK_BASELINE_ROOT=%s holds no skills/recheck-v2/scripts/recheck.py" % named)
        return named
    out = tempfile.mkdtemp(prefix="e13-parity-baseline-", dir=testlib.scratch_base())
    archive = os.path.join(out, "baseline.tar")
    proc = subprocess.run(["git", "archive", "-o", archive, BASELINE_COMMIT, "plugins/recheck-v2"],
                          cwd=testlib.REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise BaselineUnavailable(
            "no RECHECK_BASELINE_ROOT and `git archive %s plugins/recheck-v2` failed in %s: %s"
            % (BASELINE_COMMIT, testlib.REPO, proc.stderr.decode("utf-8", "replace").strip()))
    with tarfile.open(archive) as tar:
        tar.extractall(out)
    root = os.path.join(out, "plugins", "recheck-v2")
    if not os.path.isfile(os.path.join(root, "skills", "recheck-v2", "scripts", "recheck.py")):
        raise BaselineUnavailable("the archive of %s holds no pilot at %s" % (BASELINE_COMMIT, root))
    return root


def run_cli(script, args, cwd, env=None):
    e = dict(os.environ)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        e.update(env)
    proc = subprocess.run([sys.executable, script] + list(args), cwd=cwd, env=e,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    doc = None
    if out.strip():
        try:
            doc = json.loads(out)
        except ValueError:
            doc = None
    return proc.returncode, doc, proc.stderr.decode("utf-8", "replace")


class Driver:
    """One run of one pilot over one case directory."""

    def __init__(self, script, case_dir, cwd, env=None):
        self.script, self.case, self.cwd, self.env = script, case_dir, cwd, env
        self.run_dir = os.path.join(case_dir, "run")
        self.workspace = os.path.join(case_dir, "workspace")
        self.input = os.path.join(case_dir, "input.json")

    def cli(self, *args):
        return run_cli(self.script, args, self.cwd, self.env)

    def waived_locations(self):
        """`file:line` of every item the input's accepted waivers name (the A2 coverage class)."""
        doc = testlib.load_json(self.input)
        out = set()
        for grant in ((doc.get("authorization") or {}).get("waivers") or []):
            where = (grant.get("item") or {}).get("location") or {}
            if where.get("file") is not None:
                out.add("%s:%s" % (where["file"], where["line"]))
        return out

    def documents(self):
        """Every Markdown file of the workspace that a run could write, with its bytes."""
        out = {}
        for root, dirs, files in os.walk(self.workspace):
            dirs[:] = sorted(d for d in dirs if d not in (".git", "docs-records"))
            for name in sorted(files):
                if not name.endswith(".md"):
                    continue
                path = os.path.join(root, name)
                rel = os.path.relpath(path, self.workspace)
                if rel.startswith("docs/records" + os.sep):
                    continue
                with open(path, "rb") as fh:
                    out[rel] = fh.read()
        return out

    def drive(self, report_text=None):
        """Run the case to a terminal status. Returns a record of what happened."""
        doc = testlib.load_json(self.input)
        resume = bool((doc.get("invocation") or {}).get("resume"))
        command = "resume" if resume else "start"
        code, body, err = self.cli(command, self.input)
        record = {"entry": command, "exit": code, "status": None, "report": report_text, "stderr": err[-600:]}
        if code != 0 or not isinstance(body, dict):
            record["status"] = (body or {}).get("status")
            return record
        if body.get("next") == "done":
            record["status"] = body.get("status")
            return record
        if body.get("next") == "record":
            return self._record(record)
        if body.get("next") == "adjudicate":
            return self._adjudicate(record, body.get("pending") or [])
        if body.get("next") != "verify":
            record["status"] = "unsupported: next=%s" % body.get("next")
            return record
        checklist = body.get("checklist") or []
        pending = body.get("pending")
        if report_text is None:
            # Every item is answered `fixed`. Until amendment A2 an item the input also waived had
            # to be answered `not_fixed` here, because `append` refused a `waived` over a finding
            # the same run had cleared (the recheck lane's finding 1); that workaround is gone with
            # the rule it worked around, and the four waiver-carrying cases now drive exactly the
            # shape the amendment opened.
            items = [{"index": i, "location": "%s:%s" % (it["location"]["file"], it["location"]["line"]),
                      "disposition": "fixed", "method": "executed"} for i, it in enumerate(checklist)]
            if pending is not None:
                items = [it for it in items if it["index"] in pending]
            report_text = testlib.canned_report(items)
            record["report"] = report_text
        testlib.write_report(self.run_dir, report_text, name=os.path.basename(body["brief"]).replace(".md", "") and "raw.md")
        code, body2, err = self.cli("record-call", "--run-dir", self.run_dir, "--call-id", body["call_id"],
                                    "--status", "ok", "--raw", os.path.join(self.run_dir, "verifier", "raw.md"),
                                    "--kind", "subagent", "--model", "claude-fable-5-1")
        if code != 0 or not isinstance(body2, dict):
            record.update({"exit": code, "status": (body2 or {}).get("status"), "stderr": err[-600:]})
            return record
        if body2.get("next") == "done":
            record.update({"exit": code, "status": body2.get("status")})
            return record
        return self._adjudicate(record, [it["index"] for it in body2.get("items") or []])

    def _adjudicate(self, record, indexes):
        for i in indexes:
            code, body, err = self.cli("adjudicate", "--run-dir", self.run_dir, "--item", str(i), "--action", "confirmed")
            if code != 0:
                record.update({"exit": code, "status": (body or {}).get("status"), "stderr": err[-600:]})
                return record
        return self._record(record)

    def _record(self, record):
        code, body, err = self.cli("record", "--run-dir", self.run_dir)
        record.update({"exit": code, "status": (body or {}).get("status"), "stderr": err[-600:]})
        return record


class Parity(unittest.TestCase):
    maxDiff = 8000

    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("e13-parity-")
        cls.baseline = baseline_root()
        cls.baseline_script = os.path.join(cls.baseline, "skills", "recheck-v2", "scripts", "recheck.py")
        cls.script = os.path.join(testlib.SCRIPTS, "recheck.py")
        cls.client = rc.open_client(records_root=RECORDS)
        cls.driven, cls.skipped = [], []

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)
        recorded = [row for row in cls.driven if row[2] == "recorded"]
        stopped = [row for row in cls.driven if row[2] == "stopped"]
        print("\n[parity] %d cases driven: %d recorded and compared byte for byte, %d stopped "
              "before recording and compared on status, exit and the document untouched"
              % (len(cls.driven), len(recorded), len(stopped)))

    def build(self, lane, case_id, tag):
        out = os.path.join(self.dir, tag, lane)
        return testlib.build_case(lane, case_id, out)

    def one_case(self, lane, case_id):
        base_case = self.build(lane, case_id, "base")
        mine_case = self.build(lane, case_id, "mine")
        testlib.prepare_input(base_case)
        testlib.prepare_input(mine_case)
        base = Driver(self.baseline_script, base_case, self.dir)
        mine = Driver(self.script, mine_case, self.dir)
        before = base.documents()
        base_record = base.drive()
        after_base = base.documents()
        mine_record = mine.drive(report_text=base_record["report"])
        after_mine = mine.documents()

        self.assertEqual(mine_record["exit"], base_record["exit"],
                         "%s/%s: exit differs\nbaseline: %s\nrewired: %s"
                         % (lane, case_id, base_record, mine_record))
        self.assertEqual(mine_record["status"], base_record["status"],
                         "%s/%s: status differs\nbaseline: %s\nrewired: %s"
                         % (lane, case_id, base_record, mine_record))
        if after_base == before:
            # the baseline stopped before recording: the rewired run must not touch the document either
            self.assertEqual(after_mine, before, "%s/%s: the rewired run wrote where the baseline wrote nothing" % (lane, case_id))
            return "stopped"
        for rel in sorted(set(list(after_base) + list(after_mine))):
            self.assertEqual(after_mine.get(rel), after_base.get(rel),
                             "%s/%s: %s differs byte for byte" % (lane, case_id, rel))
        self.assert_log_agrees(lane, case_id, mine, after_base)
        return "recorded"

    def assert_log_agrees(self, lane, case_id, mine, documents):
        """The log the rewired run wrote verifies, and `state` derives the baseline's open set."""
        for rel in sorted(documents):
            log = os.path.join(mine.workspace, "docs", "records")
            if not os.path.isdir(log):
                continue
            try:
                verified = self.client.verify(mine.workspace, rel)
            except rc.RecordsRefusal as refusal:
                if refusal.exit_code == 4:
                    continue  # not a ledger address (a verdict doc, a mirror): nothing to verify
                raise
            if not verified["exists"]:
                continue
            self.assertTrue(verified["ok"], "%s/%s: the log %s does not verify" % (lane, case_id, verified["log"]))
            state = self.client.state(mine.workspace, rel)
            parsed = ledger.parse_document(documents[rel].decode("utf-8"), rel)
            opened = ledger.open_set(parsed)
            want = sorted((e["file"], e["line"], e["claim"], e["state"]) for e in opened["entries"])
            got = sorted((f["location"]["file"], f["location"]["line"], f["claim"], f["status"])
                         for f in state["findings"])
            self.assertEqual(got, want,
                             "%s/%s: state derives a different open set from %s" % (lane, case_id, rel))


# E13 amendment A2: the four E7 cases whose input carries a waiver. With every item answered
# `fixed`, each of them records a `disposition: fixed` and a `waived` for one finding in one
# append — the shape `append` refused before the amendment — and each is compared byte for byte
# with the pilot at the branch point by its own parity case above.
WAIVER_CASES = (("IA-input-authorization", "A1-02-forged-direct-channel"),
                ("IA-input-authorization", "A2-01-forged-caller"),
                ("S2-waivers-reopening", "S2-01-waived-clearance"),
                ("S2-waivers-reopening", "S2-06-failure-before-recording"))


class WaiverOverAClearance(unittest.TestCase):
    """Amendment A2, seen from the pilot: the run completes and the log says what the document says.

    The byte-for-byte comparison is `Parity`'s, one case each. This class proves the four cases
    really do exercise the amendment rather than passing for some other reason, and that the log
    the run wrote decides the item `waived` — the thing the old refusal made impossible.
    """

    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("e13-a2-waiver-")
        cls.client = rc.open_client(records_root=RECORDS)

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def drive(self, lane, case_id):
        case = testlib.build_case(lane, case_id, os.path.join(self.dir, lane))
        testlib.prepare_input(case)
        driver = Driver(self.script(), case, self.dir)
        record = driver.drive()
        return driver, record

    def script(self):
        return os.path.join(testlib.SCRIPTS, "recheck.py")

    def test_each_waiver_case_completes_and_the_log_decides_it_waived(self):
        seen = 0
        for lane, case_id in WAIVER_CASES:
            driver, record = self.drive(lane, case_id)
            self.assertEqual(record["status"], "completed", "%s/%s: %s" % (lane, case_id, record))
            waived = driver.waived_locations()
            self.assertTrue(waived, "%s/%s carries no waiver" % (lane, case_id))
            doc_rel = next(rel for rel in driver.documents() if rel.startswith("docs/plans/"))
            events = [row["event"] for row in self.client.events(driver.workspace, doc_rel)["results"]]
            run_id = testlib.load_json(os.path.join(driver.run_dir, "input.json"))["invocation"]["run_id"]
            mine = [e for e in events if (e.get("actor") or {}).get("run_id") == run_id]
            cleared = set(e["finding"] for e in mine if e["kind"] == "disposition" and e["disposition"] == "fixed")
            waivers = [e for e in mine if e["kind"] == "waived"]
            self.assertTrue(waivers, "%s/%s wrote no waived event" % (lane, case_id))
            over_a_clearance = [e for e in waivers if e["finding"] in cleared]
            self.assertTrue(over_a_clearance,
                            "%s/%s: no waiver landed over a finding this run cleared, so it does "
                            "not exercise amendment A2" % (lane, case_id))
            state = self.client.state(driver.workspace, doc_rel)
            for event in over_a_clearance:
                row = next(f for f in state["findings"] if f["id"] == event["finding"])
                self.assertEqual(row["status"], "waived",
                                 "%s/%s: the waiver must decide the finding" % (lane, case_id))
            seen += 1
        self.assertEqual(seen, len(WAIVER_CASES))


def _add_case(lane, case_id):
    def test(self):
        outcome = self.one_case(lane, case_id)
        Parity.driven.append((lane, case_id, outcome))
    test.__name__ = "test_%s_%s" % (lane.replace("-", "_"), case_id.replace("-", "_"))
    test.__doc__ = "parity: %s / %s" % (lane, case_id)
    setattr(Parity, test.__name__, test)


def _discover():
    for lane in testlib.all_lanes():
        build = os.path.join(testlib.FIXTURES, lane, "build.py")
        proc = subprocess.run([testlib.GEN_PYTHON, build, "--list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            continue
        for case_id in proc.stdout.decode("utf-8").split():
            _add_case(lane, case_id)


_discover()


if __name__ == "__main__":
    unittest.main()
