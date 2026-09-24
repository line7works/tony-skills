"""E13 slice 2, the last fix round, Astra's N1 in the pilot: a native ranged review passes recheck.

Records keeps a ranged location on the review line it renders (amendment A7, F9). The pilot's
strict Appendix A check (`inputs.strict_ambiguities`) read that NATIVE line with the legacy
grammar, which has no range, and stopped `start` with `missing_input` ("second field
'src/widget.py:2-3' is not a file:line location"). Astra's `probe_fix_edges.py`: `next recheck:
missing_input`.

The pilot now asks the records CLI which record lines the component itself rendered (`events`,
`render --run-id`, and the dry run's `native_rendered`), consumes each native occurrence once,
and applies the UNCHANGED Appendix A stop to the hand-written records that remain. E13-1 holds: a
hand-written ranged line stops exactly as at the baseline, and so does a second copy of a
rendered one. Every event is appended and rendered through the real records CLI.
"""
import json
import os
import unittest

import testlib
from test_native_raise_address import Base, DOC, NATIVE_CLAIM, NATIVE_RUN

RANGED_RAW = "src/widget/export.py:31-32"


class N1ANativeRangedReviewPassesTheNextRecheck(Base):

    def raise_native_ranged(self):
        self.records("import-legacy", "--workspace", self.workspace, "--doc", DOC)
        head = self.records("state", "--workspace", self.workspace, "--doc", DOC)["head"]
        identity = self.records("identity", "--workspace", self.workspace)["identity"]
        event = {"v": 1, "kind": "finding_raised", "at": "2026-09-21T10:00:00Z", "ledger_doc": DOC,
                 "actor": {"station": "signoff-v2", "run_id": NATIVE_RUN, "harness": "claude-code"},
                 "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
                 "slice": "A", "severity": "MAJOR",
                 "location": {"raw": RANGED_RAW, "file": "src/widget/export.py", "line": 31,
                              "line_end": 32, "tag": None, "more": [], "resolved": True},
                 "claim": NATIVE_CLAIM,
                 "scenario": "run the exporter twice and read the file; two header lines",
                 "raised_by": "independent reviewer"}
        path = os.path.join(self.dir, "native-events.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([event], fh)
        self.records("append", "--workspace", self.workspace, "--doc", DOC, "--events", path,
                     "--expect-head", head)
        return self.records("render", "--workspace", self.workspace, "--doc", DOC,
                            "--run-id", NATIVE_RUN)

    def test_start_proceeds_over_the_rendered_ranged_line(self):
        rendered = self.raise_native_ranged()
        self.assertIn(RANGED_RAW, rendered["review_lines"][0])
        self.place(rendered["review"])
        code, doc, err = self.start()
        self.assertEqual(code, 0, "%s\n%s" % (err, doc))
        self.assertEqual(doc["next"], "verify", doc)
        checklist = self.checkpoint()["scope"]["checklist"]
        native = self.item(checklist, NATIVE_CLAIM)
        self.assertEqual(native["location"], {"file": "src/widget/export.py", "line": 31})

    def test_a_hand_written_ranged_line_stops_as_at_the_baseline(self):
        rendered = self.raise_native_ranged()
        self.place(rendered["review"].replace("independent reviewer", "a person"))
        code, doc, err = self.start()
        self.assertEqual(code, 10, "%s\n%s" % (err, doc))
        result = testlib.load_json(os.path.join(self.case, "run", "result.json"))
        self.assertEqual(result["status"], "missing_input", result)
        self.assertIn("is not a file:line location", json.dumps(result))

    def test_a_second_copy_of_the_rendered_line_stops(self):
        rendered = self.raise_native_ranged()
        self.place(rendered["review"] + rendered["review_lines"][0] + "\n")
        code, doc, err = self.start()
        self.assertEqual(code, 10, "%s\n%s" % (err, doc))
        result = testlib.load_json(os.path.join(self.case, "run", "result.json"))
        self.assertEqual(result["status"], "missing_input", result)


if __name__ == "__main__":
    unittest.main()
