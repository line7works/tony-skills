"""The rest of group 3.7 (SEC-1, SEC-5, SEC-6, SEC-7, SEC-11), group 3.8 (FORM-1, FORM-2), GOV-1 and RISK-1, on fakes.

SEC-1's fourth safe source is `TheFourthSafeSource`; SEC-2's own request to a provider's host is `TheFramesOwnRequest`. FORM-3
and the restore halves of SEC-7 are in `test_restore.py`.
"""
import ast
import base64
import hashlib
import hmac
import json
import os
import unittest
import urllib.parse

import harness
import rowlib
import scan
from sun_core import forms, fsio, journal as journalmod, texts
from test_log_op import at, planted


class Case(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.count = 0

    def fresh(self, rows, **lane):
        self.count += 1
        m = harness.Machine(self.tmp, "s%d" % self.count, "s%d" % self.count)
        rowlib.install(m, rowlib.lane("sunrise", rows, **lane))
        m.put("shortcuts.txt", "alias other\n")
        m.put("dev/demo-scope.md", "scope\n")
        return m


class TheScan(Case):
    def test_SEC11_the_scan_is_itself_proven_in_every_scanned_place_and_every_form(self):
        canary = harness.canary("scan")
        component = "pw" + harness.canary("part")
        whole = "postgres://u:%s@h/d" % component
        forms_ = {"whole": canary, "percent-encoded": urllib.parse.quote(whole, safe=""), "base64": base64.b64encode(canary.encode()).decode(),
                  "a component": "x" + component + "y"}
        for label, text in forms_.items():
            places = {
                "a file under the fixture home": lambda m: m.put("dev/notes.txt", text),
                "a file name": lambda m: m.put("dev/%s.txt" % text.replace("/", "_"), "x") if "/" not in text else m.put("dev/notes.txt", text),
                "a fake's recorded arguments": lambda m: self.record(m, "calls.jsonl", {"argv": ["noop", text], "env_values": {}}),
                "a fake's recorded environment": lambda m: self.record(m, "calls.jsonl", {"argv": ["noop"], "env_values": {"X": text}}),
                "the recorded arguments of a fake's own child": lambda m: self.record(m, "children.jsonl", {"argv": ["sleep-child", text]}),
                "a form": lambda m: self.in_form(m, text),
            }
            for place, plant in places.items():
                with self.subTest(form=label, place=place):
                    m = self.fresh([rowlib.check()])
                    plant(m)
                    self.assertTrue(scan.scan(m, [(canary, []), (whole, [component])]), "the scan did not find the value")
        m = self.fresh([rowlib.check()])
        out = harness.Result(0, "the output holds " + canary, "", [])
        err = harness.Result(0, "", canary, [])
        self.assertEqual(len(scan.scan(m, [(canary, [])], [out, err])), 2)
        self.assertEqual(scan.scan(m, [(canary, [])], [harness.Result(0, "clean", "clean", [])]), [])

    def test_SEC11_S1_the_scan_finds_a_value_under_Library_in_a_packed_git_object_and_a_fake_issued_value_in_a_form(self):
        """SEC-11: "The scan covers every file under the fixture home and the fixture working tree, ... and every git object";
        its test line: "a canary planted in each scanned place, in each form, is found ...; an issued value planted in a form
        is found." The reviewer's S1: "Scan every promised file and git object representation, prove those negative controls
        fail"."""
        import subprocess
        canary = harness.canary("scan-s1")
        for label, text in (("whole", canary), ("base64", base64.b64encode(canary.encode()).decode()),
                            ("percent-encoded", urllib.parse.quote("a/" + canary, safe=""))):
            with self.subTest(form=label, place="a file under Library"):
                m = self.fresh([rowlib.check()])
                m.put(os.path.join("Library", "Caches", "fixture", "note.txt"), "x %s y\n" % text)
                self.assertTrue(scan.scan(m, [(canary, []), ("a/" + canary, [])]), "the scan did not look under Library")
            for packed in (False, True):
                with self.subTest(form=label, place="a packed git object" if packed else "a loose git object"):
                    m = self.fresh([rowlib.check()])
                    repo = m.path("dev", "demo")
                    os.makedirs(repo)
                    env = {"HOME": m.home, "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}

                    def git(*args):
                        subprocess.run(["/usr/bin/git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid"] + list(args),
                                       cwd=repo, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    git("init", "-q", "-b", "main")
                    with open(os.path.join(repo, "f.txt"), "w") as fh:
                        fh.write("x %s y\n" % text)
                    git("add", "f.txt")
                    git("commit", "-q", "-m", "one")
                    os.remove(os.path.join(repo, "f.txt"))
                    if packed:
                        git("repack", "-a", "-d", "-q")
                        git("prune-packed")
                        loose = [d for d in os.listdir(os.path.join(repo, ".git", "objects")) if len(d) == 2]
                        self.assertEqual(loose, [], "a loose object is left: the control would not be a packed one")
                    self.assertTrue(scan.scan(m, [(canary, []), ("a/" + canary, [])]), "the scan did not find the value in the git object")
        m = self.fresh([rowlib.create("C1")])
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        values = [(v, []) for v in scan.issued(m)]
        self.assertTrue(values, "the fake issued nothing")
        self.assertEqual(scan.scan(m, values, [looked, went]), [])
        with open(went.doc["forms"][0], "a") as fh:
            fh.write(values[0][0] + "\n")
        self.assertTrue(scan.scan(m, values), "an issued value planted in a form was not found")

    # SEC-11: "It looks for the canary and for each issued value whole, for each of its components, and for the percent-encoded
    # and base64 forms of both." Its test line: "a canary planted in each scanned place, in each form, is found". The forms, a
    # list of this test's own, written out by hand, each named by its encoding (the reviewer's S2; the owner's ruling, A140):
    # not built from the tool's `screen.forms_of` nor from the scan's `scan.needles`.
    UNRESERVED = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"

    @classmethod
    def percent(cls, text, plus=False, lower=False):
        """Percent-encoding by hand, of the UTF-8 bytes: an unreserved character as it is, a space as `+` in the form
        encoding, every other byte as `%` and two hexadecimal digits, in capitals or in lower case."""
        out = []
        for byte in text.encode("utf-8"):
            ch = chr(byte)
            if ch in cls.UNRESERVED:
                out.append(ch)
            elif plus and ch == " ":
                out.append("+")
            else:
                out.append(("%%%02x" if lower else "%%%02X") % byte)
        return "".join(out)

    @classmethod
    def forms_by_hand(cls, text):
        raw = text.encode("utf-8")
        standard = base64.b64encode(raw).decode("ascii")
        link_safe = standard.replace("+", "-").replace("/", "_")      # the link-safe alphabet, by hand from the standard one
        return [("whole", text),
                ("percent-encoding, capital escapes", cls.percent(text)),
                ("percent-encoding, lower-case escapes", cls.percent(text, lower=True)),
                ("form encoding with its plus, capital escapes", cls.percent(text, plus=True)),
                ("form encoding with its plus, lower-case escapes", cls.percent(text, plus=True, lower=True)),
                ("base64, standard alphabet, with its padding", standard),
                ("base64, standard alphabet, without its padding", standard.rstrip("=")),
                ("base64, link-safe alphabet, with its padding", link_safe),
                ("base64, link-safe alphabet, without its padding", link_safe.rstrip("="))]

    @staticmethod
    def telling(base):
        """`base` made into a value whose nine forms all differ: a space and characters whose escapes hold letters, bytes
        whose base64 holds `+` and `/` in the standard alphabet (`???` and `>>>` at a multiple of three bytes), and a length
        that gives base64 its padding."""
        base += "-" * (-len(base.encode("utf-8")) % 3)
        return base + "???>>> :/x"

    def test_SEC11_S2_the_scan_finds_a_value_and_a_component_in_each_form_and_forms_of_produces_each_form(self):
        from sun_core import facts as factsmod, runner, screen
        component = self.telling(harness.canary("s2-part"))
        value = self.telling("postgres://u:%s@h/d" % component)
        for label, text in (("a value", value), ("one of its components", component)):
            forms = self.forms_by_hand(text)
            # nine forms all different: so the value has its padding, a `+` or a `/` in the standard alphabet, a letter in an
            # escape and a space, and no form on the list stands for another
            self.assertEqual(len(set(f for _n, f in forms)), 9, "two of the nine forms are alike: the test proves less than it says")
            # (b) the tool's screen produces every form on the list, for the value and for one of its components (an entry of
            # the register holds the forms of its value and of each component, `screen.Entry`)
            produced = screen.forms_of(text)
            entry = screen.Entry(value, [component])
            for name, form in forms:
                with self.subTest(of=label, form=name, part="(b) forms_of"):
                    self.assertIn(form, produced, "forms_of does not produce it")
                    self.assertIn(form, entry.forms, "the register's entry does not hold it")
            # (a) the scan finds a planted value in each form on the list, each form its own positive control: planted alone,
            # in a scanned file, and in a fake's recorded arguments, the fake started through the runner with that form as an
            # argument. A place with nothing planted is no finding.
            values = [(value, [component])] if label == "one of its components" else [(value, [])]
            m = self.fresh([rowlib.check()])
            self.assertEqual(scan.scan(m, values), [], "a finding with nothing planted: no form is its own control")
            for name, form in forms:
                with self.subTest(of=label, form=name, part="(a) the scan, in a scanned file"):
                    m = self.fresh([rowlib.check()])
                    m.put("dev/notes.txt", "before %s after\n" % form)
                    self.assertTrue(scan.scan(m, values), "the scan did not find it in a scanned file")
                with self.subTest(of=label, form=name, part="(a) the scan, in a fake's recorded arguments"):
                    m = self.fresh([rowlib.check()])
                    world = m.world()
                    context = runner.Context(screen.Screen(), None, factsmod.Facts(world.env).search_list(world.fs))
                    raw = runner.run(world, context, {"tool": "fakehost", "time_limit": 20}, ["noop", "--name", form], {}, m.home)
                    self.assertEqual(raw.exit_code, 0)
                    self.assertEqual(m.calls("fakehost")[-1]["argv"], ["noop", "--name", form], "the fake did not record the form")
                    found = scan.scan(m, values)
                    self.assertTrue(found, "the scan did not find it in a fake's recorded arguments")
                    self.assertTrue(all(where.startswith(os.path.join(".fakes", "fakehost")) for where, _w in found), found)

    def record(self, m, name, doc):
        folder = os.path.join(m.home, ".fakes", "fakehost")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, name), "a") as fh:
            fh.write(json.dumps(doc) + "\n")

    def in_form(self, m, text):
        looked = m.look()
        with open(looked.doc["forms"][0], "a") as fh:
            fh.write(text + "\n")

    def test_SEC11_a_value_at_a_place_of_SEC7_is_no_finding_and_with_wider_permissions_it_is_reported(self):
        m = self.fresh([rowlib.create("C1")])
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        values = [(v, []) for v in scan.issued(m)]
        self.assertTrue(values, "the fake issued nothing for the scan")
        self.assertEqual(scan.scan(m, values, [looked, went]), [], "an issued value is outside the places of SEC-7")
        folder = os.path.join(m.facts.run_dir(looked.doc["run"]), "protected")
        record = [n for n in os.listdir(folder) if n != "key"][0]
        self.assertEqual(open(os.path.join(folder, record)).read(), values[0][0], "the held id is not in its protected record")
        os.chmod(os.path.join(folder, record), 0o644)
        self.assertEqual([what for _where, what in scan.scan(m, values)], ["at a place of SEC-7 with wider permissions"])

    def test_SEC11_SEC7_a_value_in_a_file_of_another_name_under_the_run_directorys_private_folder_is_a_finding(self):
        """SEC-11: "One found outside a place of SEC-7, or at one with wider permissions than SEC-7 gives, fails." SEC-7's
        places in the run directory are "the private password file | the database's connection address, every part of it |
        a new file built by the frame (SEC-2); owner-only; removed after use", "the protected folder of the run directory"
        and "staging". The build keeps the private password file at `private/password-<operation>` (`rundir`); nothing
        else under `private/` is a place of SEC-7. A held value planted, owner-only, in a file of another name under that
        folder, and in a file of the password file's name one folder further down, is a finding; the same value in the
        private password file's own place, owner-only, is none, and with wider permissions it is reported as such."""
        m = self.fresh([rowlib.create("C1")])
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        values = [(v, []) for v in scan.issued(m)]
        self.assertTrue(values, "the fake issued nothing for the scan")
        self.assertEqual(scan.scan(m, values, [looked, went]), [], "an issued value is outside the places of SEC-7")
        private = os.path.join(m.facts.run_dir(looked.doc["run"]), "private")

        def plant(*rel):
            path = os.path.join(private, *rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write(values[0][0] + "\n")
            os.chmod(path, 0o600)
            return path
        for label, rel in (("a file of another name", ("notes.txt",)),
                           ("a file of the password file's name, one folder further down", ("kept", "password-C1"))):
            with self.subTest(planted=label):
                path = plant(*rel)
                found = scan.scan(m, values)
                self.assertTrue(found, "a value under the private folder outside the private password file is no finding")
                self.assertTrue(all(where.startswith(os.path.relpath(path, m.home)) for where, _what in found), found)
                os.remove(path)
        password = plant("password-C1")
        self.assertEqual(scan.scan(m, values), [], "the value in the private password file's own place is a finding")
        os.chmod(password, 0o644)
        self.assertEqual([what for _where, what in scan.scan(m, values)], ["at a place of SEC-7 with wider permissions"])


class PlantedAtRunTime(unittest.TestCase):
    def test_SEC11_no_file_of_the_plugin_holds_an_address_with_a_password_or_a_key_shaped_string_as_a_literal(self):
        """SEC-11: "A marked canary, built at run time"; the contract's section 3: "a planted test secret is a
        marked canary built at run time, never a literal in a committed file that a scanner would read as a key"."""
        import re
        address = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^/\s\"'@:%]+:[^@\s\"'%{}()+]+@")
        shaped = re.compile(r"gh[pousr]_[A-Za-z0-9]{10,}|github_pat_\w{10,}|sk-[A-Za-z0-9]{10,}|sk_(?:live|test)_\w{6,}"
                            r"|AKIA[0-9A-Z]{12,}|xox[abpr]-[A-Za-z0-9-]{6,}|-----BEGIN [A-Z ]*KEY|AIza[0-9A-Za-z_-]{20,}")
        found = []
        for base, dirs, files in os.walk(harness.PLUGIN):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(files):
                full = os.path.join(base, name)
                with open(full, "rb") as fh:
                    text = fh.read().decode("utf-8", "replace")
                for number, line in enumerate(text.split("\n"), 1):
                    if address.search(line) or shaped.search(line):
                        found.append("%s:%d" % (os.path.relpath(full, harness.PLUGIN), number))
        self.assertEqual(found, [], "a planted secret written as a literal")


class EveryPlace(Case):
    def test_SEC1_SEC7_FORM1_a_canary_in_every_source_reaches_no_record_manifest_form_output_or_error(self):
        token = harness.canary("token")
        password = "pw" + harness.canary("password")
        address = "postgres://appuser:%s@db.fixture.invalid:5432/appdb" % password
        env_secret = harness.canary("envvalue")
        protected_line = "alias " + harness.canary("ownerfile")
        pull = rowlib.build("E1", "remote", place=rowlib.path(rowlib.DEV, "demo.pulled.env"), output="env file")
        pull["construction"] = {"id": "C1", "builder": "pull", "out_param": "out", "single_file": True, "mode": 0o600}
        pull["commands"] = [rowlib.use("pull", "fakehost.write")]
        place = pull["thing"]["place"]
        pull["after_test"] = [{"read": "path", "path": place, "is": "file"}]
        pull["after_check"] = [{"read": "path", "path": place, "is": "file"}, {"read": "mode", "path": place, "at_most": 0o600}]
        rows = rowlib.clean_rows() + [pull, rowlib.keep("P1", "remote"), rowlib.secret_op("X1", "remote")]
        m = self.fresh(rows, phases=("prepare", "remote"))
        m.put("shortcuts.txt", protected_line + "\n")                      # the present text of a file: protected
        m.put("dev/demo.env", "DATABASE_URL=%s\n" % address, 0o600)        # a value of an env file: secret
        m.set_fake("fakehost", secret=env_secret, things={})
        dump_data = harness.canary("dumpdata")                               # the data in a dump: secret
        m.set_fake("fakedump", secret=dump_data)
        m.env["FAKEHOST_TOKEN"] = token                                     # a provider's token, in its channel
        m.env["FAKEHOST_DEBUG"] = "1"                                       # a debug variable in the session
        m.secret_places = (os.path.join(m.dev, "demo.env"), os.path.join(m.dev, "demo.pulled.env"), os.path.join(m.dev, "demo-dump.txt"))
        m.owner_files = (m.path("shortcuts.txt"),)
        looked, went = m.started()
        run = looked.doc["run"]
        self.assertEqual(went.ending, "complete", went.text)
        status = m.summon("status", "demo", "--run", run)
        values = [(token, []), (address, [password, "appuser:" + password]), (env_secret, []), (protected_line, []), (dump_data, [])]
        values += [(v, []) for v in scan.issued(m)]
        self.assertGreaterEqual(len(scan.issued(m)), 2, "the fakes issued too little for the scan")
        findings = scan.scan(m, values, [looked, went, status])
        self.assertEqual(findings, [])
        # the work was done: each secret rests where SEC-7 lets it, owner-only
        self.assertEqual(os.stat(os.path.join(m.dev, "demo.pulled.env")).st_mode & 0o777, 0o600)
        self.assertIn(env_secret, open(os.path.join(m.dev, "demo.pulled.env")).read())
        self.assertEqual(os.stat(os.path.join(m.dev, "demo-dump.txt")).st_mode & 0o777, 0o600)
        self.assertIn(dump_data, open(os.path.join(m.dev, "demo-dump.txt")).read())
        self.assertEqual(os.stat(m.facts.keying_file).st_mode & 0o777, 0o600)
        # and the same run's forms hold the safe fields FORM-2 requires, so an implementation that shows nothing fails
        form = open(went.doc["forms"][0]).read()
        for line in ("[B1] done: the fake row B1", "[K1] the check passed: the fake row K1", "names: demo", "in your words: a fixture project"):
            self.assertIn(line, form)
        self.assertIn("the shortcut file before the line was added: " + os.path.join(m.facts.run_dir(run), "protected"), form)
        for call in [c for tool in ("fakehost", "fakegit", "fakedump") for c in m.calls(tool)]:
            self.assertNotIn("FAKEHOST_DEBUG", call["env_names"])
            self.assertNotIn("FAKEHOST_TOKEN", call["env_names"])

    def test_SEC5_nothing_a_tool_prints_is_kept_or_shown_and_the_stops_form_gives_the_operation_the_kind_and_the_command(self):
        canary = harness.canary("echo")
        m = self.fresh(rowlib.clean_rows(), phases=("prepare", "remote"))
        m.plan_fake("fakegit", {"command": "cas", "do": "echo", "value": canary, "exit": 9})
        looked, went = m.started()
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(scan.scan(m, [(canary, [canary[: len(canary) // 2]])], [looked, went]), [])
        form = open(went.doc["forms"][0]).read()
        self.assertIn("stopped: a command failed; operation G1; the command you can run: fakegit cas --ref main --new c1 --old none", form)
        reason = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "invocation-end"][-1]["reason"]
        self.assertEqual(reason["result"], "malformed")

    def test_SEC6_a_protected_record_is_named_never_shown_and_its_fingerprint_is_keyed(self):
        content = b"alias other\n"
        prints = []
        for index in range(2):
            m = self.fresh(rowlib.clean_rows(), phases=("prepare", "remote"))
            looked, went = m.started()
            run_dir = m.facts.run_dir(looked.doc["run"])
            start = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "start" and r["op"] == "S1"][0]
            reference = start["inputs"][0]
            self.assertEqual(sorted(reference), ["fingerprint", "label", "record", "type"])
            self.assertEqual(open(os.path.join(run_dir, "protected", reference["record"]), "rb").read(), content)
            self.assertNotEqual(reference["fingerprint"], hashlib.sha256(content).hexdigest(), "the fingerprint is the plain hash of the content")
            key = open(os.path.join(run_dir, "protected", "key")).read().strip()
            self.assertEqual(reference["fingerprint"], hmac.new(key.encode(), content, hashlib.sha256).hexdigest(), "D16: not the keyed algorithm")
            self.assertNotIn(reference["record"], hashlib.sha256(content).hexdigest())
            self.assertEqual(os.stat(os.path.join(run_dir, "protected", reference["record"])).st_mode & 0o777, 0o600)
            prints.append(reference["fingerprint"])
        self.assertNotEqual(prints[0], prints[1], "two runs give one fingerprint for the same content")

    def test_SEC6_a_thing_found_at_a_provider_under_a_name_he_did_not_type_is_counted_and_named_by_a_file(self):
        other = "databasename" + harness.canary("dbname")[-6:]
        row = rowlib.refusing("H1")
        row["thing"]["found_things"] = {"command": "look", "field": "name", "kind": "database", "provider": "fakehost"}
        m = self.fresh([row])
        m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}})
        m.plan_fake("fakehost", {"command": "get", "name_as": other})
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        preview = open(looked.doc["forms"][0]).read()
        self.assertIn("1 database found at fakehost; their names are in a private file: ", preview)
        self.assertNotIn(other, preview)
        self.assertNowhere(other, looked)
        path = preview.split("private file: ")[1].split("\n")[0]
        self.assertEqual(open(path).read().strip(), other)

    def test_SEC7_a_link_planted_at_a_place_fails_the_operation_with_nothing_written_through_it(self):
        m = self.fresh([rowlib.build("B1")])
        looked = m.look()
        elsewhere = os.path.join(m.home, "elsewhere")
        os.makedirs(elsewhere)
        os.rename(m.dev, m.dev + "-real")
        os.symlink(m.dev + "-real", m.dev)
        went = m.go(looked)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(os.listdir(m.dev + "-real"), ["demo-scope.md"], "something was written through a link")
        s = self.fresh([rowlib.swap_add("S1")])
        os.rename(s.path("shortcuts.txt"), s.path("real-shortcuts.txt"))
        looked = s.look()
        self.assertEqual(looked.ending, "refused", "a file that is not there was planned")
        s2 = self.fresh([rowlib.swap_add("S1")])
        looked = s2.look()
        os.rename(s2.path("shortcuts.txt"), s2.path("real-shortcuts.txt"))
        os.symlink(s2.path("real-shortcuts.txt"), s2.path("shortcuts.txt"))
        went = s2.go(looked)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(open(s2.path("real-shortcuts.txt")).read(), "alias other\n")


class Forms(Case):
    def test_FORM1_no_form_is_built_by_reading_a_files_text(self):
        source = open(os.path.join(harness.SCRIPTS, "sun_core", "forms.py")).read()
        tree = ast.parse(source)
        reads = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                if name in ("open", "read", "read_text", "read_json", "readlines"):
                    reads.append(name)
        self.assertEqual(reads, [], "a form template reads a file's text directly")
        self.assertIn("format(", source)

    def test_FORM2_every_line_of_the_table_holds_the_parts_its_row_names_and_a_template_without_one_fails(self):
        parts = {"done": dict(what="W"), "already so": dict(what="W"), "not proven": dict(what="W"),
                 "adopted": dict(what="W", identity="ID"), "waiting": dict(step="STEP", mode="MODE", how="HOW"),
                 "done by owner, read back": dict(what="W"), "done by owner, on his word": dict(what="W"), "left": dict(what="W"),
                 "held": dict(what="W", need="NEED", provider="PROV", status="STATUS"), "refused": dict(what="W", result="RESULT"),
                 "not needed": dict(what="W"), "not applicable": dict(reason="REASON", what="W", step="; STEPHE"),
                 "unavailable": dict(what="W"), "outstanding": dict(what="W", check="CHECK", ways="WAYS"),
                 "stop": dict(reason="KIND", what="", operation="; OP", command="; CMD", need="; NEED", ways="WAYS"),
                 "protected record": dict(label="LABEL", path="PATH")}
        self.assertEqual(sorted(parts), sorted(forms.LINES))
        for status, given in parts.items():
            line = forms.line_for(status, {}, **given)
            for value in given.values():
                self.assertIn(value, line, "%s: its line lacks a part" % status)
            for missing in given:
                short = dict(given)
                del short[missing]
                with self.assertRaises(forms.NoLine, msg="%s rendered without %s" % (status, missing)):
                    forms.line_for(status, {}, **short)
        self.assertIn("a read checked it", forms.LINES["done by owner, read back"])
        self.assertIn("no read checked it", forms.LINES["done by owner, on his word"])
        with self.assertRaises(forms.NoLine):
            forms.line_for("passed", {}, what="W")
        self.assertEqual(forms.line_for("passed", {"passed": "the check passed: {what}"}, what="W"), "the check passed: W")
        self.assertEqual(forms.line_for("done", {"done": "a lane may not replace this: {what}"}, what="W"), "done: W")

    def test_FORM2_a_status_with_a_line_neither_in_the_table_nor_in_the_lanes_list_fails_the_forms_build(self):
        m = self.fresh([rowlib.check("K1")], form_changes={})
        looked, went = m.started()
        self.assertEqual(went.lines, [texts.NO_FORM_LINE + "passed"])
        self.assertIsNone(went.doc.get("forms"))
        self.assertEqual([n for n in os.listdir(os.path.join(m.facts.run_dir(looked.doc["run"]), "forms")) if n.startswith("status")], [])
        given = self.fresh([rowlib.check("K1")])
        looked, went = given.started()
        self.assertIn("[K1] the check passed: the fake row K1", open(went.doc["forms"][0]).read())

    def test_FORM2_a_run_through_its_statuses_renders_each_matching_line(self):
        rows = [rowlib.build("B1"), rowlib.owner_step("O1", mode="on his word"), rowlib.owner_answer("A1"),
                rowlib.check("N1", needs=[{"output": "answer-A1", "level": "answered", "value": "use it", "treatment": "then not applicable"}]),
                rowlib.refusing("H1")]
        m = self.fresh(rows)
        m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}})
        looked = m.look()
        things = m.fake("fakehost", "state.json")["things"]
        things["demo"]["state"] = "paused"
        m.set_fake("fakehost", things=things)
        went = m.go(looked)
        form = open(went.doc["forms"][0]).read()
        self.assertIn("[B1] done: the fake row B1", form)
        self.assertIn("[H1] found already so; a restore will not reverse it: the fake row H1", form)
        self.assertIn("[O1] waiting on you: connect the fake host by hand; mode: on his word; the tool will know it is done by your word alone", form)
        self.assertIn("[A1] waiting on you: use the merged file?; mode: answer; the tool will know it is done by your answer", form)
        m.resume("demo", None, "--done", "O1")
        last = m.resume("demo", None, "--answer", "A1=keep the old file")
        form = open(last.doc["forms"][0]).read()
        self.assertIn("[O1] done by you, on your word; no read checked it: the fake row O1", form)
        self.assertIn("[A1] you answered: the fake row A1", form)
        self.assertIn("[N1] not run: the fake row N1; it needed answer-A1 at the answered level, and A1 ended answered", form)
        self.assertEqual(last.ending, "ended with exceptions")


