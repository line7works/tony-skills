"""Part J7: the three findings of the final review, fixed.

- D8 (BLOCKER): the lines `drop_cli_keys` leaves out of a hosting environment's copy are a provider's secrets too. The
  values of the keys a row names as the CLI's secrets (`cli_secrets`) enter the withheld register as they are read, before
  anything is written; where one already stands in the run's own records (her case: the run's description equals the
  token), a durable disproof record is written and the run stops on it, and every later form withholds the value. Earlier
  records are never rewritten.
- L-19 (MAJOR): a re-plan after T13 places a T17 member found inside the moved vault folder through T13's output and its
  folder-relative path, as the first look did, so that the restore's V06 finds it.
- L-24 (MAJOR): T17 edits links only (wiki links, an embed among them, and Markdown links), never plain text, and never a
  file the tool wrote as a lifecycle record (`_sunset-*.md`, `_restore-*.md`).
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_set_lib as lib  # noqa: E402
import test_lane_prov_set as pset  # noqa: E402
import test_j6i_replan as j6i  # noqa: E402


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def text_files(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".fakes"]
        for name in files:
            yield os.path.join(base, name)


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def vault_notes(m):
    return dict((os.path.relpath(p, m.vault), read(p)) for p in text_files(m.vault) if p.endswith(".md"))


class Disclosure(harness.Case):
    """D8, her collision case."""

    def test_D8_SEC12_a_dropped_cli_secret_equal_to_the_runs_description_is_disproved_and_withheld_in_every_later_form(self):
        marker = harness.canary("reviewdrop")
        m = pset.world(self)
        provlib.put_state(m, "vercel", oidc_token=marker)
        looked = lib.look(m, description=marker)
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        run_dir = m.facts.run_dir(run)
        before = dict((p, sha(p)) for p in text_files(run_dir))
        went = lib.go(m, looked)
        # the go meets the token as T04-development's pull lands, finds it already in the run's records, records the
        # disproof and stops on it (SEC-12)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("a safe ground disproved", went.text)
        disproofs = [r for r in m.journal(run) if r["kind"] == "disproof"]
        self.assertEqual(len(disproofs), 1)
        self.assertNotIn(marker, json.dumps(disproofs))
        self.assertNotIn(marker, went.text)
        # the resume reads the disproof back, withholds the value, and completes
        resumed = m.resume(lib.NAMES[0], None, also=lib.ALSO, caps=list(lib.CAPS))
        self.assertEqual(resumed.ending, "complete", resumed.text)
        self.assertNotIn(marker, resumed.text)
        for result in (went, resumed):
            for form in result.doc.get("forms") or []:
                with open(form) as fh:
                    self.assertNotIn(marker, fh.read(), form)
        # every form and record written after the look holds it nowhere; the look's own records are as they were
        for path in text_files(run_dir):
            if path in before:
                self.assertEqual(sha(path), before[path], path)
            else:
                self.assertNotIn(marker.encode("utf-8"), read(path), path)
        for path in text_files(pset.folder(m)):
            self.assertNotIn(marker.encode("utf-8"), read(path), path)


class Relocation(harness.Case):
    """L-19, her case: links inside the moved vault folder, a stop at T16 after an index edit, a re-plan."""

    def test_L19_V06_RUN6_a_member_inside_the_moved_folder_keeps_its_folder_relative_place_and_the_restore_completes(self):
        m, looked, went = j6i.stopped_foreign_at_t16(self, links_inside=True)
        self.assertEqual(went.ending, "stopped", went.text)
        replanned = j6i.replan(m)
        self.assertTrue(replanned.doc.get("manifest_sha256"), replanned.text)
        run = looked.doc["run"]
        first, again = j6i.manifest(m, run, 1), j6i.manifest(m, run, j6i.numbers(m, run)[-1])
        places = lambda doc: sorted(json.dumps(o["thing"]["place"], sort_keys=True) for o in doc["operations"] if o["id"].startswith("T17-"))
        self.assertEqual(places(again), places(first))
        done = j6i.go_on(m, replanned)
        self.assertEqual(done.ending, "complete", done.text)
        back = lib.look(m, "restore")
        restored = lib.go(m, back, "restore")
        self.assertEqual(restored.ending, "complete", restored.text)
        self.assertEqual(read(m.path("vault", "projects", "demo", "plan.md")), b"the plan, from [[projects/demo/_index]]\n")


NOTE = ("the old folder was projects/demo/ until today\n"
        "see [[projects/demo/plan|the plan]] and [[projects/demo/_index#Top]]\n"
        "an embed ![[projects/demo/plan]]\n"
        "and [the plan](projects/demo/plan.md) too\n")
REPOINTED = ("the old folder was projects/demo/ until today\n"
             "see [[archive/demo/plan|the plan]] and [[archive/demo/_index#Top]]\n"
             "an embed ![[archive/demo/plan]]\n"
             "and [the plan](archive/demo/plan.md) too\n")


class LinksOnly(harness.Case):
    """L-24, the owner's "Links only"."""

    def test_T17_V06_L24_links_are_repointed_plain_text_is_not_and_the_restore_puts_the_links_back(self):
        m = lib.machine(self)
        m.put("vault/notes/mixed.md", NOTE)
        m.put("vault/notes/plain.md", "only a mention of projects/demo/ in plain text\n")
        lib.run(self, m)
        self.assertEqual(read(m.path("vault", "notes", "mixed.md")).decode("utf-8"), REPOINTED)
        self.assertEqual(read(m.path("vault", "notes", "plain.md")), b"only a mention of projects/demo/ in plain text\n")
        back = lib.look(m, "restore")
        restored = lib.go(m, back, "restore")
        self.assertEqual(restored.ending, "complete", restored.text)
        self.assertEqual(read(m.path("vault", "notes", "mixed.md")).decode("utf-8"), NOTE)
        self.assertEqual(read(m.path("vault", "notes", "plain.md")), b"only a mention of projects/demo/ in plain text\n")

    def test_T17_L24_history_a_second_sunset_after_a_restore_leaves_every_earlier_lifecycle_record_byte_equal(self):
        m = lib.machine(self)
        lib.run(self, m)
        back = lib.look(m, "restore")
        restored = lib.go(m, back, "restore")
        self.assertEqual(restored.ending, "complete", restored.text)
        records = dict((k, v) for k, v in vault_notes(m).items()
                       if os.path.basename(k).startswith(("_sunset-", "_restore-")))
        self.assertEqual(sorted(os.path.basename(k).split("-")[0] for k in records), ["_restore", "_sunset"])
        self.assertTrue(any(b"projects/demo/" in v for v in records.values()))
        m.now = lambda: "2026-01-02T01:00:00Z"
        looked = lib.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = lib.go(m, looked)
        self.assertEqual(went.ending, "complete", went.text)
        after = dict((os.path.basename(k), v) for k, v in vault_notes(m).items())
        for name, data in records.items():
            self.assertEqual(after[os.path.basename(name)], data, name)


