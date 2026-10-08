"""Other plans are left out (the E15 lane contract A32, the full review's finding 1; contract section 5, the allow
rule's (5)).

Every packet and every summons copy, local and outside, carries the build doc under review alone among the plans:
every other file under `docs/plans/` (two consecutive components `docs` then `plans`, letter case aside, wherever they
stand, any kind of file), and every other `.md` regular file the build-doc form reads as a build doc (a level 2
heading the withheld-name rule reads as `## Punch list` or `## Handoffs`, or a level 2 heading on the form's slice
pattern, in either reading), is withheld and named in `withheld.json` with its reason. The preview (`scope`) and every
summons copy agree, since one function builds both.

`TheRule` drives the snapshot directly over each shape and each control. `TheSmallestCase` drives the full review's
smallest case through the real CLI (`scope`, the local `request`, `record-local`, `request --outside`): no trace of
either plan in any preview, summons copy or request file, local or outside, every withheld list naming each plan,
and the plan under review arriving with its ledger removed as before.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import packet, spec as specmod  # noqa: E402

D = vlib.D
DOC = vlib.DOC

# the full review's smallest case: a second tracked plan with a `Status:` line, a prior verdict in its punch list and
# builder advocacy in its handoffs
PREVIOUS = ("# Previous plan\n\n## Slice X\nStatus: signed off\n\n## Punch list\nPRIOR-PLAN-VERDICT: accepted after "
            "review.\n\n## Handoffs\nAUTHOR-ADVOCACY: implementation is correct.\n")
NO_LEDGER = "# Draft plan\n\nIntent: a later counter.\n\n## Goals\nNO-LEDGER-MARKER count twice as fast\n"

# (path, text, the line the reason names or None for a docs/plans path): each must be withheld
WITHHELD = [
    ("docs/plans/previous.md", PREVIOUS, None),
    ("docs/plans/2026-10-01-draft.md", NO_LEDGER, None),
    ("docs/plans/sketch.txt", "PLANS-FOLDER-TEXT-MARKER a sketch\n", None),
    ("pkg/docs/plans/old.md", "# Old\n\nNESTED-PLANS-MARKER\n", None),
    ("sub/Docs/Plans/old.md", "# Old\n\nCASED-PLANS-MARKER\n", None),
    ("notes/old-plan.md", "# Old bench plan\n\nIntro.\n\n## Punch list\n- FORM-PUNCH-MARKER accepted\n", 5),
    ("archive/log.md", "# Log\n\n## Handoffs\n\n### 2026-08-02 %s handoff\n- FORM-HANDOFF-MARKER skim it\n" % D, 3),
    ("archive/setext.md", "# Log\n\nHand-offs\n---------\n- FORM-SETEXT-MARKER skim it\n", 3),
    ("archive/listed.md", "# Log\n\n- ## Punch list\n  - FORM-LISTED-MARKER accepted\n", 3),
    ("archive/coded.md", "# Log\n\n## P&#117;nch list\n- FORM-CODED-MARKER accepted\n", 3),
    ("archive/numbered.md", "# Log\n\n## 1. Punch list\n- FORM-NUMBERED-MARKER accepted\n", 3),
    ("plan/old.md", "# Old %s build plan (2026-08-01)\n\n## Slice A %s the first counter\nStatus: signed off\n"
                    "FORM-SLICE-MARKER every slice signed off\n" % (D, D), 3),
]
# (path, text, its marker): each must still reach the packets
KEPT = [
    ("docs/guide.md", "# Guide\n\n### Punch list\nKEPT-LEVEL-THREE how a punch list reads\n", "KEPT-LEVEL-THREE"),
    ("docs/form.md", "# The form\n\n```\n## Punch list\n## Handoffs\n```\nKEPT-FENCED-EXAMPLE\n", "KEPT-FENCED-EXAMPLE"),
    ("docs/handoff.md", "# Handoff\n\nKEPT-HANDOFF-TITLE how the handoff station works.\n", "KEPT-HANDOFF-TITLE"),
    ("docs/slices.md", "# Notes\n\n## Slices\nKEPT-SLICES-HEADING how a plan is sliced\n", "KEPT-SLICES-HEADING"),
    ("docs/prose.md", "# Notes\n\nKEPT-PROSE the punch list and the handoffs live in the plan.\n", "KEPT-PROSE"),
    ("src/fixture.py", 'TEXT = """\n## Punch list\nKEPT-NOT-MARKDOWN\n"""\n', "KEPT-NOT-MARKDOWN"),
]