class Governing(Case):
    def test_GOV1_a_result_kind_no_rule_names_and_a_journal_status_no_rule_names_each_stop_with_no_effect_after(self):
        m = self.fresh(rowlib.clean_rows(), phases=("prepare", "remote"))
        m.plan_fake("fakehost", {"command": "set", "do": "fail", "exit": 42, "stdout": {"kind": "a kind nobody declared"}})
        looked, went = m.started()
        run = looked.doc["run"]
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("operation: H1", went.lines)
        self.assertNotIn("H1", m.statuses(run))
        calls = len([c for c in m.calls("fakehost") if c["changing"]])
        j = self.fresh([rowlib.owner_step("O1", mode="on his word"), rowlib.build("B1", needs=[
            {"output": "connected", "level": "state", "accepts": ["his word"], "treatment": "then not applicable"}])])
        looked, went = j.started()
        run = looked.doc["run"]
        records = j.journal(run)
        body = {"n": len(records), "kind": "status", "at": "2026-01-01T00:00:00Z", "prev": records[-1]["h"], "inv": records[-1]["inv"],
                "op": "O1", "status": "probably fine"}
        body["h"] = journalmod._hash(body["prev"], body)
        with open(os.path.join(j.facts.run_dir(run), "journal.jsonl"), "a") as fh:
            fh.write(fsio.canonical_json(body) + "\n")
        stopped = j.summon("resume", "demo", "--position", len(records) + 1, "--word", "go on")
        self.assertEqual(stopped.ending, "stopped", stopped.text)
        self.assertIn("stopped: the journal holds a record no rule names", stopped.lines)
        self.assertIn("operation: O1", stopped.lines)
        self.assertFalse(os.path.exists(os.path.join(j.dev, "demo")), "an effect was applied after the stop")

    def test_RISK1_each_mark_is_recorded_once_for_its_operation_and_its_risk_and_no_other_record_carries_one(self):
        m = self.fresh(rowlib.clean_rows() + [rowlib.secret_op("X1", "remote")], phases=("prepare", "remote"))
        looked = m.look()
        m.go(looked, kill=at("post", "journal", "start", "M1"))
        m.resume()
        marks = sorted((r["op"], r["risk"]) for r in m.journal(looked.doc["run"]) if r.get("step") == "risk-mark")
        self.assertEqual(marks, [("M1", "RK4"), ("S1", "RK13"), ("S1", "RK2"), ("S1", "RK5")])   # a shortcut's add: RK5 and RK13 beside RK2 (A63)
        for record in m.journal(looked.doc["run"]):
            if record.get("step") != "risk-mark":
                self.assertNotIn("risk", record)
            self.assertNotIn(record.get("risk"), ("RK1", "RK6", "RK7", "RK8"))


