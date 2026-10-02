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
        for section in ("## Build assumptions", "## Deviations", "## Discovered"):
            self.assertNotIn(section, spec)
        self.assertIn("Acceptance criteria:", spec)

    def test_the_copies_ignore_the_repos_export_attributes(self):
        """C1A-5: no `export-subst` expansion and no `export-ignore` drop: each copy holds the commit's bytes."""
        self.scoped(extra_build_files={".gitattributes": "src/ver.txt export-subst\nsrc/hidden.py export-ignore\n",
                                       "src/ver.txt": "$Format:%B$\n", "src/hidden.py": "HIDDEN = 1\n"})
        for name in ("export", "local"):
            root = os.path.join(self.run_dir, name)
            self.assertEqual(testlib.read_text(os.path.join(root, "src", "ver.txt")), "$Format:%B$\n", name)
            self.assertEqual(testlib.read_text(os.path.join(root, "src", "hidden.py")), "HIDDEN = 1\n", name)
            for path in every_file(root):
                self.assertNotIn("the build\n", testlib.read_text(path), path)


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


class TheBuildersWorkingRecords(_Scope):
    """C1A-3, the owner's ruling in A3: `## Build assumptions`, `## Deviations` and `## Discovered` are left
    out of the spec every reviewer receives, each named as withheld in every packet."""

    MARKED = ("BUILDER-ASSUMPTION-MARKER", "BUILDER-DEVIATION-MARKER", "BUILDER-DISCOVERED-MARKER")

    def doc(self):
        text = vlib.build_doc()
        text = text.replace("- the bench clock is monotonic", "- the bench clock is monotonic BUILDER-ASSUMPTION-MARKER")
        text = text.replace("## Deviations\n", "## Deviations\n- BUILDER-DEVIATION-MARKER: skipped the retry, plainly unneeded\n")
        text = text.replace("## Discovered\n", "## Discovered\n- BUILDER-DISCOVERED-MARKER: the clock drifts\n")
        return text

    def test_no_working_record_reaches_any_packet_copy_or_mandate(self):
        self.scoped(doc_text=self.doc())
        for root in ("export", "local", "packets"):
            for path in every_file(os.path.join(self.run_dir, root)):
                if os.path.basename(path) in ("files.json", "withheld.json"):
                    continue
                text = testlib.read_text(path)
                for marker in self.MARKED:
                    self.assertNotIn(marker, text, (path, marker))
        for name in ("spec.md", "mandate.md"):
            text = testlib.read_text(os.path.join(self.run_dir, name))
            for marker in self.MARKED:
                self.assertNotIn(marker, text, (name, marker))

    def test_each_packet_names_the_three_sections_as_withheld(self):
        self.scoped(doc_text=self.doc())
        for packet in vlib.load(self.run_dir, "scope.json")["packets"]:
            withheld = [w["what"] for w in testlib.load_json(packet["withheld"])["withheld"]]
            for section in ("## Build assumptions", "## Deviations", "## Discovered"):
                self.assertIn("%s %s" % (vlib.DOC, section), withheld, (packet["name"], section))


class TheStagedNames(_Scope):
    """C1A-6: two export paths that stage to one name both reach the packet under distinct names, and the
    file list never carries one name twice."""

    def test_a_collision_stages_both_files_under_distinct_names(self):
        self.scoped(rows=("deepseek",), extra_build_files={"docs/a__b.md": "COLLIDE-ONE\n", "docs/a/b.md": "COLLIDE-TWO\n"})
        packet = [p for p in vlib.load(self.run_dir, "scope.json")["packets"] if p["name"] == "outside-deepseek"][0]
        entries = testlib.load_json(packet["files"])["files"]
        names = [os.path.basename(e["path"]) for e in entries]
        self.assertEqual(len(names), len(set(names)), names)
        texts = sorted(testlib.read_text(e["abs"]) for e in entries if e["role"] == "document"
                       and testlib.read_text(e["abs"]).startswith("COLLIDE-"))
        self.assertEqual(texts, ["COLLIDE-ONE\n", "COLLIDE-TWO\n"])
        sources = sorted(e.get("source") for e in entries if e["role"] == "document"
                         and testlib.read_text(e["abs"]).startswith("COLLIDE-"))
        self.assertEqual(sources, ["docs/a/b.md", "docs/a__b.md"])
        self.assertEqual(testlib.load_json(packet["withheld"])["left_out"], [])

    def test_the_names_are_the_same_on_every_run(self):
        files = {"docs/a__b.md": "COLLIDE-ONE\n", "docs/a/b.md": "COLLIDE-TWO\n"}
        seen = []
        for attempt in ("one", "two"):
            sub = os.path.join(self.tmp, attempt)
            os.makedirs(sub)
            self.tmp, keep = sub, self.tmp
            try:
                self.scoped(rows=("deepseek",), extra_build_files=files)
            finally:
                self.tmp = keep
            packet = [p for p in vlib.load(self.run_dir, "scope.json")["packets"] if p["name"] == "outside-deepseek"][0]
            seen.append(sorted((os.path.basename(e["path"]), e.get("source"))
                               for e in testlib.load_json(packet["files"])["files"] if e["role"] == "document"))
        self.assertEqual(seen[0], seen[1])


class TheLocalMandateFollowsTheRoute(_Scope):
    """C1A-9: on the `repo` route the local mandate says the reader reads and runs nothing and never promises
    tests; on `repo-with-tools` it keeps its words."""

    def mandates(self):
        return [testlib.read_text(os.path.join(self.run_dir, "packets", name, "mandate.md"))
                for name in sorted(os.listdir(os.path.join(self.run_dir, "packets"))) if name.startswith("local-")]

    def test_on_the_repo_route_the_mandate_runs_nothing(self):
        ws, info = vlib.make_repo(self.tmp, review_sheet=SHEET, records=True)
        drive, run_dir = vlib.start(self.tmp, ws, harness="codex-cli")
        code, out, err = vlib.through_ask(drive, self.tmp, run_dir, rows=(), local_row="claude-opus-cli")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(drive(["scope", "--run-dir", run_dir])[0], 0)
        self.run_dir = run_dir
        texts = self.mandates()
        self.assertTrue(texts)
        for text in texts:
            self.assertNotIn("You may run the project's tests", text)
            self.assertNotIn("verification blocked", text)
            self.assertIn("This route runs no command", text)
            self.assertNotIn("executed, read or reasoned", text)
        correctness = [t for t in texts if "lens: correctness" in t][0]
        self.assertIn("runs nothing", correctness.split("## The scope")[0])

    def test_on_the_tools_route_the_mandate_keeps_its_words(self):
        self.scoped(rows=())
        for text in self.mandates():
            self.assertIn("You may run the project's tests there", text)
            self.assertNotIn("This route runs no command", text)


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
