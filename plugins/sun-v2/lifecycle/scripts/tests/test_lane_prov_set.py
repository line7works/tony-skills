"""Slice 3, the providers: the sunset rows (rows-prov section 3.3) and restore's two ways back (3.4) as the join leaves them,
in slice 4's shipped `sunset/lane.json`, over the four fakes on slice 4's own fixture machine (`test_lane_set_lib`, slice 3's
world planted by `provlib.sunset_world`): a whole sunset, slice 4's rows giving the outputs these rows need; this lane's
required items 1 (the hosting keep's mark) and 2 (N3, the reversible encoding); and part two's rows and mechanisms (T01 on
G23-1, T21 and V11 on G23-5, T03 on G23-9, T04 on G23-6 and G23-8, T04c on G23-3 and G23-7, `repository moved` at
slice 4's level).

Every test's name carries the row's id and the rule's id.
"""
import copy
import json
import os
import stat
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_set_lib as lib  # noqa: E402
from sun_core import effects, plan, protected  # noqa: E402

SET_ROWS = ("T01s", "T01", "T03", "T04-development", "T04-preview", "T04-production", "T04c", "T20", "T21")
DATE = "2026-01-01"                 # the look's date by the fixture's clock (`plan.build`: `world.now()[:10]`)
TAG = "refs/tags/sunset-" + DATE
NOT_SAVED = "Not saved, Sensitive (the provider never returns the value): %s (%s)"


def read_file(path, mode="r"):
    with open(path, mode) as fh:
        return fh.read()


def completion(m, run, op):
    return [r for r in m.journal(run) if r["kind"] == "completion" and r["op"] == op][0]


def record(m, run, reference):
    return json.loads(protected.read(m.world().fs, m.facts.run_dir(run), reference).decode())


def folder(m):
    """Slice 4's T02, the sunset folder (rows-set SF)."""
    return os.path.join(m.archive, "demo.sunset-" + DATE)


def tombstone(m, run):
    """Slice 4's T30, the run's last record in the moved vault folder (rows-set T30)."""
    return read_file(m.path("vault", "archive", "demo", "_sunset-%s.md" % run))


def world(case, label="m", seed=None, **planted):
    """Slice 4's fixture machine with slice 3's world (`planted`: `provlib.sunset_world`'s values, tables, custom) and the
    shipped lanes; `m.world_made` is (the repository, its commit, the database's password)."""
    return lib.machine(case, label, **planted)


KEEP = {"keep_github": "github", "keep_vercel": "hosting", "keep_db": "database"}


def look(m, **keep):
    """The sunset look; v1's `--keep-github`, `--keep-vercel`, `--keep-db` given as the layers they drop (rows-set C4; the
    join's J1b item 5)."""
    return lib.look(m, drop_layers=[KEEP[k] for k, v in sorted(keep.items()) if v])


def started(m, **flags):
    looked = look(m, **flags)
    assert looked.doc and looked.doc.get("manifest_sha256"), looked.text
    return looked, lib.go(m, looked)


def sunset_row(rid):
    return [r for r in lib.shipped_lane("sunset")["rows"] if r["id"] == rid][0]


def stop_of(m, run):
    return [r for r in m.journal(run) if r["kind"] == "invocation-end"][-1]["reason"]


class Admission(harness.Case):
    def test_ROW1_ROW3_the_joined_sunset_and_restore_lanes_are_admitted_with_their_checklists(self):
        lane = lib.shipped_lane("sunset")
        self.assertEqual(plan.admit_all(lane, plan.expand(lane, provlib.providers()), provlib.providers()), [])
        self.assertEqual([r["id"] for r in lane["rows"] if r["id"] in SET_ROWS], list(SET_ROWS))
        restore = lib.shipped_lane("restore")
        self.assertEqual(plan.admit_all(restore, plan.expand(restore, provlib.providers()), provlib.providers()), [])
        # V10 rides as T20's way back, admitted as a reverse (EV-4)
        t20 = [r for r in lane["rows"] if r["id"] == "T20"][0]
        self.assertEqual(t20["way_back"]["reverse"]["id"], "V10")

    def test_required_1_RK19_KEEP1_A149_every_hosting_keep_carries_the_mark_and_its_two_reads_are_admitted_only_with_it(self):
        part = lib.shipped_lane("sunset")
        keeps = [r for r in part["rows"] if r["id"].startswith("T04")]
        self.assertEqual(sorted(r["id"] for r in keeps), ["T04-development", "T04-preview", "T04-production", "T04c"])
        self.assertTrue(all(r["construction"].get("hosting_env") is True for r in keeps))
        self.assertNotIn("hosting_env", [r for r in part["rows"] if r["id"] == "T03"][0]["construction"])
        # without the mark, T04's two reads before and after the pull fail the build (G22-4), naming the row
        unmarked = copy.deepcopy(part)
        for r in unmarked["rows"]:
            if r["id"] == "T04-production":
                del r["construction"]["hosting_env"]
        lane = unmarked
        found = plan.admit_all(lane, plan.expand(lane, provlib.providers()), provlib.providers())
        self.assertEqual([(f["row"], f["entry"]) for f in found], [("T04-production", "keep_scope")])


