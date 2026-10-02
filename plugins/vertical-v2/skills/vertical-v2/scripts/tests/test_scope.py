"""vertical-v2's scope (contract section 3.3; readings CR-3 and CR-4; ruling E15-8 with A2's Q1).

The local lenses review a `git archive` copy of HEAD with the outside export's exclusions and no `.git`,
under the run directory; vertical-v2 never runs `git worktree`. The spec every reviewer receives is the
build doc with `## Punch list`, `## Handoffs` and every slice's `Status:` line removed, through the
build-doc form's parse. Never in any packet: `docs/reviews/`, `docs/records/`, the removed sections, the
builder's notes, an untracked or ignored file; outside packets also never carry `REVIEW.md`, which
reaches the local lenses only. Each packet's file list carries a sha256 per file and is written before
any request, beside a withheld list naming what was kept back.
"""
import json
import os
import unittest

import testlib
import vlib

D = vlib.D
SHEET = """# Review sheet

## Passes
- correctness: on
- security: off (no network surface)
- accessibility: on

## Severity bar
| Severity | Meaning |
|---|---|
| BLOCKER | the bench loses a count |

## Repo-specific checks
- a reset never leaves a negative count
- the spinner never imports the encoder
"""
MARKERS = ("PRIOR-VERDICT-MARKER", "BUILDER-ADVOCACY-MARKER", "TOKEN=not-a-real-value",
           "the builder says slice B was easy", "the counter skips a turn", "Status: signed off")