class TheFourthSafeSource(Case):
    """SEC-1's table, the safe class: "content of a file on this machine that the owner or the tool wrote, where a validator
    the row declares has passed"; the protected class: "Content the run read from the owner's files and has not validated".
    ROW-1: every row states "the class of every content it reads, stores or shows; any validator that makes content of a
    file on this machine safe (SEC-1), none being able to make a provider's value safe". SEC-1's test line: "a canary
    planted in each secret source and each protected source ... appear[s] ... in no journal record, manifest, form, output
    or error; and the same run's forms hold the safe fields FORM-2 requires". Here the source is a line of the project's
    scope file that an owner step's text is built from (OP-9: "The step shown to him is built from safe content (SEC-1)")."""

    VALIDATOR = "one line of plain words"

    def row(self, declared=True):
        step = {"text": [rowlib.lit("read the project's scope: "),
                         {"local": {"path": rowlib.path(rowlib.DEV, "demo-scope.md"), "validator": self.VALIDATOR}}]}
        row = rowlib.owner_step("O1", mode="on his word", safe_content={"step": step})
        row["content_classes"]["reads"] = ["safe", "protected"]
        row["content_classes"]["validators"] = [self.VALIDATOR] if declared else []
        return row

    def test_SEC1_ROW1_a_line_of_a_file_on_this_machine_that_the_rows_validator_passes_is_safe_and_one_it_fails_is_protected(self):
        for case in ("the validator passes", "the validator fails", "the row declares no validator"):
            with self.subTest(content=case):
                m = self.fresh([self.row(declared=case != "the row declares no validator")])
                planted = harness.canary("scope-" + case[:12].replace(" ", "-"))
                if case == "the validator fails":
                    m.put("dev/demo-scope.md", "Tide table: %s\nand a second line\n" % planted)
                else:
                    m.put("dev/demo-scope.md", "Tide table %s\n" % planted)
                looked = m.look()
                if case == "the row declares no validator":
                    self.assertEqual(looked.ending, "refused", looked.text)
                    self.assertIn("row O1, entry content_classes: a validator the row does not declare", looked.lines)
                    continue
                self.assertEqual(looked.ending, "preview", looked.text)
                run = looked.doc["run"]
                manifest_text = open(os.path.join(m.facts.run_dir(run), "manifest-1.json")).read()
                step = [o for o in json.loads(manifest_text)["operations"] if o["id"] == "O1"][0]["safe_content"]["step"]
                went = m.go(looked)
                self.assertEqual(went.ending, "waiting", went.text)
                form = open(went.doc["forms"][0]).read()
                if case == "the validator passes":
                    # safe by where it came from: the manifest holds it as a literal, and the form shows the step built from it
                    self.assertEqual(step, {"literal": "read the project's scope: Tide table %s" % planted})
                    self.assertIn("[O1] waiting on you: read the project's scope: Tide table %s;" % planted, form)
                    continue
                # protected: in a protected record the manifest refers to, and in no manifest, journal record, form or output
                self.assertIn("record", json.dumps(step), step)
                self.assertNotIn(planted, manifest_text)
                for record in m.journal(run):
                    self.assertNotIn(planted, json.dumps(record))
                self.assertNowhere(planted, looked)
                self.assertNowhere(planted, went)
                self.assertNotIn(planted, form + open(looked.doc["forms"][0]).read())
                self.assertIn("[O1] waiting on you: read the project's scope: ", form, "the form does not hold the waiting line FORM-2 requires")
                self.assertIn(os.path.join(m.facts.run_dir(run), "protected") + os.sep, form, "the form does not name the record")