class EndToEnd(harness.Case):
    def test_T01s_T01_T03_T04_T04c_T20_T21_RUN8_KEEP1_KEEP3_a_sunset_over_the_fakes_looked_previewed_approved_and_complete(self):
        m = world(self, custom=[{"id": "env_customone", "slug": "staging"}])
        repo, commit, password = m.world_made
        state = provlib.state(m, "vercel")
        state["envs"]["demo"].append({"key": "STAGE_ONLY", "value": "staging-value-1", "type": "encrypted", "custom": "env_customone"})
        provlib.put_state(m, "vercel", envs=state["envs"])
        looked = look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        preview = read_file(looked.doc["forms"][0])
        for line in ("Backup: dump the whole database to the sunset folder", "Saved copies: hosting env values of production, owner-only",
                     "Saved copies: hosting env values of custom environment custom-1, owner-only",
                     "GitHub: archive fixture-account/demo (read-only)", "Scan: every commit the tag push sends",
                     "GitHub: tag sunset-%s at the head" % DATE, "Hosting: pause demo (production blocked, reversible)"):
            self.assertIn(line, preview)
        self.assertNotIn("staging", preview)                 # the custom environment's own name is held (SEC-4; N2)
        went = lib.go(m, looked)
        self.assertEqual(went.ending, "complete", went.text)
        statuses = m.statuses(run)
        self.assertEqual(statuses.get("T01s"), "passed")
        for op in ("T01", "T03", "T04-development", "T04-preview", "T04-production", "T04c-custom-1", "T20", "T21"):
            self.assertEqual(statuses.get(op), "done", op)
        # T01: the dated tag at the remote is the head T01s scanned, one push, no local tag
        self.assertEqual(provlib.remote_head(m, ref=TAG), commit)
        self.assertEqual(provlib.git(repo if os.path.isdir(repo) else os.path.join(m.archive, "demo"), "tag", "--list"), "")
        # T03: the whole database, owner-only, its inventory pg_dump's own CREATE TABLE lines, the source read before the copy
        dump = os.path.join(folder(m), "demo-db.sql")
        self.assertEqual(stat.S_IMODE(os.stat(dump).st_mode), 0o600)
        text = read_file(dump)
        self.assertTrue(text.endswith("-- PostgreSQL database dump complete\n--\n\n"))
        done = completion(m, run, "T03")
        self.assertEqual(record(m, run, done["keep"]["inventory"]), ["CREATE TABLE public.alpha (", "CREATE TABLE public.beta ("])
        self.assertEqual(record(m, run, done["keep"]["source"]), "7000000000000000001")
        pg = [c["command"] for c in provlib.calls(m, "pg")]
        # the look's read of the dump's scope (G25-3), then the source's identity just before the copy (A147), one dump
        self.assertEqual(pg, ["psql", "psql", "pg_dump"])
        self.assertTrue(all(c["service_mode"] == "0o600" and c["service_keys"] == ["dbname", "host", "password", "port", "user"]
                            for c in provlib.calls(m, "pg")))
        self.assertNowhere(password, went)
        # T04: each environment saved owner-only; the Sensitive key listed apart, by key, never by value
        for env in provlib.ALL_ENVS:
            saved = os.path.join(folder(m), "hosting-env." + env)
            self.assertEqual(stat.S_IMODE(os.stat(saved).st_mode), 0o600)
            self.assertIn('FEATURE="on"', read_file(saved))
            kept = completion(m, run, "T04-" + env)["keep"]
            self.assertEqual(sorted(record(m, run, kept["inventory"])), ["DATABASE_URL", "FEATURE"])
            self.assertEqual(record(m, run, kept["apart"]), ["SIGNING_KEY"])
            self.assertEqual(record(m, run, kept["source"]), "prj_fixture1")
        # T04c: the custom environment by its label, its pairs written by the frame and decoding back whole
        custom = os.path.join(folder(m), "hosting-env.custom-1")
        self.assertEqual(effects.decode_pairs(read_file(custom, "rb")), [["STAGE_ONLY", "staging-value-1"]])
        self.assertTrue(any(r.get("query") == ["customEnvironmentId", "decrypt", "slug"] for r in provlib.requests(m, "GET")))
        # T20: archived, once
        self.assertEqual(provlib.state(m, "gh")["things"]["demo"]["state"], "archived")
        self.assertEqual(provlib.state(m, "gh")["sets"], [{"name": "demo", "state": "archived"}])
        # T21: paused, once, by the project's id `look` read, sent back to vercel alone (SEC-2), the id in no journal record
        host = provlib.state(m, "vercel")
        self.assertEqual(host["things"]["demo"]["state"], "paused")
        self.assertEqual(host["sets"], [{"name": "demo", "state": "paused"}])
        self.assertEqual([r["path"] for r in provlib.requests(m, "POST")], [["v1", "projects", "prj_fixture1", "pause"]])
        self.assertNotIn("prj_fixture1", json.dumps(m.journal(run)))
        status = "".join(read_file(p) for p in went.doc["forms"])
        self.assertIn("Saved copies: hosting env values of development, owner-only", status)
        # the join's punch list (b), the reviewer's P4: T03's line says that no test load ran (rows-prov section 5's Backup
        # line; its table count and its empty-database words are Machinery request 3)
        self.assertIn("[T03] done: Backup: dump the whole database to the sunset folder. A test load was not done.", status)
        self.assertNotIn("prj_fixture1", status)
        with open(os.path.join(os.environ.get("SUN_V2_PROV_FORMS", m.root), "set-forms-2.txt"), "w") as fh:
            fh.write(preview + "\n=====\n" + status + "\n=====\n" + tombstone(m, run))

    def test_V10_V11_EV4_EV5_G23_5_restore_offers_T20s_and_T21s_ways_back_un_archives_and_un_pauses_by_the_saved_id(self):
        m = world(self)
        _looked, went = started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(provlib.state(m, "vercel")["things"]["demo"]["state"], "paused")
        looked = lib.look(m, "restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        preview = read_file(looked.doc["forms"][0])
        self.assertIn("GitHub: un-archive fixture-account/demo", preview)
        self.assertIn("Hosting: un-pause", preview)
        self.assertNotIn("prj_fixture1", preview)
        back = lib.go(m, looked, "restore")
        self.assertEqual(back.ending, "complete", back.text)
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual((statuses.get("V10"), statuses.get("V11")), ("done", "done"))
        gh = provlib.state(m, "gh")
        self.assertEqual(gh["things"]["demo"]["state"], "active")
        self.assertEqual(gh["sets"], [{"name": "demo", "state": "archived"}, {"name": "demo", "state": "active"}])
        host = provlib.state(m, "vercel")
        self.assertEqual(host["things"]["demo"]["state"], "active")
        self.assertEqual(host["sets"], [{"name": "demo", "state": "paused"}, {"name": "demo", "state": "active"}])
        # V11's unpause went to vercel with T21's saved id, the copy mapped to its issuer (G23-5), and nowhere else
        self.assertEqual([r["path"] for r in provlib.requests(m, "POST")][-1], ["v1", "projects", "prj_fixture1", "unpause"])
        self.assertNowhere("prj_fixture1", back)
        self.assertTrue(os.path.isdir(m.path("dev", "demo")))           # V01s put the repository back first (ORD-4)
        status = "".join(read_file(p) for p in back.doc["forms"])
        with open(os.path.join(os.environ.get("SUN_V2_PROV_FORMS", m.root), "restore-forms-2.txt"), "w") as fh:
            fh.write(preview + "\n=====\n" + status)

    def test_T01_ORD1_OP8_G23_1_the_tag_is_the_commit_the_scan_passed_on_and_sunset_tag_carries_ref_and_commit(self):
        """T01 on G23-1: T01s, a check of the repository's head, binds `tag scan.commit` at its pass; T01 pushes that commit
        to the dated tag and gives slice 4 `sunset tag` {ref, commit}."""
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from sun_core import journal as journalmod, state as statemod
        m = world(self)
        repo, commit, _ = m.world_made
        looked, went = started(m, keep_db=True, keep_vercel=True)
        self.assertEqual(went.ending, "complete", went.text)
        run = looked.doc["run"]
        with open(os.path.join(m.facts.run_dir(run), "manifest-1.json")) as fh:
            manifest = json.load(fh)
        bound = statemod.State(manifest, journalmod.Journal(m.facts.run_dir(run), m.journal(run))).outputs
        self.assertEqual(bound["tag scan"], {"commit": commit})
        self.assertEqual(bound["sunset tag"], {"ref": TAG, "commit": commit})
        self.assertEqual(provlib.remote_head(m, ref=TAG), commit)


class PunchList(harness.Case):
    def test_P4_T01s_FORM2_a_scan_that_stops_the_run_has_a_line_that_does_not_say_the_commits_are_clear(self):
        """The join's punch list (b), the reviewer's P4 on T01s: a commit the tag push would send holds the env file's value;
        the scan fails and the run stops before any push, and T01s's line in the status form does not say the commits hold no
        guarded value (rows-prov section 5's two lines, one per outcome, are Machinery request 3)."""
        m = world(self)
        repo, _commit, password = m.world_made
        m.put("dev/demo/notes.txt", "the url: %s\n" % password)
        provlib.git(repo, "add", "notes.txt")
        provlib.git(repo, "commit", "-q", "-m", "notes")
        looked = lib.look(m, flags={"archive_as_is": True})          # G8 would ask about the unpushed commit
        self.assertEqual(looked.ending, "preview", looked.text)
        went = lib.go(m, looked)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertNotEqual(m.statuses(looked.doc["run"]).get("T01s"), "passed")
        self.assertIsNone(provlib.remote_head(m, ref=TAG))
        status = "".join(read_file(p) for p in went.doc["forms"])
        t01s = [line for line in status.split("\n") if line.startswith("[T01s]")]
        self.assertEqual(len(t01s), 1, status)
        self.assertNotIn("hold no value", t01s[0])
        self.assertNowhere(password, went)


class RequiredItems(harness.Case):
    def test_required_1_T04_RK19_SEC4_a_saved_value_under_eight_bytes_is_saved_whole_and_makes_no_register_entry(self):
        """`FEATURE=on`, two bytes: saved whole in each environment's copy, and the lines holding "on" go out as they stand
        (an entry in the register would withhold every one of them: the status form would be the register's words)."""
        m = world(self)
        looked, went = started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertIn('FEATURE="on"', read_file(os.path.join(folder(m), "hosting-env.production")))
        status = "".join(read_file(p) for p in went.doc["forms"])
        self.assertIn("[T04-production] done: Saved copies: hosting env values of production, owner-only", status)
        self.assertNotIn("a value this run held as safe is withheld", status)

    def test_required_2_N3_T04c_G19_29_her_case_decodes_from_the_kept_copy_to_exactly_the_answers_pairs(self):
        """The reviewer's N3 on T04c: a value holding a line break and then `OTHER=1`, a quote, a backslash and an empty value;
        the frame's reversible encoding (G19-29) writes one line each, and decoding the kept copy gives back exactly the
        answer's pairs."""
        pairs = [["SPLIT", "a long first line\nOTHER=1"], ["QUOTED", 'say "hi" there'], ["SLASHED", "back\\slash value"], ["EMPTY", ""]]
        m = world(self, custom=[{"id": "env_customone", "slug": "staging"}])
        state = provlib.state(m, "vercel")
        state["envs"]["demo"] += [{"key": k, "value": v, "type": "encrypted", "custom": "env_customone"} for k, v in pairs]
        provlib.put_state(m, "vercel", envs=state["envs"])
        looked, went = started(m)
        self.assertEqual(went.ending, "complete", went.text)
        data = read_file(os.path.join(folder(m), "hosting-env.custom-1"), "rb")
        self.assertEqual(data.count(b"\n"), 4)                       # one line each: no `OTHER` entry of its own
        self.assertEqual(effects.decode_pairs(data), pairs)
        self.assertEqual(record(m, looked.doc["run"], completion(m, looked.doc["run"], "T04c-custom-1")["keep"]["inventory"]),
                         ["SPLIT", "QUOTED", "SLASHED", "EMPTY"])

    def test_required_2_N3_T04_her_case_in_the_pulled_copy_is_one_entry_and_a_raw_line_break_fails_the_keep(self):
        """T04's copy is the provider's own pull (the CLI writes it, D10): her value is one quoted line there, the copy's keys
        equal the returned keys, and the keep is whole; a copy whose value broke onto a line of its own shows a key the listing
        never returned, and the keep fails and stops the run before anything is retired."""
        every = provlib.ALL_ENVS
        m = world(self, values=[{"key": "SPLIT", "value": "a long first line\nOTHER=1", "type": "encrypted", "target": every},
                                {"key": "QUOTED", "value": 'say "hi" \\ there', "type": "encrypted", "target": every},
                                {"key": "EMPTY", "value": "", "type": "encrypted", "target": every}])
        looked, went = started(m, keep_db=True, keep_github=True)
        self.assertEqual(went.ending, "complete", went.text)
        kept = completion(m, looked.doc["run"], "T04-production")["keep"]
        self.assertEqual(sorted(record(m, looked.doc["run"], kept["inventory"])), ["EMPTY", "QUOTED", "SPLIT"])
        # the raw break: the pulled copy holds `OTHER` as a key of its own, which no listing returned
        m2 = world(self, "h2", "h2", values=[{"key": "SPLIT", "value": "a long first line\nOTHER=1", "type": "encrypted", "target": every}])
        provlib.plan(m2, "vercel", {"command": "env-pull", "nth": 1, "do": "raw-break"})
        looked2, went2 = started(m2, keep_db=True, keep_github=True)
        self.assertEqual(went2.ending, "stopped", went2.text)
        stop = [r for r in m2.journal(looked2.doc["run"]) if r["kind"] == "invocation-end"][-1]["reason"]
        self.assertEqual(stop, {"kind": "the keep is not whole", "op": "T04-development"})


class PartTwo(harness.Case):
    def test_T04_KEEP1_A149_G23_6_a_variable_that_targets_another_environment_only_is_in_that_keep_alone(self):
        """Part one's machinery request 10, met by G23-6: each T04's two-read inventory takes only the keys whose targets hold
        its environment, so a variable of preview alone is in preview's copy and inventory and in neither of the others, and
        every keep is whole."""
        every = provlib.ALL_ENVS
        m = world(self, values=[{"key": "FEATURE", "value": "on", "type": "plain", "target": every},
                                {"key": "PREVIEW_ONLY", "value": "preview-value-1", "type": "encrypted", "target": ["preview"]}])
        looked, went = started(m, keep_db=True, keep_github=True)
        self.assertEqual(went.ending, "complete", went.text)
        for env in every:
            kept = completion(m, looked.doc["run"], "T04-" + env)["keep"]
            want = ["FEATURE", "PREVIEW_ONLY"] if env == "preview" else ["FEATURE"]
            self.assertEqual(sorted(record(m, looked.doc["run"], kept["inventory"])), want, env)
            self.assertEqual("PREVIEW_ONLY=" in read_file(os.path.join(folder(m), "hosting-env." + env)), env == "preview", env)

    def test_T04c_KEEP1_A148_G23_7_a_sensitive_custom_member_is_set_apart_by_key_and_the_keep_is_whole(self):
        """Part one's machinery request 11, met by G23-7: a custom environment's Sensitive member is returned with no value;
        T04c's pairs read takes the members whose value is returned, the Sensitive one is set apart by its type, and the keep
        is whole: the copy decodes to the returned pair alone, its `apart` record names the Sensitive key."""
        m = world(self, custom=[{"id": "env_customone", "slug": "staging"}])
        state = provlib.state(m, "vercel")
        state["envs"]["demo"] += [{"key": "STAGE_ONLY", "value": "staging-value-1", "type": "encrypted", "custom": "env_customone"},
                                  {"key": "STAGE_SECRET", "value": harness.canary("custom-sensitive"), "type": "sensitive",
                                   "custom": "env_customone"}]
        provlib.put_state(m, "vercel", envs=state["envs"])
        looked, went = started(m, keep_db=True, keep_github=True)
        self.assertEqual(went.ending, "complete", went.text)
        kept = completion(m, looked.doc["run"], "T04c-custom-1")["keep"]
        self.assertEqual(effects.decode_pairs(read_file(os.path.join(folder(m), "hosting-env.custom-1"), "rb")),
                         [["STAGE_ONLY", "staging-value-1"]])
        self.assertEqual(record(m, looked.doc["run"], kept["apart"]), ["STAGE_SECRET"])
        self.assertEqual(record(m, looked.doc["run"], kept["inventory"]), ["STAGE_ONLY"])

    def test_T04_T04c_SEC6_A148_G23_8_the_sensitive_keys_are_named_by_key_in_the_preview_and_in_the_tombstone(self):
        """Part one's machinery request 12, met by G23-8: each T04's Sensitive keys are named by key, never by value, as not
        saved, in the sunset preview (the look's read of the keys) and in the tombstone (slice 4's T30, as shipped); T04c's,
        set apart at the keep, in the tombstone. The line is this lane's (rows-prov section 5)."""
        m = world(self, custom=[{"id": "env_customone", "slug": "staging"}])
        state = provlib.state(m, "vercel")
        sensitive = harness.canary("custom-sensitive")
        state["envs"]["demo"] += [{"key": "STAGE_ONLY", "value": "staging-value-1", "type": "encrypted", "custom": "env_customone"},
                                  {"key": "STAGE_SECRET", "value": sensitive, "type": "sensitive", "custom": "env_customone"}]
        provlib.put_state(m, "vercel", envs=state["envs"])
        looked = look(m, keep_db=True, keep_github=True)
        self.assertEqual(looked.ending, "preview", looked.text)
        preview = read_file(looked.doc["forms"][0])
        for env in provlib.ALL_ENVS:
            self.assertIn(NOT_SAVED % ("SIGNING_KEY", "Saved copies: hosting env values of %s, owner-only" % env), preview)
        self.assertNotIn("FEATURE", preview)
        went = lib.go(m, looked)
        self.assertEqual(went.ending, "complete", went.text)
        tomb = tombstone(m, looked.doc["run"])
        for env in provlib.ALL_ENVS:
            self.assertIn(NOT_SAVED % ("SIGNING_KEY", "Saved copies: hosting env values of %s, owner-only" % env), tomb)
        self.assertIn(NOT_SAVED % ("STAGE_SECRET", "Saved copies: hosting env values of custom environment custom-1, owner-only"), tomb)
        self.assertNotIn(sensitive, tomb)
        self.assertNowhere(sensitive, went)


class Stops(harness.Case):
    def test_T03_KEEP1_KEEP3_G23_9_a_dump_cut_off_fails_the_keep_when_it_is_built_and_is_never_published(self):
        """Part one's machinery request 8, met by G23-9: pg_dump's last line is checked as the keep is built, so a cut copy is
        never published and the run stops at T03 itself, before anything is retired (part one's test, which stopped at the
        barrier before T20 with the cut copy published, now passes on the mechanism)."""
        m = world(self)
        provlib.plan(m, "pg", {"command": "pg_dump", "nth": 1, "do": "short"})
        looked, went = started(m)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(stop_of(m, looked.doc["run"]), {"kind": "the keep is not whole", "op": "T03"})
        self.assertFalse(os.path.exists(os.path.join(folder(m), "demo-db.sql")))
        self.assertEqual(provlib.state(m, "gh")["things"]["demo"]["state"], "active")
        self.assertEqual(provlib.calls(m, "gh", "archive-set"), [])

    def test_T03_KEEP1_G23_9_a_table_created_in_the_copy_without_its_data_section_fails_the_keep_and_nothing_is_published(self):
        """Rows-prov T03: "each table the copy creates has its data section in the copy": a copy with `CREATE TABLE
        public.beta` and no `COPY public.beta` section fails the keep (G23-9's `has-section`, the whole name as F2 reads it)."""
        for drop, ending in ((None, "complete"), ("beta", "stopped")):
            with self.subTest(drop=drop):
                m = world(self, "d%s" % drop, "d%s" % drop)
                if drop:
                    provlib.plan(m, "pg", {"command": "pg_dump", "nth": 1, "drop": drop})
                looked, went = started(m, keep_vercel=True, keep_github=True)
                self.assertEqual(went.ending, ending, went.text)
                self.assertEqual(os.path.exists(os.path.join(folder(m), "demo-db.sql")), drop is None)
                if drop:
                    self.assertEqual(stop_of(m, looked.doc["run"]), {"kind": "the keep is not whole", "op": "T03"})

    def test_P3_T03_KEEP1_RUN7_G25_3_a_table_the_role_cannot_read_refuses_the_look_before_approval(self):
        """The reviewer's P3, T03's own scope check, on G25-3: T03's `scope` read (`inventory` `unreadable` equal 0) refers to
        nothing the plan makes, so the look reads it though the dump's place is in the sunset folder the plan is to make; a
        table the role cannot read ends the look as KEEP-1's planning stop, before any approval (was: stopped at the dump)."""
        m = world(self)
        provlib.put_state(m, "pg", unreadable=["beta"])
        looked = look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the whole scope of a keep cannot be read or established: row T03", looked.text)
        self.assertEqual([c["command"] for c in provlib.calls(m, "pg")], ["psql"])      # no dump
        self.assertFalse(os.path.exists(folder(m)))
        self.assertNotIn("beta", looked.text)

    def test_T04_KEEP1_A149_a_key_added_during_the_pull_fails_the_keep(self):
        m = world(self)
        provlib.plan(m, "vercel", {"command": "env-pull", "nth": 1,
                                   "then_add": {"key": "LATE", "value": "late-value-1", "type": "encrypted", "target": provlib.ALL_ENVS}})
        looked, went = started(m, keep_db=True, keep_github=True)
        self.assertEqual(went.ending, "stopped", went.text)
        stop = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "invocation-end"][-1]["reason"]
        self.assertEqual(stop, {"kind": "the keep is not whole", "op": "T04-development"})

    def test_P3_T04_KEEP1_RUN7_G25_3_a_listing_already_known_to_be_paged_or_hiding_values_refuses_the_look(self):
        """The reviewer's P3 on G25-3: T04's `scope` reads (the project read, `env-keys` `next` present false, `hidden` 0,
        rows-prov T04 entry 3) are read at the look though its place is the plan's to make; a paged listing, or one that hides
        production values, ends the look before any approval, nothing pulled (was: a preview, then a stop at the probe)."""
        for label, fields in (("paged", {"next": 2}), ("hidden", {"hidden": 1})):
            with self.subTest(case=label):
                m = world(self, label, label)
                provlib.put_state(m, "vercel", **fields)
                looked = look(m, keep_db=True, keep_github=True)
                self.assertEqual(looked.ending, "refused", looked.text)
                self.assertIn("the whole scope of a keep cannot be read or established: row T04-", looked.text)
                self.assertEqual(provlib.calls(m, "vercel", "env-pull"), [])
                self.assertFalse(os.path.exists(folder(m)))

    def test_T20_RUN7_G10_a_repository_found_archived_is_already_so_and_no_archive_call_is_made(self):
        m = world(self)
        provlib.put_state(m, "gh", things={"demo": {"id": "R_fixturerepo1", "kind": "repo", "state": "archived", "name": "demo"}})
        looked = look(m, keep_db=True, keep_vercel=True)
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("found already so; a restore will not reverse it: GitHub: archive <account>/<name> (read-only)",
                      read_file(looked.doc["forms"][0]))
        went = lib.go(m, looked)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(provlib.calls(m, "gh", "archive-set"), [])

    def test_T04c_G19_7_G23_3_the_shipped_family_read_is_made_after_the_identity_reads_and_the_look_builds(self):
        """Part one's machinery request 3, met by G23-3: the shipped T04c's `environments` read carries the team, an account
        mark, and is made after vercel's identity reads, so it settles and the sunset look builds where hosting is saved (part
        one's test of the refused look now passes on the mechanism); where hosting is kept, T04c is not read and is listed
        not applicable."""
        m = world(self, custom=[{"id": "env_customone", "slug": "staging"}])
        looked = look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        gets = [r["path"] for r in provlib.requests(m, "GET")]
        envs = gets.index(["v9", "projects", "demo", "custom-environments"])
        self.assertLess(gets.index(["v2", "teams", provlib.TEAM]), envs, "the family was read before the identity read")
        self.assertIn("Saved copies: hosting env values of custom environment custom-1, owner-only", read_file(looked.doc["forms"][0]))
        self.assertEqual(provlib.requests(m, "POST"), [])
        m2 = world(self, "h2", "h2", custom=[{"id": "env_customone", "slug": "staging"}])
        kept = look(m2, keep_vercel=True)
        self.assertEqual(kept.ending, "preview", kept.text)
        self.assertNotIn(["v9", "projects", "demo", "custom-environments"], [r["path"] for r in provlib.requests(m2, "GET")])

    def test_T01_OP5_OP6_G24_1_a_tag_another_pushed_on_another_commit_is_foreign_the_run_stops_and_no_push_is_made(self):
        """G24-1 (part two's Question 2): T01's after-test and after-check are rows-prov's equality, the tag's `head` equal to
        `tag scan.commit`. A tag of that name pushed by another on another commit before the go: after-test false (an equality
        on the field holds a commit, not the scanned one), before-test false (the tag stands), `foreign` (OP-5), which stops
        (OP-6); before, on the tag's presence, it read `already so` and the run ended complete. The fresh tag, made and pushed,
        is `EndToEnd.test_T01_ORD1_OP8_G23_1_...` and the end-to-end run, on the same shipped row."""
        m = world(self)
        repo, commit, _ = m.world_made
        provlib.git(repo, "checkout", "-q", "-b", "other")
        m.put("dev/demo/other.txt", "another's\n")
        provlib.git(repo, "add", "other.txt")
        provlib.git(repo, "commit", "-q", "-m", "another's")
        theirs = provlib.git(repo, "rev-parse", "HEAD")
        provlib.git(repo, "push", "-q", "origin", "%s:%s" % (theirs, TAG), home=m.home)
        provlib.git(repo, "checkout", "-q", "main")
        provlib.git(repo, "branch", "-q", "-D", "other")
        looked, went = started(m, keep_db=True, keep_vercel=True)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("foreign", went.text)
        run = looked.doc["run"]
        self.assertEqual(m.statuses(run).get("T01s"), "passed")
        self.assertNotIn("T01", m.statuses(run), "the tag of another commit was given a status")
        self.assertEqual([r["kind"] for r in m.journal(run) if r.get("op") == "T01" and r["kind"] in ("start", "status")], [],
                         "T01 was started or given a status")
        self.assertEqual(provlib.remote_head(m, ref=TAG), theirs)
        self.assertNotEqual(theirs, commit)
        self.assertNotEqual(provlib.state(m, "gh")["things"]["demo"]["state"], "archived")      # nothing after T01 ran
        # the shipped row's after-test and after-check, rows-prov's T01 entries 5 and 9
        t01 = sunset_row("T01")
        equality = {"read": "command", "command": "look", "result": "success", "field": "head", "equals": {"output": "tag scan.commit"}}
        self.assertEqual((t01["after_test"], t01["after_check"]), ([equality], [equality]))

    def test_T21_RUN7_G10_a_project_found_paused_is_already_so_and_no_pause_is_sent(self):
        m = world(self)
        state = provlib.state(m, "vercel")
        state["things"]["demo"]["state"] = "paused"
        provlib.put_state(m, "vercel", things=state["things"])
        looked = look(m, keep_db=True, keep_github=True)
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("found already so; a restore will not reverse it: Hosting: pause <slug> (production blocked, reversible)",
                      read_file(looked.doc["forms"][0]))
        went = lib.go(m, looked)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(provlib.requests(m, "POST"), [])

    def test_T21_KEEP2_KEEP3_a_hosting_keep_that_fails_stops_the_run_and_the_project_is_not_paused(self):
        m = world(self)
        provlib.plan(m, "vercel", {"command": "env-pull", "nth": 3,
                                   "then_add": {"key": "LATE", "value": "late-value-1", "type": "encrypted", "target": provlib.ALL_ENVS}})
        looked, went = started(m, keep_db=True, keep_github=True)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(provlib.state(m, "vercel")["things"]["demo"]["state"], "active")
        self.assertEqual(provlib.requests(m, "POST"), [])

    def test_seam_item4_ORD1_T20_and_T21_need_repository_moved_at_the_level_slice_4s_check_gives_it(self):
        """Item 4: slice 4 gives `repository moved` as a check's output (T12m), met at `passed` (lane-report-set item 5); T20's
        and T21's needs on it are written at that level, and slice 4's shipped check passes before either runs."""
        for rid in ("T20", "T21"):
            r = sunset_row(rid)
            self.assertIn({"output": "repository moved", "level": "passed", "treatment": "then not needed"}, r["needs"], rid)
        m = world(self)
        looked, went = started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"]).get("T12m"), "passed")