def every_file(root):
    for base, dirs, files in os.walk(root):
        for name in files:
            yield os.path.join(base, name)


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "scope runs after the gate and the ask (the records component, readers' roster, jsonschema)")
class _Scope(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vscope-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def scoped(self, rows=("gpt-astra", "deepseek"), review_sheet=SHEET, depth=None, **repo):
        repo.setdefault("builder_notes", True)
        ws, info = vlib.make_repo(self.tmp, review_sheet=review_sheet, records=True, **repo)
        station = {"depth": depth} if depth else {}
        drive, run_dir = vlib.start(self.tmp, ws, **station)
        code, out, err = vlib.through_ask(drive, self.tmp, run_dir, rows=rows)
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["scope", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.ws, self.info, self.run_dir, self.drive = ws, info, run_dir, drive
        return out


class TheCopies(_Scope):

    def test_the_export_and_the_local_copy_are_the_reviewed_head_with_no_history(self):
        out = self.scoped()
        for name in ("export", "local"):
            root = os.path.join(self.run_dir, name)
            self.assertTrue(os.path.isdir(root), name)
            self.assertFalse(os.path.exists(os.path.join(root, ".git")), name)
            got = sorted(os.path.relpath(p, root) for p in every_file(root))
            self.assertEqual(got, ["README.md", "docs/plans/2026-09-20-turnstile.md", "src/legacy.py",
                                   "src/spinner.py", "src/turnstile.py"], name)
        self.assertEqual(testlib.tree_digest(os.path.join(self.run_dir, "export")),
                         testlib.tree_digest(os.path.join(self.run_dir, "local")))

    def test_no_worktree_is_cut_and_the_workspace_is_unchanged(self):
        before = testlib.tree_digest(self.tmp)
        self.scoped()
        listing = testlib.git(self.ws, ["worktree", "list", "--porcelain"])
        self.assertEqual(listing.count("worktree "), 1, listing)

    def test_the_build_docs_copy_is_the_spec_alone(self):
        self.scoped()
        spec = testlib.read_text(os.path.join(self.run_dir, "export", vlib.DOC))
        self.assertNotIn("## Punch list", spec)
        self.assertNotIn("## Handoffs", spec)
        self.assertNotIn("Status:", spec)
        self.assertIn("## Slice A %s the counter" % D, spec)
        self.assertIn("## Build assumptions", spec)
        self.assertIn("Acceptance criteria:", spec)


class ThePackets(_Scope):

    def test_no_planted_record_reaches_any_packet_or_copy(self):
        self.scoped()
        for root in ("export", "local", "packets"):
            for path in every_file(os.path.join(self.run_dir, root)):
                if os.path.basename(path) in ("files.json", "withheld.json"):
                    continue
                text = testlib.read_text(path)
                for marker in MARKERS:
                    self.assertNotIn(marker, text, (path, marker))

    def test_review_md_reaches_the_local_lenses_only(self):
        out = self.scoped()
        packets = vlib.load(self.run_dir, "scope.json")["packets"]
        local = [p for p in packets if p["side"] == "local"]
        outside = [p for p in packets if p["side"] == "outside"]
        self.assertTrue(local and outside)
        for packet in local:
            files = testlib.load_json(packet["files"])
            self.assertIn("REVIEW.md", [os.path.basename(f["path"]) for f in files["files"] if f["role"] == "document"])
        for packet in outside:
            files = testlib.load_json(packet["files"])
            self.assertNotIn("REVIEW.md", [os.path.basename(f["path"]) for f in files["files"]])
            withheld = testlib.load_json(packet["withheld"])
            self.assertIn("REVIEW.md", [w["what"] for w in withheld["withheld"]])
            for path in every_file(packet["dir"]):
                self.assertNotIn("a reset never leaves a negative count", testlib.read_text(path))

    def test_each_packet_names_every_planted_record_as_withheld(self):
        self.scoped()
        for packet in vlib.load(self.run_dir, "scope.json")["packets"]:
            withheld = [w["what"] for w in testlib.load_json(packet["withheld"])["withheld"]]
            for what in ("docs/reviews/2026-09-24-signoff-turnstile-A.md", "docs/builder-notes.md", ".env",
                         "%s ## Punch list" % vlib.DOC, "%s ## Handoffs" % vlib.DOC):
                self.assertIn(what, withheld, (packet["name"], what))
            self.assertEqual(len([w for w in withheld if w.startswith("%s Status: line" % vlib.DOC)]), 2, withheld)
            self.assertTrue(any(w.startswith("docs/records/") for w in withheld), withheld)

    def test_each_file_list_carries_a_sha256_per_file_and_matches_the_bytes(self):
        self.scoped()
        for packet in vlib.load(self.run_dir, "scope.json")["packets"]:
            files = testlib.load_json(packet["files"])
            self.assertTrue(files["files"], packet["name"])
            for entry in files["files"]:
                self.assertEqual(testlib.sha256_file(entry["abs"]), entry["sha256"], entry["path"])

    def test_a_packet_only_row_reads_staged_files_named_with_double_underscores(self):
        self.scoped(rows=("deepseek",))
        packet = [p for p in vlib.load(self.run_dir, "scope.json")["packets"] if p["name"] == "outside-deepseek"][0]
        names = sorted(os.path.basename(f["path"]) for f in testlib.load_json(packet["files"])["files"]
                       if f["role"] == "document")
        self.assertIn("src__turnstile.py", names)
        self.assertIn("docs__plans__2026-09-20-turnstile.md", names)
        self.assertIsNone(packet["workspace"])

    def test_a_repo_row_reads_the_export_as_its_workspace(self):
        self.scoped(rows=("gpt-astra",))
        packet = [p for p in vlib.load(self.run_dir, "scope.json")["packets"] if p["name"] == "outside-gpt-astra"][0]
        self.assertEqual(packet["workspace"], os.path.join(self.run_dir, "export"))

    def test_the_outside_mandate_is_v1s_with_its_three_slots_filled(self):
        self.scoped()
        mandate = testlib.read_text(os.path.join(self.run_dir, "mandate.md"))
        for slot in ("[BUILD_DOC]", "[BASE_COMMIT]", "[BOUNDARY_FILES]"):
            self.assertNotIn(slot, mandate)
        self.assertIn("Base commit: %s" % self.info["base"], mandate)
        self.assertIn("src/spinner.py", mandate)
        self.assertIn("## Slice B %s the spinner" % D, mandate)
        self.assertNotIn("Status:", mandate)
        asset = testlib.read_text(os.path.join(testlib.SKILL, "assets", "vertical-mandate.md"))
        self.assertTrue(mandate.startswith(asset.split("[BUILD_DOC]")[0]))


class TheLensesAndTheSheet(_Scope):

    def test_lean_lenses_and_the_sheets_passes(self):
        self.scoped()
        scope = vlib.load(self.run_dir, "scope.json")
        self.assertEqual(scope["depth"], "LEAN")
        self.assertEqual(scope["lenses"], ["spec", "correctness", "seams", "accessibility"])
        sheet = scope["review_sheet"]
        self.assertEqual(sheet["state"], "read")
        self.assertEqual(sheet["skipped"], [{"pass": "security", "reason": "no network surface"}])
        self.assertEqual(sheet["checks"], ["a reset never leaves a negative count", "the spinner never imports the encoder"])

    def test_deep_adds_security_and_tests_unless_the_sheet_turns_one_off(self):
        self.scoped(depth="DEEP")
        self.assertEqual(vlib.load(self.run_dir, "scope.json")["lenses"],
                         ["spec", "correctness", "seams", "tests", "accessibility"])

    def test_a_file_that_is_not_the_sheet_is_reported_and_the_defaults_apply(self):
        self.scoped(review_sheet="# How we review\n\nBe kind.\n")
        scope = vlib.load(self.run_dir, "scope.json")
        self.assertEqual(scope["review_sheet"]["state"], "present but not the kit sheet")
        self.assertEqual(scope["lenses"], ["spec", "correctness", "seams"])

    def test_no_sheet_reads_absent(self):
        self.scoped(review_sheet=None)
        self.assertEqual(vlib.load(self.run_dir, "scope.json")["review_sheet"]["state"], "absent")

    def test_each_local_mandate_names_its_lens_the_base_and_the_boundary(self):
        self.scoped()
        for lens in ("spec", "correctness", "seams", "accessibility"):
            text = testlib.read_text(os.path.join(self.run_dir, "packets", "local-%s" % lens, "mandate.md"))
            self.assertIn("lens: %s" % lens, text)
            self.assertIn(self.info["base"], text)
            self.assertIn("src/spinner.py", text)
            self.assertIn("a reset never leaves a negative count", text)


if __name__ == "__main__":
    unittest.main()