class RUN7TwoFailedReads(Case):
    """RUN-7's test line (batch 36, A86): "and a failed read in two more forms: a file on this machine that a row's local mark
    names, made unreadable to the fixture's owner, of which nothing is safe by SEC-1 since no validator could pass on content
    that was not read, and a request of the frame's own (SEC-2) answered by a redirect, which is not followed and keeps
    nothing (SEC-4); each ends the look as that planning stop with the read named, and each met at an operation's probe
    instead gives `unreadable` (OP-5) with no effect call". OP-5's table: "either | the read failed, was partial, was made as
    the wrong account, or ran out of time | `unreadable`"; OP-6: "`foreign`, `unreadable` | stop"."""

    VALIDATOR = TheFourthSafeSource.VALIDATOR

    def local_row(self):
        """A change of the scope file whose added line is built from a line of that file through the row's local mark: the
        look reads the file for the mark, and the probe reads it for the row's tests."""
        scope = rowlib.path(rowlib.DEV, "demo-scope.md")
        line = {"text": [rowlib.lit("# also: "), {"local": {"path": scope, "validator": self.VALIDATOR}}]}
        row = rowlib.swap_add("S1", file=scope, line=line)
        row["before_test"] = [c for c in row["before_test"] if c.get("read") != "name-free"]
        row["construction"]["risks"] = ["RK2"]
        row["span"] = {"placement": "at the end", "ordered": False}
        row["content_classes"]["reads"] = ["safe", "protected"]
        row["content_classes"]["validators"] = [self.VALIDATOR]
        reverse = row["way_back"]["reverse"]
        reverse["content_classes"]["reads"] = ["safe", "protected"]
        reverse["content_classes"]["validators"] = [self.VALIDATOR]
        return row

    def redirect_row(self):
        row = rowlib.refusing("H1")
        row["commands"] = [rowlib.use("look", "fakehost.api-maybe"), row["commands"][1]]
        return row

    def redirect_machine(self, rows):
        self.count += 1
        m = harness.Machine(self.tmp, "r%d" % self.count, "r%d" % self.count)
        decls = request_providers()
        decls["fakehost"]["commands"]["api-maybe"] = dict(decls["fakehost"]["commands"]["api-moved"],
                                                          template=[{"literal": "v1"}, {"literal": "maybe"}])
        rowlib.install(m, rowlib.lane("sunrise", rows), providers=decls)
        m.put("shortcuts.txt", "alias other\n")
        token = harness.canary("redirect-token")
        m.env["FAKEHOST_TOKEN"] = token
        m.transport = MaybeMoved(m, token)
        return m

    def assertLookStopped(self, m, looked, line):
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn(line, looked.lines, "the planning stop does not name the read")
        run_dir = m.facts.run_dir(looked.doc["run"]) if looked.doc.get("run") else None
        if run_dir and os.path.isdir(run_dir):
            self.assertFalse([n for n in os.listdir(run_dir) if n.startswith("manifest")], "a manifest was written")
            self.assertFalse(os.path.exists(os.path.join(run_dir, "journal.jsonl")), "a journal was written")

    def assertProbeUnreadable(self, m, went, op, effects):
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: unreadable", went.lines)
        self.assertIn("operation: %s" % op, went.lines)
        self.assertFalse([r for r in m.journal(went.doc["run"]) if r.get("op") == op and r["kind"] in ("start", "completion")],
                         "the probe of %s recorded a start or a completion" % op)
        self.assertEqual(effects(), [], "an effect call was made")

    def test_RUN7_OP5_a_file_a_rows_local_mark_names_made_unreadable_ends_the_look_and_gives_unreadable_at_the_probe(self):
        planted = harness.canary("local-unreadable")
        m = self.fresh([self.local_row()])
        scope = m.put("dev/demo-scope.md", "Tide table %s\n" % planted)
        os.chmod(scope, 0)
        try:
            looked = m.look()
        finally:
            os.chmod(scope, 0o644)
        self.assertLookStopped(m, looked, "the read failed: a file on this machine of row S1")
        self.assertNowhere(planted, looked)
        # met at the probe: the look read it, then it is made unreadable before the go
        m = self.fresh([self.local_row()])
        scope = m.put("dev/demo-scope.md", "Tide table %s\n" % planted)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        before = open(scope, "rb").read()
        os.chmod(scope, 0)
        try:
            went = m.go(looked)
        finally:
            os.chmod(scope, 0o644)
        self.assertProbeUnreadable(m, went, "S1", lambda: [] if open(scope, "rb").read() == before else ["the file changed"])
        self.assertNowhere(planted, went)

    def test_RUN7_OP5_SEC2_a_request_of_the_frames_own_answered_by_a_redirect_ends_the_look_and_gives_unreadable_at_the_probe(self):
        m = self.redirect_machine([self.redirect_row()])
        m.transport.moved = True
        looked = m.look()
        self.assertLookStopped(m, looked, "the read failed: the thing of row H1")
        self.assertEqual([r["path"] for r in m.transport.records], ["/v1/maybe"], "a redirect was followed")
        self.assertEqual(m.calls("fakehost", "set"), [], "an effect call was made")
        # met at the probe: the look's request answered, the probe's redirected
        m = self.redirect_machine([self.redirect_row()])
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        m.transport.moved = True
        seen = len(m.transport.records)
        went = m.go(looked)
        self.assertProbeUnreadable(m, went, "H1", lambda: m.calls("fakehost", "set"))
        self.assertEqual([r["path"] for r in m.transport.records[seen:]], ["/v1/maybe"], "a redirect was followed")