class FixRound(harness.Case):
    """The reviewer's code check, P1 (ROW-1, GOV-1, EV-1, EV-4): the reverses compare the identity their forward row saved.
    T20 saves the repository's held id beside its name (T21 already saves the project's id); V10 and V11 read the thing and
    hold its `id` equal in memory to that saved id in their planning test, before-test and after-check (rows-prov V10 entry
    9 and V11 entry 9), so a thing replaced under the same name between the sunset and the restore is never acted on."""

    def test_P1_V10_GOV1_EV4_a_repository_replaced_under_its_name_between_sunset_and_restore_is_never_unarchived(self):
        m = world(self)
        _looked, went = started(m, keep_db=True, keep_vercel=True)
        self.assertEqual(went.ending, "complete", went.text)
        things = provlib.state(m, "gh")["things"]
        things["demo"]["id"] = "R_replacement1"                 # another repository, archived, under the same name
        provlib.put_state(m, "gh", things=things)
        looked = lib.look(m, "restore")
        self.assertNotEqual(looked.ending, "preview", looked.text)
        self.assertIn("row V10", looked.text)
        self.assertEqual(len(provlib.calls(m, "gh", "archive-set")), 1, "the replacement was un-archived")
        self.assertEqual(provlib.state(m, "gh")["things"]["demo"]["state"], "archived")

    def test_P1_V11_GOV1_EV4_a_project_that_answers_with_another_id_than_the_saved_one_is_never_unpaused(self):
        m = world(self)
        _looked, went = started(m, keep_db=True, keep_github=True)
        self.assertEqual(went.ending, "complete", went.text)
        original = m.transport

        class OtherId(object):
            """The host answers the project read with another project's id (a project replaced under the name)."""
            def request(self, host, method, path, headers, timeout, body=None):
                code, data = original.request(host, method, path, headers, timeout, body)
                if method == "GET" and path.split("?")[0].strip("/").split("/")[:2] == ["v9", "projects"] and code == 200:
                    found = json.loads(data.decode())
                    if "id" in found:
                        found["id"] = "prj_replacement1"
                        data = json.dumps(found).encode()
                return code, data
        m.transport = OtherId()
        looked = lib.look(m, "restore")
        self.assertNotEqual(looked.ending, "preview", looked.text)
        self.assertIn("row V11", looked.text)
        self.assertEqual([r["path"][-1] for r in provlib.requests(m, "POST")], ["pause"], "an unpause was sent")
        self.assertEqual(provlib.state(m, "vercel")["things"]["demo"]["state"], "paused")



