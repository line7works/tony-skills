"""The four carried items, fixed inside E12 (owner amendment A11, 2026-09-21).

The owner withdrew "Carry": items 1, 2, 3 and 5 of the control room's carry list are repaired
here rather than in E13. Item 4 (`survey --limit` bounds the output and not the work) is closed
as designed by A11 and has no test.

Each class below is one item, and each test is the defect turned into an assertion:

- **Item 1** — the two `--resolutions` refusals of `cmd_import_legacy` declared
  `report: "import"`, and so claimed `import-report.schema.json`, while fitting no branch of it.
  They are now one published branch, `resolutions_file_refused`, with its fields in
  `interface.md` and a valid and an invalid example. `TheRefusalSweep` is the wider pass the
  brief asks for: every refusal of every command that returns a body carrying `report` is
  triggered through the real CLI and validated.
- **Item 2** — `references/examples/import-report/valid/import-landed.json` carried a `head`
  from an older build. The example is regenerated from a live run, and this is the freshness
  test that keeps it honest: it compares the whole response, `head` included.
- **Item 3** — `validate-examples.py` read the `required` lists of the `state`, `import-report`
  and `resolutions` schemas out of the schema under test, so a required field removed from one
  of them removed the obligation to test it. Those lists are now pinned as literals, every list
  reached through an array inside `$defs` included, and each pin is proven by a mutation.
- **Item 5** — `records_core.importer.utc_now` used `datetime.utcnow()`, deprecated from 3.12.
  It now uses `datetime.now(timezone.utc)` and yields the byte-identical format.

Nothing here writes into the worktree: every fixture and every mutated schema is built under
`testlib.make_scratch` and removed again.
"""
import contextlib
import copy
import datetime
import importlib.util
import io
import json
import os
import shutil
import unittest
from unittest import mock

import testlib

testlib.add_scripts_to_path()
from records_core import events as events_mod, importer as importer_mod, validate  # noqa: E402