def markers(text):
    return [word for word in text.replace("\n", " ").split() if word.endswith("-MARKER") or word in
            ("PRIOR-PLAN-VERDICT:", "AUTHOR-ADVOCACY:")]


class TheRule(unittest.TestCase):
    """The snapshot over every shape and control, read from the commit's objects."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = testlib.make_scratch("vplans-")
        files = dict((path, text) for path, text, line in WITHHELD)
        files.update(dict((path, text) for path, text, marker in KEPT))
        cls.ws, cls.info = vlib.make_repo(cls.tmp, extra_build_files=files)
        cls.snap = packet.Snapshot(cls.ws, cls.info["head"], DOC)
        cls.left = dict((item["what"], item["why"]) for item in cls.snap.left)

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.tmp)

    def test_every_other_plan_is_withheld_and_named_with_its_reason(self):
        for path, text, line in WITHHELD + [(vlib.SECOND_PLAN, vlib.second_plan_text(), None)]:
            with self.subTest(path=path):
                self.assertNotIn(path, self.snap.tree)
                self.assertNotIn(path, self.snap.texts)
                self.assertIn(path, self.left)
                self.assertIn("A32", self.left[path])
                if line is None:
                    self.assertIn("docs/plans/", self.left[path])
                else:
                    self.assertIn("line %d" % line, self.left[path])

    def test_the_controls_still_reach_the_packets(self):
        for path, text, marker in KEPT:
            with self.subTest(path=path):
                self.assertEqual(self.snap.tree.get(path), text.encode("utf-8"))
                self.assertNotIn(path, self.left)

    def test_the_plan_under_review_still_arrives_with_its_ledger_removed(self):
        with open(os.path.join(self.ws, DOC), encoding="utf-8", newline="") as fh:
            spec, removed = specmod.clean(fh.read())
        self.assertEqual(self.snap.tree[DOC], spec.encode("utf-8"))
        self.assertEqual(self.snap.spec, spec)
        self.assertIn("Goal: one sentence about the counter.", spec)
        for gone in ("## Punch list", "## Handoffs", "Status: signed off", "the reviewers should skim it"):
            self.assertNotIn(gone, spec)
        self.assertNotIn(DOC, self.left)

    def test_every_packet_kind_leaves_every_other_plan_out(self):
        gate = {"base": {"commit": self.info["base"]}, "head": self.info["head"], "boundary": []}
        worktree = packet.worktree_names(self.ws)
        for spec in ({"name": "local-spec", "side": "local", "lens": "spec", "profile": "repo-with-tools"},
                     {"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"},
                     {"name": "outside-deepseek", "side": "outside", "row": "deepseek", "profile": "packet-only"}):
            built = packet.build(self.snap, spec, gate, testlib.SKILL, worktree)
            named = [w["what"] for w in built["withheld"]]
            text = b"\n".join(built["files"].values()).decode("utf-8", "replace")
            with self.subTest(packet=spec["name"]):
                for path, body, line in WITHHELD:
                    self.assertIn(path, named)
                    for word in markers(body):
                        self.assertNotIn(word, text)
                for path, body, marker in KEPT:
                    self.assertIn(marker, text)


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the smallest case runs the gate, the ask, scope and the requests (records, readers' roster, "
                     "jsonschema)")
class TheSmallestCase(unittest.TestCase):
    """The full review's smallest case through the real CLI, with a plan holding no ledger and a file on the build-doc
    form outside `docs/plans/` beside it."""

    PLANTED = {"docs/plans/previous.md": PREVIOUS, "docs/plans/2026-10-01-draft.md": NO_LEDGER,
               "notes/old-plan.md": "# Old bench plan\n\n## Handoffs\n- FORM-HANDOFF-MARKER skim it\n"}
    WORDS = ("PRIOR-PLAN-VERDICT", "AUTHOR-ADVOCACY", "NO-LEDGER-MARKER", "FORM-HANDOFF-MARKER") + \
        vlib.SECOND_PLAN_MARKERS

    def setUp(self):
        self.tmp = testlib.make_scratch("vplans-cli-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def run_case(self):
        ws, info = vlib.make_repo(self.tmp, extra_build_files=dict(self.PLANTED), records=True, builder_notes=True)
        drive, run_dir = vlib.start(self.tmp, ws)

        def named(args):
            return drive(args + (["--doc", DOC] if args[0] == "gate" else []))

        code, out, err = vlib.through_ask(named, self.tmp, run_dir, rows=("gpt-astra", "deepseek"),
                                          words="local plus GPT and DeepSeek")
        self.assertEqual(code, 0, (out, err))
        for args in (["scope", "--run-dir", run_dir], ["request", "--run-dir", run_dir]):
            code, out, err = drive(args)
            self.assertEqual(code, 0, (args, out, err))
        vlib.file_local_sidecars(run_dir)
        code, out, err = vlib.record_local(drive, self.tmp, run_dir)
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 0, (out, err))
        return run_dir

    def test_no_other_plan_leaves_a_trace_and_each_is_named_in_every_preview_and_summons(self):
        run_dir = self.run_case()
        lists = {}
        for folder in ("packets", "summons"):
            root = os.path.join(run_dir, folder)
            names = sorted(os.listdir(root))
            self.assertTrue(names, folder)
            for name in names:
                withheld = testlib.load_json(os.path.join(root, name, "withheld.json"))
                lists[(folder, name)] = withheld
                named = dict((w["what"], w["why"]) for w in withheld["withheld"])
                for path in sorted(self.PLANTED) + [vlib.SECOND_PLAN]:
                    self.assertIn(path, named, (folder, name))
                    self.assertIn("A32", named[path], (folder, name, path))
                    self.assertFalse(os.path.lexists(os.path.join(root, name, "workspace", *path.split("/"))),
                                     (folder, name, path))
                    self.assertFalse(os.path.lexists(os.path.join(root, name, "documents", path.replace("/", "__"))),
                                     (folder, name, path))
        self.assertEqual(sorted(name for folder, name in lists if folder == "summons"),
                         sorted(["run-0001-local-spec", "run-0001-local-correctness", "run-0001-local-seams",
                                 "run-0001-gpt-astra", "run-0001-deepseek"]))
        for (folder, name), withheld in lists.items():
            if folder == "summons":
                preview = lists[("packets", withheld["packet"])]
                self.assertEqual(withheld["withheld"], preview["withheld"], name)
        self.assertEqual(vlib.second_plan_absent(run_dir), [])
        for folder in ("packets", "summons", "requests"):
            for base, dirs, files in os.walk(os.path.join(run_dir, folder)):
                for name in files:
                    if name == "withheld.json":
                        continue
                    text = testlib.read_text(os.path.join(base, name))
                    for word in self.WORDS:
                        self.assertNotIn(word, text, os.path.join(base, name))

    def test_the_plan_under_review_still_arrives_with_its_ledger_removed(self):
        run_dir = self.run_case()
        root = os.path.join(run_dir, "summons")
        with open(os.path.join(self.tmp, "workspace", DOC), encoding="utf-8", newline="") as fh:
            spec, removed = specmod.clean(fh.read())
        local = [n for n in os.listdir(root) if "-local-" in n]
        self.assertEqual(len(local), 3)
        for name in local:
            self.assertEqual(testlib.read_text(os.path.join(root, name, "documents", "spec.md")), spec)
            self.assertEqual(testlib.read_text(os.path.join(root, name, "workspace", DOC)), spec)
        named = [w["what"] for w in testlib.load_json(os.path.join(root, local[0], "withheld.json"))["withheld"]]
        for section in ("## Punch list", "## Handoffs", "## Build assumptions", "## Deviations", "## Discovered"):
            self.assertIn("%s %s" % (DOC, section), named)


if __name__ == "__main__":
    unittest.main()