def replace_at(m, provider, new_id, state=None):
    """Another thing under the same name at the fake host: its id `new_id`, and, where given, its state."""
    things = provlib.state(m, provider)["things"]
    things["demo"]["id"] = new_id
    if state:
        things["demo"]["state"] = state
    provlib.put_state(m, provider, things=things)


def replace_after_keeps(m, new_id, state=None):
    """For T21: the project replaced at the host under its name once the three hosting keeps have pulled (a replacement
    before them breaks the link file the pull goes by, and the keep stops first, which proves nothing of T21)."""
    original, done = m.transport, []

    class Replacing(object):
        def request(self, host, method, path, headers, timeout, body=None):
            if not done and len(provlib.calls(m, "vercel", "env-pull")) == 3:
                done.append(True)
                replace_at(m, "vercel", new_id, state)
            return original.request(host, method, path, headers, timeout, body)
    m.transport = Replacing()


class PartFour(harness.Case):
    """Part four, on G25: the reviewer's P1 forward half (T20, T21 on G25-1 and its fix round) and P2 (T21 on G25-2)."""

    def test_P1_T20_T21_GOV1_EV3_G25_1_a_thing_replaced_under_its_name_after_the_look_is_foreign_and_receives_no_effect(self):
        for provider, op in (("gh", "T20"), ("vercel", "T21")):
            with self.subTest(row=op):
                m = world(self, op, op)
                looked = look(m, keep_db=True, **({"keep_vercel": True} if op == "T20" else {"keep_github": True}))
                self.assertEqual(looked.ending, "preview", looked.text)
                if op == "T20":
                    replace_at(m, provider, "R_replacement1")
                else:
                    replace_after_keeps(m, "prj_replacement1")
                went = lib.go(m, looked)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn(op, went.text)
                self.assertIn("foreign" if op == "T20" else "the target is not the thing its keep copied", went.text)
                self.assertNotIn(op, m.statuses(looked.doc["run"]))
                self.assertEqual(provlib.state(m, provider)["things"]["demo"]["state"], "active")
                self.assertEqual(provlib.calls(m, "gh", "archive-set"), [])
                self.assertEqual(provlib.requests(m, "POST"), [])

    def test_P1_T20_T21_OP5_EV3_G25_R1_a_replacement_already_in_the_after_state_is_foreign_never_already_so(self):
        for provider, op, after in (("gh", "T20", "archived"), ("vercel", "T21", "paused")):
            with self.subTest(row=op):
                m = world(self, op, op)
                looked = look(m, keep_db=True, **({"keep_vercel": True} if op == "T20" else {"keep_github": True}))
                self.assertEqual(looked.ending, "preview", looked.text)
                if op == "T20":
                    replace_at(m, provider, "R_replacement1", state=after)
                else:
                    replace_after_keeps(m, "prj_replacement1", state=after)
                went = lib.go(m, looked)
                self.assertEqual(went.ending, "stopped", went.text)
                # T21's KEEP-2 tie, made before its probe, meets the replacement first (its keeps copied the planned project)
                self.assertIn("foreign" if op == "T20" else "the target is not the thing its keep copied", went.text)
                run = looked.doc["run"]
                self.assertNotIn(op, m.statuses(run))
                self.assertFalse([r for r in m.journal(run) if r.get("op") == op and r.get("status") == "already so"])
                self.assertEqual(provlib.calls(m, "gh", "archive-set"), [])
                self.assertEqual(provlib.requests(m, "POST"), [])

    def test_P1_T21_EV1_GOV1_G25_1_a_project_replaced_between_the_pause_and_its_confirming_read_fails_the_after_check(self):
        m = world(self)
        original = m.transport

        class Replacing(object):
            def request(self, host, method, path, headers, timeout, body=None):
                answer = original.request(host, method, path, headers, timeout, body)
                if method == "POST" and path.split("?")[0].endswith("/pause"):
                    replace_at(m, "vercel", "prj_replacement1")
                return answer
        m.transport = Replacing()
        looked, went = started(m, keep_db=True, keep_github=True)
        self.assertEqual(went.ending, "stopped", went.text)
        run = looked.doc["run"]
        self.assertNotIn(m.statuses(run).get("T21"), ("done", "already so"))
        self.assertFalse([r for r in m.journal(run) if r.get("op") == "T21" and r["kind"] == "completion"])
        # one pause, sent with the planned id, the project the look read
        self.assertEqual([r["path"] for r in provlib.requests(m, "POST")], [["v1", "projects", "prj_fixture1", "pause"]])

    def test_P2_T21_KEEP2_G25_2_the_pause_waits_on_every_custom_environments_keep_and_one_not_final_stops_it(self):
        m = world(self, custom=[{"id": "env_customone", "slug": "staging"}, {"id": "env_customtwo", "slug": "qa"}])
        state = provlib.state(m, "vercel")
        state["envs"]["demo"] += [{"key": "ONE", "value": "one-value-1", "type": "encrypted", "custom": "env_customone"},
                                  {"key": "TWO", "value": "two-value-1", "type": "encrypted", "custom": "env_customtwo"}]
        provlib.put_state(m, "vercel", envs=state["envs"])
        original = m.transport

        class SecondFails(object):
            """The host fails the read of the second custom environment's values: its keep is never final."""
            def request(self, host, method, path, headers, timeout, body=None):
                if method == "GET" and "customEnvironmentId=env_customtwo" in path:
                    return 500, b"{}"
                return original.request(host, method, path, headers, timeout, body)
        m.transport = SecondFails()
        looked = look(m, keep_db=True, keep_github=True)
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        with open(os.path.join(m.facts.run_dir(run), "manifest-1.json")) as fh:
            manifest = json.load(fh)
        t21 = [o for o in manifest["operations"] if o["id"] == "T21"][0]
        self.assertEqual(t21["keeps_required"], ["T04-development", "T04-preview", "T04-production", "T04c-custom-1",
                                                 "T04c-custom-2"])
        went = lib.go(m, looked)
        self.assertEqual(went.ending, "stopped", went.text)
        statuses = m.statuses(run)
        self.assertEqual(statuses.get("T04c-custom-1"), "done")
        self.assertNotEqual(statuses.get("T04c-custom-2"), "done")
        self.assertNotIn("T21", statuses)
        self.assertEqual(provlib.requests(m, "POST"), [])
        self.assertEqual(provlib.state(m, "vercel")["things"]["demo"]["state"], "active")

    def test_P2_T21_KEEP2_G25_2_a_custom_keep_whose_recorded_source_is_another_project_stops_the_pause(self):
        """Her custom-tie case: the project read just before the custom environment's copy answers another id, so that keep
        records another source; T21 compares each required keep's recorded source again before pausing, and stops."""
        m = world(self, custom=[{"id": "env_customone", "slug": "staging"}])
        state = provlib.state(m, "vercel")
        state["envs"]["demo"].append({"key": "ONE", "value": "one-value-1", "type": "encrypted", "custom": "env_customone"})
        provlib.put_state(m, "vercel", envs=state["envs"])
        original = m.transport

        class OtherSource(object):
            def request(self, host, method, path, headers, timeout, body=None):
                code, data = original.request(host, method, path, headers, timeout, body)
                pulled = len(provlib.calls(m, "vercel", "env-pull"))
                copied = any("customEnvironmentId" in r.get("query", []) for r in provlib.requests(m))
                if method == "GET" and path.split("?")[0].strip("/") == "v9/projects/demo" and pulled == 3 and not copied:
                    found = json.loads(data.decode())
                    found["id"] = "prj_other1"
                    data = json.dumps(found).encode()
                return code, data
        m.transport = OtherSource()
        looked, went = started(m, keep_db=True, keep_github=True)
        self.assertEqual(went.ending, "stopped", went.text)
        run = looked.doc["run"]
        self.assertEqual(m.statuses(run).get("T04c-custom-1"), "done")
        self.assertNotIn("T21", m.statuses(run))
        self.assertEqual(provlib.requests(m, "POST"), [])
        status = "".join(read_file(p) for p in went.doc["forms"])
        self.assertIn("T04c-custom-1", status)


if __name__ == "__main__":
    import unittest
    unittest.main()