GRANTS = "docs/plans/2026-05-05-grants.md"
SHARED = "docs/plans/2026-05-03-join-ambiguous-shared.md"
IMPORT_REPORT_EXAMPLES = os.path.join(testlib.REFERENCES, "examples", "import-report")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def examples_module():
    """`validate-examples.py` as a module, so a mutation costs a call and not a process."""
    spec = importlib.util.spec_from_file_location("validate_examples", testlib.EXAMPLES_CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validator(root):
    """Run the example checker in process against a component root; (exit code, document)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = examples_module().main(["--component-root", root])
    return code, json.loads(out.getvalue())


def required_lists(schema):
    """Every `required` list in a schema, by JSON pointer, arrays inside `$defs` included."""
    found = {}

    def walk(node, pointer):
        if isinstance(node, dict):
            if isinstance(node.get("required"), list):
                found[pointer] = list(node["required"])
            for key, value in node.items():
                walk(value, pointer + "/" + key.replace("~", "~0").replace("/", "~1"))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, pointer + "/" + str(index))

    walk(schema, "")
    return found


def at_pointer(document, pointer):
    """The node a JSON pointer of the shape `required_lists` produces names."""
    node = document
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


# ---- item 5: `utc_now` reads the clock the way 3.12 onward wants it read ----------------------

class UtcNowIsTimezoneAware(unittest.TestCase):
    """Carry item 5. `datetime.utcnow()` is correct on the 3.9 floor and deprecated from 3.12."""

    MOMENT = (2026, 5, 20, 12, 0, 0)

    def test_utc_now_is_timezone_aware(self):
        self.assertIsNotNone(importer_mod.utc_now().tzinfo,
                             "utc_now() returns a naive datetime, so it read a deprecated clock")

    def test_no_module_calls_the_deprecated_clock(self):
        offenders = []
        for dirpath, dirnames, filenames in os.walk(testlib.ROOT):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                if os.path.abspath(path) == os.path.abspath(__file__):
                    continue  # this file names them to forbid them
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                for call in ("datetime.utcnow(", "datetime.utcfromtimestamp("):
                    if call in text:
                        offenders.append("%s: %s" % (os.path.relpath(path, testlib.ROOT), call))
        self.assertEqual(offenders, [])

    def test_the_stamp_and_the_run_id_are_byte_identical(self):
        naive = datetime.datetime(*self.MOMENT)
        aware = datetime.datetime(*self.MOMENT, tzinfo=datetime.timezone.utc)
        self.assertEqual(importer_mod.stamp(aware), importer_mod.stamp(naive))
        self.assertEqual(importer_mod.stamp(aware), "2026-05-20T12:00:00Z")
        self.assertEqual(importer_mod.run_id_for(GRANTS, aware),
                         importer_mod.run_id_for(GRANTS, naive))
        self.assertEqual(aware.strftime("%Y-%m-%d"), naive.strftime("%Y-%m-%d"))

    def test_the_clock_it_reads_is_utc_and_whole_seconds(self):
        moment = importer_mod.utc_now()
        self.assertEqual(moment.microsecond, 0)
        self.assertEqual(moment.utcoffset(), datetime.timedelta(0))
        # the same instant the deprecated call reported, to the second
        elsewhere = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        self.assertLess(abs((elsewhere - moment).total_seconds()), 5)

    def test_a_live_import_still_stamps_the_documented_shape(self):
        scratch = testlib.make_scratch("records-clock-")
        try:
            workspace = testlib.fixture_workspace(scratch)
            body = testlib.import_doc(workspace, GRANTS, now=importer_mod.utc_now())
            self.assertRegex(body["run_id"], r"^import-docs__plans__2026-05-05-grants-"
                                             r"[0-9]{8}T[0-9]{6}Z$")
            for event in testlib.events_of(workspace, GRANTS):
                if event["kind"] in ("log_opened", "import_started", "import_finished"):
                    self.assertRegex(event["at"], r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
                                                  r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
        finally:
            testlib.rmtree(scratch)


# ---- item 2: the shipped landed-import example reproduces from a live run ---------------------

STALE_LOCK = {"command": "import-legacy", "pid": 999999, "pid_start": "Wed Apr  1 09:00:00 2026"}
ORPHAN = ".docs__plans__2026-05-05-grants.events.jsonl.ci4o2fs.tmp"


class TheLandedImportExamplesAreFresh(unittest.TestCase):
    """Carry item 2. The example is a real response; a stale field in it is a false promise.

    The comparison is the WHOLE response, `head` included. `head` is the field that went stale:
    every other one reproduced, and nothing in the suite compared it, so the example kept a hash
    no build of this component has produced since. `import-recovered.json` is the same document's
    second pass and carries the same `head`; it is compared here for the same reason.
    """

    def setUp(self):
        self.scratch = testlib.make_scratch("records-fresh-")
        self.workspace = testlib.fixture_workspace(self.scratch)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def envelope(self, body):
        import records  # the CLI, for the envelope it puts around every body
        version = records.component_meta(testlib.COMPONENT)["version"]
        response = {"interface_version": records.INTERFACE_VERSION, "component_version": version}
        response.update(body)
        response.setdefault("ok", True)
        return response

    def import_kwargs(self):
        import records
        return {"component_version": records.component_meta(testlib.COMPONENT)["version"],
                "interface_version": records.INTERFACE_VERSION}

    def landed(self):
        """The example's own run: the fixture document, the fixed instant, through the library."""
        return self.envelope(testlib.import_doc(self.workspace, GRANTS, **self.import_kwargs()))

    def recovered(self):
        """`import-recovered.json`: a second pass that breaks a stale lock and finds no news."""
        self.landed()
        log = events_mod.log_path(self.workspace, GRANTS)
        testlib.write(events_mod.lock_path(log), json.dumps(STALE_LOCK, sort_keys=True))
        testlib.write(os.path.join(os.path.dirname(log), ORPHAN),
                      "an interrupted write left this behind\n")
        with mock.patch.object(events_mod, "holder_alive", lambda info: False):
            body = testlib.import_doc(self.workspace, GRANTS, break_lock=True,
                                      **self.import_kwargs())
        return self.envelope(body)

    def compare(self, name, live):
        shipped = load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid", name))
        for field in sorted(set(shipped) | set(live)):
            self.assertEqual(live.get(field), shipped.get(field), "%s: %s" % (name, field))
        self.assertEqual(live, shipped, name)

    def test_the_landed_example_reproduces_from_a_live_run(self):
        self.compare("import-landed.json", self.landed())

    def test_the_recovered_example_reproduces_from_a_live_run(self):
        self.compare("import-recovered.json", self.recovered())

    def test_the_comparison_covers_head(self):
        """A guard on the tests above: `head` is in the response, so it is in the comparison."""
        live = self.landed()
        self.assertIn("head", live)
        self.assertRegex(live["head"], r"^[0-9a-f]{64}$")

    def test_the_two_examples_agree_on_the_head(self):
        landed = load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid", "import-landed.json"))
        recovered = load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid", "import-recovered.json"))
        self.assertEqual(recovered["head"], landed["head"],
                         "the second pass appended nothing, so the head did not move")

    def test_the_examples_still_validate(self):
        for name in ("import-landed.json", "import-recovered.json"):
            shipped = load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid", name))
            self.assertEqual(
                validate.validate_document("import_report", shipped, testlib.schemas()), [], name)


PUNCH_LIST = "docs/punch-list.md"
STATE_EXAMPLES = os.path.join(testlib.REFERENCES, "examples", "state")


class TheStateExamplesAreFresh(unittest.TestCase):
    """Carry item 2, the same defect one schema over: three `state` examples of the same logs.

    `state.json` and `state-at-source.json` describe the log `import-landed.json` writes and
    carried its old `head`; `state-punch-list-has-no-card.json` carried the old head of the
    punch list's log. Every other field of all three reproduces. They are compared here so the
    shipped examples cannot drift apart again: an example of a log and an example of the import
    that wrote it have to agree about that log's head.
    """

    def setUp(self):
        self.scratch = testlib.make_scratch("records-state-")
        self.workspace = testlib.fixture_workspace(self.scratch)
        import records
        kwargs = {"component_version": records.component_meta(testlib.COMPONENT)["version"],
                  "interface_version": records.INTERFACE_VERSION}
        for doc in (GRANTS, PUNCH_LIST):
            testlib.import_doc(self.workspace, doc, **kwargs)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def live(self, argv):
        code, body, err = testlib.run_json(argv)
        self.assertEqual(code, 0, (body, err))
        return body

    def identity_file(self):
        return testlib.write_json(os.path.join(self.scratch, "identity.json"),
                                  self.live(["identity", "--workspace", self.workspace]))

    def compare(self, name, live):
        shipped = load(os.path.join(STATE_EXAMPLES, "valid", name))
        for field in sorted(set(shipped) | set(live)):
            self.assertEqual(live.get(field), shipped.get(field), "%s: %s" % (name, field))
        self.assertEqual(live, shipped, name)

    def test_the_state_example_reproduces_from_a_live_run(self):
        self.compare("state.json",
                     self.live(["state", "--workspace", self.workspace, "--doc", GRANTS]))

    def test_the_at_source_example_reproduces_from_a_live_run(self):
        self.compare("state-at-source.json",
                     self.live(["state", "--workspace", self.workspace, "--doc", GRANTS,
                                "--at-source", self.identity_file()]))

    def test_the_punch_list_example_reproduces_from_a_live_run(self):
        self.compare("state-punch-list-has-no-card.json",
                     self.live(["state", "--workspace", self.workspace, "--doc", PUNCH_LIST]))

    def test_the_state_examples_agree_with_the_import_example_on_the_head(self):
        landed = load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid", "import-landed.json"))
        for name in ("state.json", "state-at-source.json"):
            shipped = load(os.path.join(STATE_EXAMPLES, "valid", name))
            self.assertEqual(shipped["head"], landed["head"], name)
            self.assertEqual(shipped["log"], landed["log"], name)


# ---- item 3: the pinned `required` lists of the other three schemas ---------------------------

PINNED_SCHEMAS = {"state": "state.schema.json", "import_report": "import-report.schema.json",
                  "resolutions": "resolutions.schema.json"}


class ThePinnedRequiredListsAreLiterals(unittest.TestCase):
    """Carry item 3. An obligation a checker reads out of the thing it checks is no obligation.

    `validate-examples.py` pins the event schema's `required` lists to the contract. The other
    three were read from the schema under test, so removing a required field from one of them
    removed the obligation to test it and every mutation still passed. They are pinned the same
    way now, and this class proves each pin by removing a field from a scratch copy.
    """

    @classmethod
    def setUpClass(cls):
        cls.module = examples_module()

    def setUp(self):
        self.scratch = testlib.make_scratch("records-pins-")

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def copy_root(self):
        root = os.path.join(self.scratch, "records-%d" % len(os.listdir(self.scratch)))
        os.makedirs(root)
        shutil.copytree(os.path.join(testlib.COMPONENT, "references"),
                        os.path.join(root, "references"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        return root

    def pins_for(self, key):
        return self.module.SCHEMA_REQUIRED[key]

    def test_every_schema_has_a_pin_table(self):
        # The three document schemas carry the pins this item added; send-back 1 added the event
        # schema's beside them, and `NoRequiredListIsReadFromTheSchemaUnderTest` holds the set of
        # four.
        self.assertLessEqual(set(PINNED_SCHEMAS), set(self.module.SCHEMA_REQUIRED))

    def test_the_pins_name_every_required_list_in_each_schema(self):
        schemas = testlib.schemas()
        for key, filename in sorted(PINNED_SCHEMAS.items()):
            live = required_lists(schemas.docs[key])
            pinned = dict((pointer, list(fields))
                          for pointer, fields in self.pins_for(key).items())
            self.assertEqual(sorted(pinned), sorted(live), filename)
            for pointer in sorted(live):
                self.assertEqual(list(pinned[pointer]), live[pointer],
                                 "%s at %s" % (filename, pointer or "<root>"))

    def test_the_pins_are_not_read_out_of_the_schema(self):
        """The literals live in the source, not in a call that loads the schema."""
        with open(testlib.EXAMPLES_CLI, encoding="utf-8") as fh:
            source = fh.read()
        head = source.split("SCHEMA_REQUIRED = ", 1)[1]
        for key in sorted(PINNED_SCHEMAS):
            self.assertIn('"%s"' % key, head)
        for pointer in ("/$defs/ambiguity/properties/candidates/items",
                        "/$defs/answer/oneOf/2", "/$defs/location/properties/more/items"):
            self.assertIn(pointer, source, pointer)

    def test_removing_a_required_field_from_any_pinned_list_is_caught(self):
        """Every pin, one mutation each: the checker must exit non-zero and name the list."""
        failures = []
        for key, filename in sorted(PINNED_SCHEMAS.items()):
            for pointer, fields in sorted(self.pins_for(key).items()):
                if not fields:
                    continue
                root = self.copy_root()
                path = os.path.join(root, "references", filename)
                document = load(path)
                node = at_pointer(document, pointer)
                dropped = node["required"].pop(0)
                testlib.write(path, json.dumps(document, indent=2, ensure_ascii=False) + "\n")
                code, report = run_validator(root)
                if code == 0 or report["ok"]:
                    failures.append("%s at %s without %s is still accepted"
                                    % (filename, pointer or "<root>", dropped))
        self.assertEqual(failures, [])

    def test_an_untouched_copy_still_passes(self):
        code, report = run_validator(self.copy_root())
        self.assertEqual(code, 0, report["failures"])
        self.assertTrue(report["ok"])


# ---- item 1: the two `--resolutions` refusals are a published shape ---------------------------

class TheResolutionsFileRefusalsArePublished(unittest.TestCase):
    """Carry item 1. Both refusals declare `report: "import"` and fit no branch of the schema.

    They are raised by `cmd_import_legacy` before the importer reads a single answer, so they
    carry none of the plan's fields — the same class of defect as the reviewer's N1, one step
    earlier in the same command.
    """

    def setUp(self):
        self.scratch = testlib.make_scratch("records-refusal-")
        self.workspace = testlib.fixture_workspace(self.scratch)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def refuse(self, answers, name):
        path = testlib.write_json(os.path.join(self.scratch, name), answers)
        code, body, err = testlib.run_json(["import-legacy", "--workspace", self.workspace,
                                            "--doc", SHARED, "--resolutions", path])
        self.assertEqual(code, 4, (body, err))
        return body

    def schema_failure(self):
        return self.refuse({"answers": [{"line": 1}]}, "fails-its-own-schema.json")

    def other_document(self):
        return self.refuse({"answered_by": "the review", "answered_on": "2026-05-03",
                            "doc": "docs/plans/2026-05-01-l1-backticks.md",
                            "answers": [{"line": 16, "raw": "a line", "skip": True,
                                         "why": "the wrong document"}]},
                           "answers-another-document.json")

    def test_a_resolutions_file_that_fails_its_own_schema_validates(self):
        body = self.schema_failure()
        self.assertEqual(validate.validate_document("import_report", body, testlib.schemas()), [])

    def test_a_resolutions_file_that_answers_another_document_validates(self):
        body = self.other_document()
        self.assertEqual(validate.validate_document("import_report", body, testlib.schemas()), [])

    def test_the_schema_failure_names_every_error_the_schema_found(self):
        body = self.schema_failure()
        self.assertEqual(body["error"], "invalid")
        self.assertEqual(body["report"], "import")
        self.assertEqual(body["doc"], SHARED)
        self.assertEqual(body["log"], events_mod.log_relpath(SHARED))
        self.assertTrue(body["errors"])
        for entry in body["errors"]:
            self.assertEqual(sorted(entry), ["message", "path"])
        self.assertIn("resolutions.schema.json", body["reason"])

    def test_the_other_document_refusal_names_both_documents(self):
        body = self.other_document()
        self.assertNotIn("errors", body)
        self.assertIn("docs/plans/2026-05-01-l1-backticks.md", body["reason"])
        self.assertIn(SHARED, body["reason"])

    def test_dropping_a_required_field_makes_each_refusal_fail_the_schema(self):
        for body in (self.schema_failure(), self.other_document()):
            for field in ("ok", "report", "error", "reason", "doc", "log"):
                mutated = copy.deepcopy(body)
                mutated.pop(field)
                self.assertTrue(
                    validate.validate_document("import_report", mutated, testlib.schemas()),
                    "a refusal without /%s is still accepted" % field)

    def test_a_refusal_carrying_a_plan_field_is_not_this_branch(self):
        body = self.other_document()
        body["head"] = "0" * 64
        self.assertTrue(validate.validate_document("import_report", body, testlib.schemas()))

    def test_neither_refusal_wrote_anything(self):
        for body in (self.schema_failure(), self.other_document()):
            self.assertFalse(body["ok"])
            self.assertFalse(os.path.exists(events_mod.log_path(self.workspace, SHARED)))
        self.assertEqual(testlib.porcelain(self.workspace), [])

    def test_the_shipped_examples_cover_the_refusal(self):
        schemas = testlib.schemas()
        for name in ("resolutions-file-refused.json",
                     "resolutions-answers-another-document.json"):
            good = load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid", name))
            self.assertEqual(validate.validate_document("import_report", good, schemas), [], name)
        self.assertIn("errors", load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid",
                                                  "resolutions-file-refused.json")))
        self.assertNotIn("errors", load(os.path.join(
            IMPORT_REPORT_EXAMPLES, "valid", "resolutions-answers-another-document.json")))
        bad = load(os.path.join(IMPORT_REPORT_EXAMPLES, "invalid",
                                "resolutions-refusal-with-a-plan-field.json"))
        self.assertTrue(validate.validate_document("import_report", bad["document"], schemas))

    def test_the_shipped_examples_reproduce_from_a_live_run(self):
        import records
        version = records.component_meta(testlib.COMPONENT)["version"]
        for name, body in (("resolutions-file-refused.json", self.schema_failure()),
                           ("resolutions-answers-another-document.json", self.other_document())):
            shipped = load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid", name))
            self.assertEqual(body, shipped, name)
            self.assertEqual(shipped["component_version"], version, name)

    def test_the_interface_documents_the_refusal(self):
        with open(os.path.join(testlib.REFERENCES, "interface.md"), encoding="utf-8") as fh:
            text = fh.read()
        for phrase in ("resolutions_file_refused", "resolutions-file-refused.json"):
            self.assertIn(phrase, text, phrase)


class TheRefusalSweep(unittest.TestCase):
    """Every refusal that declares `report` is held to `import-report.schema.json`.

    The reading (the second fix round's Q3, unchanged): a response claims this schema when it
    carries `report`, because `report` is the schema's discriminator and every branch pins it
    with a `const`. The refusals that carry no `report` claim no branch; `interface.md`'s "Every
    response" and "Every command that walks a log" tables describe those, and this round does not
    invent a shape for them. The report lists them all.
    """

    def setUp(self):
        self.scratch = testlib.make_scratch("records-sweep-")
        self.workspace = testlib.fixture_workspace(self.scratch)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def cli(self, *args):
        return testlib.run_json([str(a) for a in args])

    def answers(self, name, document):
        return testlib.write_json(os.path.join(self.scratch, name), document)

    def cases(self):
        """(name, argv, expected exit) for every refusal of a command that returns a body."""
        ws = ["--workspace", self.workspace]
        bad = self.answers("bad.json", {"answers": [{"line": 1}]})
        other = self.answers("other.json",
                             {"answered_by": "x", "answered_on": "2026-05-03",
                              "doc": "docs/plans/2026-05-01-l1-backticks.md",
                              "answers": [{"line": 1, "raw": "a", "skip": True, "why": "b"}]})
        twice = self.answers("twice.json",
                             {"answered_by": "x", "answered_on": "2026-05-03",
                              "answers": [{"line": 16, "raw": "a", "skip": True, "why": "b"},
                                          {"line": 16, "raw": "a", "skip": True, "why": "c"}]})
        not_asked = self.answers("not-asked.json",
                                 {"answered_by": "x", "answered_on": "2026-05-03",
                                  "answers": [{"line": 1, "raw": "a", "skip": True, "why": "b"}]})
        return [
            ("import-legacy ambiguous document",
             ["import-legacy"] + ws + ["--doc", SHARED, "--dry-run"], 5),
            ("import-legacy ambiguous document, real",
             ["import-legacy"] + ws + ["--doc", SHARED], 5),
            ("import-legacy rejected resolution",
             ["import-legacy"] + ws + ["--doc", SHARED, "--resolutions", not_asked], 4),
            ("import-legacy duplicate answers",
             ["import-legacy"] + ws + ["--doc", SHARED, "--resolutions", twice], 4),
            ("import-legacy resolutions file fails its own schema",
             ["import-legacy"] + ws + ["--doc", SHARED, "--resolutions", bad], 4),
            ("import-legacy resolutions file answers another document",
             ["import-legacy"] + ws + ["--doc", SHARED, "--resolutions", other], 4),
        ]

    def test_every_refusal_that_declares_report_validates(self):
        schemas = testlib.schemas()
        failures = []
        for name, argv, expected in self.cases():
            code, body, err = self.cli(*argv)
            if code != expected:
                failures.append("%s: exit %s, expected %s (%s)" % (name, code, expected, err))
                continue
            if body is None or "report" not in body:
                failures.append("%s: no body carrying `report`" % name)
                continue
            errors = validate.validate_document("import_report", body, schemas)
            if errors:
                failures.append("%s: %s %s" % (name, errors[0]["path"] or "/",
                                               errors[0]["message"][:120]))
        self.assertEqual(failures, [])

    def test_a_survey_page_still_validates(self):
        code, body, err = self.cli("survey", "--workspace", self.workspace, "--limit", 2)
        self.assertEqual(code, 0, (body, err))
        body["workspace"] = "/workspace"
        self.assertEqual(validate.validate_document("import_report", body, testlib.schemas()), [])

    def test_the_refusals_that_carry_no_report_claim_no_branch(self):
        """The other half of the sweep, recorded: no `report`, so no branch of this schema."""
        cases = [
            ("verify a document under docs/records/",
             ["verify", "--workspace", self.workspace, "--doc", "docs/records/spec.md"], 4),
            ("state a verdict doc",
             ["state", "--workspace", self.workspace,
              "--doc", "docs/reviews/2026-05-15-signoff-mirrors-a.md"], 4),
            ("mirrors a document under docs/records/",
             ["mirrors", "--workspace", self.workspace, "--doc", "docs/records/spec.md"], 4),
        ]
        for name, argv, expected in cases:
            code, body, err = self.cli(*argv)
            self.assertEqual(code, expected, (name, body, err))
            self.assertNotIn("report", body or {}, name)
            self.assertFalse(body["ok"], name)
            self.assertIn("error", body, name)
            self.assertIn("reason", body, name)


# ==== send-back 1 (control room, 2026-09-21) ==================================================
# Two items from this round's "saw and did not touch" list, brought in because nothing carries
# out of E12: the event schema's nested `required` lists, and `broke_lock`'s type.


# ---- send-back item 2: `broke_lock` is typed ---------------------------------------------------

class BrokeLockIsTyped(unittest.TestCase):
    """`import-report.schema.json` typed `broke_lock` as `{"type": "object"}` and nothing else.

    `interface.md` names three fields (`pid`, `pid_start`, `command`), so any object at all
    passed — a `broke_lock` carrying a misspelled field, or a string where the pid goes, was
    accepted by the schema that is supposed to describe it. The real object is whatever the
    lock file held: this component's own lock is `{pid, pid_start, command}`, and the stand-in
    for a lock that could not be read is `{pid: null, pid_start: null, unreadable}`.
    """

    def setUp(self):
        self.scratch = testlib.make_scratch("records-brokelock-")
        self.workspace = testlib.fixture_workspace(self.scratch)
        self.log = events_mod.log_path(self.workspace, GRANTS)
        testlib.import_doc(self.workspace, GRANTS)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def break_a_lock(self, contents):
        """Leave `contents` in the lock file, then run a real `--break-lock` import."""
        testlib.write(events_mod.lock_path(self.log), contents)
        code, body, err = testlib.run_json(["import-legacy", "--workspace", self.workspace,
                                            "--doc", GRANTS, "--break-lock"])
        self.assertEqual(code, 0, (body, err))
        self.assertIn("broke_lock", body)
        return body

    def component_lock(self):
        return json.dumps({"pid": 999999, "pid_start": "Wed Apr  1 09:00:00 2026",
                           "command": "import-legacy"}, sort_keys=True)

    def test_the_real_broke_lock_of_this_components_own_lock_validates(self):
        body = self.break_a_lock(self.component_lock())
        self.assertEqual(sorted(body["broke_lock"]), ["command", "pid", "pid_start"])
        self.assertEqual(validate.validate_document("import_report", body, testlib.schemas()), [])

    def test_the_broke_lock_of_a_lock_that_could_not_be_read_validates(self):
        body = self.break_a_lock("[]")
        self.assertEqual(sorted(body["broke_lock"]), ["pid", "pid_start", "unreadable"])
        self.assertIsNone(body["broke_lock"]["pid"])
        self.assertEqual(validate.validate_document("import_report", body, testlib.schemas()), [])

    def test_a_broke_lock_with_a_misspelled_field_is_refused(self):
        body = self.break_a_lock(self.component_lock())
        body["broke_lock"] = dict(body["broke_lock"])
        body["broke_lock"]["pid_started"] = body["broke_lock"].pop("pid_start")
        self.assertTrue(validate.validate_document("import_report", body, testlib.schemas()),
                        "a broke_lock naming a field nothing documents is still accepted")

    def test_a_broke_lock_whose_pid_is_a_string_is_refused(self):
        body = self.break_a_lock(self.component_lock())
        body["broke_lock"] = dict(body["broke_lock"], pid="999999")
        self.assertTrue(validate.validate_document("import_report", body, testlib.schemas()),
                        "a broke_lock whose pid is a string is still accepted")

    def test_a_broke_lock_missing_the_pid_is_refused(self):
        body = self.break_a_lock(self.component_lock())
        body["broke_lock"] = {"command": "import-legacy"}
        self.assertTrue(validate.validate_document("import_report", body, testlib.schemas()),
                        "a broke_lock naming no pid is still accepted")

    def test_the_shipped_examples_cover_the_type(self):
        good = load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid", "import-recovered.json"))
        self.assertEqual(sorted(good["broke_lock"]), ["command", "pid", "pid_start"])
        self.assertEqual(validate.validate_document("import_report", good, testlib.schemas()), [])
        bad = load(os.path.join(IMPORT_REPORT_EXAMPLES, "invalid",
                                "broke-lock-with-a-field-nothing-documents.json"))
        self.assertTrue(validate.validate_document("import_report", bad["document"],
                                                   testlib.schemas()))

    def test_the_interface_names_every_field_the_real_object_can_carry(self):
        with open(os.path.join(testlib.REFERENCES, "interface.md"), encoding="utf-8") as fh:
            text = fh.read()
        seen = set()
        for contents in (self.component_lock(), "[]"):
            seen.update(self.break_a_lock(contents)["broke_lock"])
        for field in sorted(seen):
            self.assertIn("| `broke_lock.%s` |" % field, text, field)


# ---- send-back item 1: every `required` list of every schema is pinned -------------------------

ALL_SCHEMAS = {"event": "event.schema.json", "state": "state.schema.json",
               "import_report": "import-report.schema.json",
               "resolutions": "resolutions.schema.json"}


class NoRequiredListIsReadFromTheSchemaUnderTest(unittest.TestCase):
    """Send-back 1, item 1: the event schema's nested lists were the last unpinned ones.

    `CONTRACT_COMMON` and `CONTRACT_KIND_FIELDS` pinned the top-level list and the per-kind
    `then` lists; every other `required` list in `event.schema.json` — `$defs/actor`,
    `$defs/origin`'s two branches, `$defs/identity`, `$defs/location` and its `more` items,
    `$defs/source`'s two branches, `$defs/resolution_answer`'s three, and the `if` clause of
    every `allOf` rule — was read from the schema being checked.
    """

    @classmethod
    def setUpClass(cls):
        cls.module = examples_module()

    def setUp(self):
        self.scratch = testlib.make_scratch("records-eventpins-")

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def copy_root(self):
        root = os.path.join(self.scratch, "records-%d" % len(os.listdir(self.scratch)))
        os.makedirs(root)
        shutil.copytree(os.path.join(testlib.COMPONENT, "references"),
                        os.path.join(root, "references"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        return root

    def test_all_four_schemas_have_a_pin_table(self):
        self.assertEqual(sorted(self.module.SCHEMA_REQUIRED), sorted(ALL_SCHEMAS))

    def test_no_required_list_in_any_schema_file_is_unpinned(self):
        """Count every `required` list in every schema file; none may be missing from the pins."""
        unpinned = []
        counted = 0
        for key, filename in sorted(ALL_SCHEMAS.items()):
            live = required_lists(load(os.path.join(testlib.REFERENCES, filename)))
            counted += len(live)
            pinned = self.module.SCHEMA_REQUIRED[key]
            for pointer in sorted(live):
                if pointer not in pinned:
                    unpinned.append("%s at %s" % (filename, pointer or "the top level"))
                else:
                    self.assertEqual(list(pinned[pointer]), live[pointer],
                                     "%s at %s" % (filename, pointer or "the top level"))
            for pointer in sorted(pinned):
                self.assertIn(pointer, live, "%s pins a list that is gone: %s"
                              % (filename, pointer or "the top level"))
        self.assertEqual(unpinned, [])
        self.assertGreater(counted, 90, "the four schemas hold far more than a handful of lists")

    def test_the_event_kind_lists_agree_with_the_pins(self):
        """The two literal tables say the same thing, without either reading the schema."""
        pins = self.module.SCHEMA_REQUIRED["event"]
        self.assertEqual(list(self.module.CONTRACT_COMMON), list(pins[""]))
        then_lists = [tuple(fields) for pointer, fields in pins.items()
                      if pointer.endswith("/then") and pointer.startswith("/allOf/")]
        for kind, fields in sorted(self.module.CONTRACT_KIND_FIELDS.items()):
            self.assertIn(tuple(fields), then_lists, kind)

    def test_removing_a_required_field_from_any_event_pin_is_caught(self):
        failures = []
        for pointer, fields in sorted(self.module.SCHEMA_REQUIRED["event"].items()):
            if not fields:
                continue
            root = self.copy_root()
            path = os.path.join(root, "references", "event.schema.json")
            document = load(path)
            dropped = at_pointer(document, pointer)["required"].pop(0)
            testlib.write(path, json.dumps(document, indent=2, ensure_ascii=False) + "\n")
            code, report = run_validator(root)
            if code == 0 or report["ok"]:
                failures.append("event.schema.json at %s without %s is still accepted"
                                % (pointer or "the top level", dropped))
        self.assertEqual(failures, [])

    def test_an_untouched_copy_still_passes(self):
        code, report = run_validator(self.copy_root())
        self.assertEqual(code, 0, report["failures"])
        self.assertEqual(report["pins"]["schemas"], 4)


# ==== send-back 2 (control room, 2026-09-21) ==================================================
# Q8's second finding, reproduced by the control room through the real CLI and ruled: the
# component PUBLISHES a lock object, it does not pass the lock file through.

FOREIGN_LOCK = json.dumps({"owner": "some other tool", "pid": "999999"}, sort_keys=True)


class AForeignLockIsPublishedNotPassedThrough(unittest.TestCase):
    """A lock file another tool wrote made a SUCCESS body fail its own published schema.

    The control room's probe: `{"owner": "some other tool", "pid": "999999"}` in the lock file,
    then `import-legacy --break-lock` — exit 0, `ok: true`, and `broke_lock` the foreign object
    verbatim, which the schema refuses. Every response now carries the documented object instead:
    `pid` an integer or null, `pid_start` a string or null, `command` only when it is a non-empty
    string, `unreadable` saying the lock was not one of ours.
    """

    def setUp(self):
        self.scratch = testlib.make_scratch("records-foreign-")
        self.workspace = testlib.fixture_workspace(self.scratch)
        testlib.import_doc(self.workspace, GRANTS)
        self.log = events_mod.log_path(self.workspace, GRANTS)
        self.plain = testlib.make_workspace(os.path.join(self.scratch, "plain"))
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def import_breaking(self, contents):
        testlib.write(events_mod.lock_path(self.log), contents)
        code, body, err = testlib.run_json(["import-legacy", "--workspace", self.workspace,
                                            "--doc", GRANTS, "--break-lock"])
        self.assertEqual(code, 0, (body, err))
        return body

    def append_breaking(self, contents):
        """An `append` that breaks a lock, and the head it needs, through the real CLI."""
        first = testlib.events_file(self.batches, [testlib.opened()], "first.json")
        code, body, err = testlib.run_json(["append", "--workspace", self.plain,
                                            "--doc", testlib.DOC, "--events", first,
                                            "--expect-head", testlib.ZERO])
        self.assertEqual(code, 0, (body, err))
        log = events_mod.log_path(self.plain, testlib.DOC)
        testlib.write(events_mod.lock_path(log), contents)
        second = testlib.events_file(self.batches, [testlib.raised()], "second.json")
        code, body, err = testlib.run_json(["append", "--workspace", self.plain,
                                            "--doc", testlib.DOC, "--events", second,
                                            "--expect-head", body["head"], "--break-lock"])
        self.assertEqual(code, 0, (body, err))
        return body

    def as_a_published_lock(self, broke_lock):
        """Validate one `broke_lock` object against the published schema.

        `append` has no response schema of its own (Q3), so its `broke_lock` is checked by
        putting it in the shipped `import-recovered.json`, which is a real `import_ok` body.
        """
        body = load(os.path.join(IMPORT_REPORT_EXAMPLES, "valid", "import-recovered.json"))
        body["broke_lock"] = broke_lock
        return validate.validate_document("import_report", body, testlib.schemas())

    def test_an_import_breaking_a_foreign_lock_returns_a_body_that_validates(self):
        body = self.import_breaking(FOREIGN_LOCK)
        self.assertTrue(body["ok"])
        self.assertEqual(validate.validate_document("import_report", body, testlib.schemas()), [],
                         "a successful response must not fail its own schema")

    def test_an_append_breaking_a_foreign_lock_returns_a_body_that_validates(self):
        body = self.append_breaking(FOREIGN_LOCK)
        self.assertTrue(body["ok"])
        self.assertEqual(self.as_a_published_lock(body["broke_lock"]), [])

    def test_the_foreign_lock_is_reported_as_foreign(self):
        for body in (self.import_breaking(FOREIGN_LOCK), self.append_breaking(FOREIGN_LOCK)):
            broke = body["broke_lock"]
            self.assertEqual(sorted(broke), ["pid", "pid_start", "unreadable"])
            self.assertIsNone(broke["pid"], "a pid that is not a JSON integer is not a pid")
            self.assertIsNone(broke["pid_start"])
            self.assertEqual(broke["unreadable"], events_mod.FOREIGN_LOCK)
            self.assertNotIn("owner", json.dumps(broke), "a foreign key is dropped, not published")

    def test_a_lock_this_component_wrote_is_published_unchanged(self):
        ours = json.dumps({"pid": 999999, "pid_start": "Wed Apr  1 09:00:00 2026",
                           "command": "import-legacy"}, sort_keys=True)
        body = self.import_breaking(ours)
        self.assertEqual(body["broke_lock"], {"pid": 999999,
                                              "pid_start": "Wed Apr  1 09:00:00 2026",
                                              "command": "import-legacy"})
        self.assertEqual(validate.validate_document("import_report", body, testlib.schemas()), [])

    def test_a_lock_with_no_recorded_start_time_is_published_unchanged(self):
        """`pid_start` is null wherever `ps` is denied; a documented null is not a foreign lock."""
        body = self.import_breaking(json.dumps({"pid": 999999, "pid_start": None,
                                                "command": "append"}, sort_keys=True))
        self.assertEqual(body["broke_lock"], {"pid": 999999, "pid_start": None,
                                              "command": "append"})
        self.assertNotIn("unreadable", body["broke_lock"])

    def test_a_lock_that_could_not_be_read_keeps_its_own_reason(self):
        body = self.import_breaking("[]")
        self.assertEqual(body["broke_lock"]["unreadable"],
                         "the lock file holds a JSON list, not an object")
        self.assertEqual(validate.validate_document("import_report", body, testlib.schemas()), [])

    def test_the_lock_field_of_a_refusal_is_published_too(self):
        """A held foreign lock is refused with the same documented object, exit 7."""
        testlib.write(events_mod.lock_path(self.log), FOREIGN_LOCK)
        code, body, err = testlib.run_json(["import-legacy", "--workspace", self.workspace,
                                            "--doc", GRANTS])
        self.assertEqual(code, 7, (body, err))
        self.assertEqual(sorted(body["lock"]), ["pid", "pid_start", "unreadable"])
        self.assertEqual(body["lock"]["unreadable"], events_mod.FOREIGN_LOCK)

    def test_the_liveness_judgement_still_reads_the_raw_contents(self):
        """`holder_alive` is unchanged: the same locks are broken and refused as before."""
        alive = {"pid": os.getpid(), "pid_start": events_mod.process_start(os.getpid()),
                 "command": "import-legacy", "owner": "some other tool"}
        self.assertTrue(events_mod.holder_alive(alive), "a live foreign holder is still alive")
        self.assertFalse(events_mod.holder_alive({"owner": "some other tool", "pid": "999999"}))
        self.assertFalse(events_mod.holder_alive({"pid": 999999, "pid_start": "old"}))
        self.assertFalse(events_mod.holder_alive([]))
        # and through the CLI: a live foreign holder is refused, never broken
        testlib.write(events_mod.lock_path(self.log), json.dumps(alive, sort_keys=True))
        code, body, err = testlib.run_json(["import-legacy", "--workspace", self.workspace,
                                            "--doc", GRANTS, "--break-lock"])
        self.assertEqual(code, 7, (body, err))
        self.assertTrue(body["holder_alive"])
        self.assertTrue(os.path.isfile(events_mod.lock_path(self.log)), "nothing was removed")

    def test_the_published_lock_drops_every_key_this_component_does_not_write(self):
        published = events_mod.published_lock(
            {"pid": 7, "pid_start": "then", "command": "append", "note": "hand made",
             "owner": None})
        self.assertEqual(sorted(published), ["command", "pid", "pid_start", "unreadable"])
        self.assertEqual(published["unreadable"], events_mod.FOREIGN_LOCK)
        self.assertEqual(published["pid"], 7)

    def test_a_boolean_pid_is_not_a_pid(self):
        published = events_mod.published_lock({"pid": True, "pid_start": "then"})
        self.assertIsNone(published["pid"])
        self.assertEqual(published["unreadable"], events_mod.FOREIGN_LOCK)

    def test_the_interface_documents_the_foreign_lock_sentence(self):
        with open(os.path.join(testlib.REFERENCES, "interface.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(events_mod.FOREIGN_LOCK, text)


if __name__ == "__main__":
    unittest.main()