class MaybeMoved(object):
    """A fake host whose `/v1/maybe` answers the thing's state until `moved` is set, then a redirect (SEC-2)."""

    def __init__(self, machine, token):
        self.m = machine
        self.records = []
        self.moved = False

    def request(self, host, method, path, headers, timeout):
        self.records.append({"host": host, "method": method, "path": path})
        if self.moved:
            return 302, b""
        return 200, json.dumps({"state": "active"}).encode("utf-8")

class FakeHosts(object):
    """The fake hosts of the frame's own requests (SEC-2). Each request is recorded with its host, method and path, whether an
    authorization header arrived, and whether its hash is the expected token's; the header itself is never stored (SEC-11).
    `api.fakehost.invalid` keeps its things in the fake host's own state, which its fake program reads too."""

    def __init__(self, machine, token):
        self.m = machine
        self.expected = hashlib.sha256(("Bearer " + token).encode("utf-8")).hexdigest() if token else None
        self.records = []

    def request(self, host, method, path, headers, timeout):
        header = (headers or {}).get("Authorization")
        self.records.append({"host": host, "method": method, "path": path, "auth": header is not None,
                             "auth_ok": header is not None and hashlib.sha256(header.encode("utf-8")).hexdigest() == self.expected})
        header = None
        parts = [urllib.parse.unquote(p) for p in path.strip("/").split("/")]
        if host != "api.fakehost.invalid":
            return 404, b"{}"
        state = self.m.fake("fakehost", "state.json") or {"account": "fixture-account", "things": {}, "refs": {}, "requests": {}}
        if parts[:2] == ["v1", "moved"]:
            return 302, b""
        if method == "PUT" and parts[:2] == ["v1", "things"] and len(parts) == 3:
            name = parts[2]
            if name in state["things"]:
                return 409, b"{}"
            ident = "i" + hashlib.sha256(("%s:%d" % (name, len(self.records))).encode()).hexdigest()[:14]
            state["things"][name] = {"id": ident, "kind": "repo", "state": "active", "name": name}
            self.m.set_fake("fakehost", things=state["things"])
            return 201, json.dumps({"id": ident, "name": name}).encode("utf-8")
        if method == "GET" and parts[:2] == ["v1", "ids"] and len(parts) == 3:
            for thing in state["things"].values():
                if thing.get("id") == parts[2]:
                    return 200, json.dumps({"state": thing["state"], "id": thing["id"]}).encode("utf-8")
            return 404, b"{}"
        return 404, b"{}"