class LinkForms(harness.Case):
    """L-24's two units: which text is a link, and which files the read skips."""

    def test_L24_replace_links_repoints_wiki_links_embeds_and_markdown_links_and_nothing_else(self):
        from sun_core import effects
        text = ("plain projects/demo/a, [[projects/demo/a]], [[projects/demo/a|b]], [[projects/demo/a#h]], ![[projects/demo/i]],"
                " [t](projects/demo/a.md), ![i](projects/demo/i.png), [[other/projects/demo/a]], [r](../projects/demo/a.md)\n")
        out, count = effects.replace_links(text, "projects/demo/", "archive/demo/")
        self.assertEqual(count, 6)
        self.assertEqual(out, "plain projects/demo/a, [[archive/demo/a]], [[archive/demo/a|b]], [[archive/demo/a#h]], "
                              "![[archive/demo/i]], [t](archive/demo/a.md), ![i](archive/demo/i.png), [[other/projects/demo/a]], "
                              "[r](../projects/demo/a.md)\n")
        self.assertIsNone(effects.edited(b"plain projects/demo/ only\n", {"kind": "replace-links", "old": "projects/demo/",
                                                                          "new": "archive/demo/"}, lambda v: v))

    def test_L24_the_family_read_skips_the_tools_lifecycle_records_by_name(self):
        from sun_core import fsio, plan
        root = os.path.join(self.tmp, "vault-skip")
        for name in ("note.md", "_sunset-sunset-1.md", "_restore-restore-1.md", "deep/_sunset-sunset-2.md"):
            os.makedirs(os.path.dirname(os.path.join(root, name)), exist_ok=True)
            with open(os.path.join(root, name), "w") as fh:
                fh.write("[[projects/demo/x]]\n")
        spec = {"read": "files", "folder": root, "glob": "*.md", "holding": "projects/demo/", "tree": True}
        every = [os.path.relpath(i["path"], root) for i in plan.found_items(fsio.FS(), spec)]
        self.assertEqual(len(every), 4)
        family = [r for r in lib.shipped_lane("sunset")["rows"] if r["id"] == "T17"][0]["thing"]["family"]
        self.assertEqual(family["skip"], ["_sunset-*.md", "_restore-*.md"])
        spec["skip"] = family["skip"]
        self.assertEqual([os.path.relpath(i["path"], root) for i in plan.found_items(fsio.FS(), spec)], ["note.md"])


if __name__ == "__main__":
    import unittest
    unittest.main()
