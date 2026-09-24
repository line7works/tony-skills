"""E13 amendment A4: two recheck runs in a row on one document leave no phantom event.

CR-F2, measured by the control room on 2026-09-22: after ONE completed run, the next levelling
(`import-legacy`, which every phase runs before it reads records, CR-1) read the pilot's OWN
rendered recheck line and `Status:` line as news and appended a `disposition` with
`known: false` and a `card_observed`. `state` then reported `cleared_unbound: 1` beside
`fixed: 1` for a finding nothing but the pilot had ever cleared.

Nothing here changes what recheck decides, and nothing here touches `recheck.py` or
`recheck_core/`: the test drives the real CLI twice and reads the log back through the records
component's own CLI.

The case is `S1-colocated/S1-01-two-claims-one-location`, the one E7 case whose slice carries two
open items at one location. Run 1 clears one and leaves the other `not_fixed`, so run 2 has
something open to start on and its `record` phase syncs a document that already holds run 1's
rendered block.
"""
import json
import os
import subprocess
import unittest

import testlib

DOC = "docs/plans/2026-09-18-widget-export.md"
LOG = "docs/records/docs__plans__2026-09-18-widget-export.events.jsonl"
RECORDS = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir, "records"))
RECORDS_CLI = os.path.join(RECORDS, "scripts", "records.py")


class TwoRunsInARow(unittest.TestCase):
    LANE = "S1-colocated"
    CASE = "S1-01-two-claims-one-location"

    def setUp(self):
        self.dir = testlib.make_scratch("e13-a4-two-runs-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case(self.LANE, self.CASE, self.dir)
        self.workspace = os.path.join(self.case, "workspace")

    # ---- the records component, run directly ------------------------------------------------

    def records(self, *args):
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run([testlib.GEN_PYTHON, RECORDS_CLI] + list(args),
                              cwd=self.dir, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace")
        try:
            body = json.loads(out) if out.strip() else None
        except ValueError:
            body = {"_raw": out}
        return proc.returncode, body, proc.stderr.decode("utf-8", "replace")

    def log_events(self):
        path = os.path.join(self.workspace, LOG)
        if not os.path.isfile(path):
            return []
        with open(path, "r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def status_text(self):
        with open(os.path.join(self.workspace, DOC), "r", encoding="utf-8") as fh:
            for line in fh.read().split("\n"):
                if line.startswith("Status:"):
                    return line[len("Status:"):].strip()
        return None

    # ---- one recheck run, through the real CLI -----------------------------------------------

    def run_once(self, suffix, dispositions):
        run_dir = os.path.join(self.case, "run" + suffix)
        if not os.path.isdir(run_dir):
            os.makedirs(run_dir)

        def mutate(doc):
            doc["invocation"]["run_id"] = doc["invocation"]["run_id"] + suffix
            doc["invocation"]["run_dir"] = run_dir

        path = testlib.prepare_input(self.case, mutate=mutate,
                                     path=os.path.join(self.case, "input%s.json" % suffix))
        code, doc, err = testlib.recheck(["start", path], cwd=self.dir)
        self.assertEqual(code, 0, err)
        items = []
        for i, item in enumerate(doc["checklist"]):
            disposition = dispositions[i % len(dispositions)]
            row = {"index": i, "disposition": disposition, "method": "executed",
                   "location": "%s:%s" % (item["location"]["file"], item["location"]["line"])}
            if disposition == "not_fixed":
                row["reason"] = "reproduces"
            items.append(row)
        testlib.write_report(run_dir, testlib.canned_report(items))
        code, _, err = testlib.recheck(
            ["record-call", "--run-dir", run_dir, "--call-id", doc["call_id"], "--status", "ok",
             "--raw", os.path.join(run_dir, "verifier", "raw.md"), "--kind", "subagent",
             "--model", "claude-fable-5-1"], cwd=self.dir)
        self.assertEqual(code, 0, err)
        for i in range(len(items)):
            code, _, err = testlib.recheck(
                ["adjudicate", "--run-dir", run_dir, "--item", str(i), "--action", "confirmed"],
                cwd=self.dir)
            self.assertEqual(code, 0, err)
        code, result, err = testlib.recheck(["record", "--run-dir", run_dir], cwd=self.dir)
        # every terminal result of the pilot exits 10 (`EXIT_TERMINAL`), success included
        self.assertEqual(code, 10, err)
        return result, len(items)

    def rendered_line_count(self):
        """How many lines of the document the component itself rendered: every native run's
        block and grant lines, plus the `Status:` line when a native `card_set` moved it."""
        events = self.log_events()
        runs, imports = [], set()
        for event in events:
            run_id = (event.get("actor") or {}).get("run_id")
            if not run_id:
                continue
            if (event.get("origin") or {}).get("kind") == "legacy":
                # an import pass: its brackets are native, its records came FROM the document
                imports.add(run_id)
            elif run_id not in runs:
                runs.append(run_id)
        runs = [r for r in runs if r not in imports]
        total = 0
        for run_id in runs:
            code, body, err = self.records("render", "--workspace", self.workspace,
                                           "--doc", DOC, "--run-id", run_id)
            self.assertEqual(code, 0, err)
            total += len(body["lines"]) + len(body["grants"]) + len(body["review_lines"])
        cards = {}
        for event in events:
            if event.get("kind") == "card_set" and (event.get("origin") or {}).get("kind") != "legacy":
                cards[event.get("slice")] = event.get("after")
        if self.status_text() in cards.values():
            total += 1
        return total

    def test_the_second_run_finds_no_phantom_event(self):
        first, first_items = self.run_once("-1", ["fixed", "not_fixed"])
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first_items, 2, "this case is the two-item one")
        cleared = [e for e in self.log_events()
                   if e["kind"] == "disposition" and e.get("disposition") == "fixed"]
        self.assertEqual(len(cleared), 1)
        finding = cleared[0]["finding"]

        second, second_items = self.run_once("-2", ["fixed"])
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second_items, 1, "run 2 starts on the item run 1 left open")

        events = self.log_events()
        unbound = [e for e in events
                   if e["kind"] == "disposition" and e.get("finding") == finding
                   and not ((e.get("verified_source") or {}).get("known") is True)]
        self.assertEqual(unbound, [], "a phantom clear was imported from the pilot's own line")

        code, state, err = self.records("state", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 0, err)
        self.assertEqual(state["counts"]["cleared_unbound"], 0)

        code, report, err = self.records("import-legacy", "--workspace", self.workspace,
                                         "--doc", DOC, "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertEqual(report["would_import"], 0)
        self.assertEqual(report["native_rendered"], self.rendered_line_count())
        self.assertGreater(report["native_rendered"], 0)


if __name__ == "__main__":
    unittest.main()