def request_providers():
    """The fake providers, with three requests of the fake host's own and one of a second provider's (SEC-2)."""
    decls = rowlib.providers()

    def request(method, parts, fields, **more):
        out = {"tool": "fakehost", "via": "request", "method": method, "template": parts, "time_limit": 20, "effects": 0,
               "exits": {"200": "success", "201": "success", "404": "not-found", "409": "conflict"}, "fields": fields,
               "definite": {"success": ["success"], "refusals": ["not-found", "conflict"]}}
        out.update(more)
        return out
    host = decls["fakehost"]["commands"]
    host["api-create"] = request("PUT", [{"literal": "v1"}, {"literal": "things"}, {"param": "name"}],
                                 [rowlib._field("id", "id", "held", **rowlib.IDF), rowlib._field("name", "name", "equal", equals={"param": "name"}, **rowlib.NAMEF)],
                                 effects=1)
    host["api-by-id"] = request("GET", [{"literal": "v1"}, {"literal": "ids"}, {"param": "id"}],
                                [rowlib._field("state", "state", "fixed", list=rowlib.STATES), rowlib._field("id", "id", "held", **rowlib.IDF)])
    host["api-moved"] = request("GET", [{"literal": "v1"}, {"literal": "moved"}], [rowlib._field("state", "state", "fixed", list=rowlib.STATES)],
                                exits={"200": "success", "302": "other"})
    other = json.loads(json.dumps(decls["fakehost"]))
    other.update({"provider": "fakeother", "host": "api.other.invalid", "token": None, "credential_env": [], "identity": rowlib.NONE})
    other["commands"] = {"api-by-id": dict(host["api-by-id"], tool="fakeother")}
    decls["fakeother"] = other
    return decls


class TheFramesOwnRequest(Case):
    """SEC-2: "The hosting token is read in-process by one function, from the environment variable, else from the hosting
    tool's own credentials file opened read-only (the owner's ruling, A2). It is used only in requests the frame itself
    makes to the provider's fixed host, over TLS, following no redirect and logging no request, and is then dropped. ... A
    held value (SEC-4) goes back to the provider that issued it in such a request of the frame's own, to that provider's
    fixed host and to no other, or through a protected input; it travels no other way." Its test line: "the fake host
    records that the authorization header arrived with the right hash and that no redirect was followed; a held id reaches
    the fake host that issued it in the frame's own request and reaches no other host and no child's argument; with the
    environment variable absent and a fixture credentials file present, the same header arrives, and the fixture file
    system shows that file opened read-only and left byte-equal". SEC-11: "The fake host records only that an
    authorization header arrived and whether its hash is the expected token's; it never stores the header."""

    def made_by_request(self):
        row = rowlib.create("C1")
        row["commands"] = [rowlib.use("look", "fakehost.get", name=rowlib.NAME), rowlib.use("make", "fakehost.api-create", name=rowlib.NAME),
                           rowlib.use("by-id", "fakehost.api-by-id", id={"output": "remote.id"})]
        return row

    def machine(self, rows, token, by_file=False):
        self.count += 1
        m = harness.Machine(self.tmp, "q%d" % self.count, "q%d" % self.count)
        rowlib.install(m, rowlib.lane("sunrise", rows), providers=request_providers())
        m.put("shortcuts.txt", "alias other\n")
        if by_file:
            m.settings["locations"]["fakehost_credentials"] = m.put(".fakehost/credentials.json", json.dumps({"token": token}), 0o600)
            m.write_settings()
        else:
            m.env["FAKEHOST_TOKEN"] = token
        m.transport = FakeHosts(m, token)
        return m

    def test_SEC2_the_frames_own_request_carries_the_token_to_the_fixed_host_follows_no_redirect_and_a_held_id_goes_back_to_its_issuer_only(self):
        token = harness.canary("hosting-token")
        for case in ("the environment variable", "the credentials file"):
            with self.subTest(token_from=case):
                m = self.machine([self.made_by_request()], token, by_file=case == "the credentials file")
                credentials = m.path(".fakehost", "credentials.json")
                before = open(credentials, "rb").read() if os.path.exists(credentials) else None
                looked, went = m.started()
                self.assertEqual(went.ending, "complete", went.text)
                records = m.transport.records
                self.assertTrue(records, "no request of the frame's own was made")
                for record in records:
                    self.assertEqual(record["host"], "api.fakehost.invalid", "a request went to a host other than the provider's own")
                    self.assertTrue(record["auth"] and record["auth_ok"], "the authorization header did not arrive with the right hash")
                    self.assertNotIn("header", record)
                ident = [t["id"] for t in m.fake("fakehost", "state.json")["things"].values()][0]
                self.assertIn("/v1/ids/" + ident, [r["path"] for r in records], "the held id did not go back to the host that issued it")
                for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold"):
                    for call in m.calls(tool):
                        self.assertNotIn(ident, json.dumps(call), "the held id reached a child's argument")
                self.assertNowhere(ident, went)
                self.assertNowhere(token, went)
                if before is not None:
                    acts = [e for e in looked.events + went.events if e["subject"] == credentials]
                    self.assertTrue(acts, "the credentials file was not read")
                    self.assertEqual(set(e["stage"] for e in acts), {"read"}, "the credentials file was written")
                    self.assertEqual(open(credentials, "rb").read(), before, "the credentials file changed")

    def test_SEC2_a_redirect_is_not_followed(self):
        token = harness.canary("hosting-token-redirect")
        moved = rowlib.check("K1")
        moved["thing"]["passes"] = [{"read": "command", "command": "moved", "result": "success", "field": "state", "equals": "active"}]
        moved["commands"] = [rowlib.use("moved", "fakehost.api-moved")]
        m = self.machine([moved], token)
        looked, went = m.started()
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual([(r["host"], r["path"]) for r in m.transport.records], [("api.fakehost.invalid", "/v1/moved")],
                         "a redirect was followed, or no request was made")

    def test_SEC2_the_real_transport_is_one_request_over_TLS_with_the_systems_checks_and_follows_no_redirect(self):
        """SEC-2: "over TLS, following no redirect and logging no request". The real transport, with the network stood in for
        by a recording connection in this process: one connection to the host's port 443 with a context that checks the
        certificate and the host name; a redirect answered is handed back as the answer, and no second request is made."""
        import http.client
        import ssl
        from sun_core import hostcall
        made = []

        class Connection(object):
            def __init__(self, host, port, timeout=None, context=None):
                made.append({"host": host, "port": port, "verify": context.verify_mode == ssl.CERT_REQUIRED,
                             "hostname": context.check_hostname, "requests": []})

            def request(self, method, path, headers=None):
                made[-1]["requests"].append((method, path, sorted((headers or {}).keys())))

            def getresponse(self):
                class Response(object):
                    status = 302

                    def read(self, most):
                        return b""
                return Response()

            def close(self):
                made[-1]["closed"] = True
        real = http.client.HTTPSConnection
        http.client.HTTPSConnection = Connection
        try:
            answer = hostcall.TLS().request("api.fakehost.invalid", "GET", "/v1/moved", {"Authorization": "Bearer x"}, 5)
        finally:
            http.client.HTTPSConnection = real
        self.assertEqual(answer, (302, b""))
        self.assertEqual(len(made), 1, "more than one connection: a redirect was followed")
        self.assertEqual((made[0]["host"], made[0]["port"], made[0]["verify"], made[0]["hostname"]), ("api.fakehost.invalid", 443, True, True))
        self.assertEqual(made[0]["requests"], [("GET", "/v1/moved", ["Authorization"])])
        self.assertTrue(made[0].get("closed"))

    def test_SEC2_a_held_id_sent_to_a_provider_that_did_not_issue_it_fails_the_build(self):
        token = harness.canary("hosting-token-other")
        elsewhere = rowlib.check("K2", needs=[{"output": "remote", "level": "made", "treatment": "then not applicable"}])
        elsewhere["thing"]["passes"] = [{"read": "command", "command": "there", "result": "success", "field": "state", "equals": "active"}]
        elsewhere["commands"] = [rowlib.use("there", "fakeother.api-by-id", id={"output": "remote.id"})]
        m = self.machine([self.made_by_request(), elsewhere], token)
        looked = m.look()
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row K2, entry commands: a held value goes back only to the provider that issued it (SEC-2)", looked.lines)
        self.assertEqual(m.transport.records, [], "a request was made")


if __name__ == "__main__":
    unittest.main()
