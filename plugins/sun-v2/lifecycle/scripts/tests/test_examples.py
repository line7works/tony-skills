"""The frozen schemas and their examples (the brief's CR-5; the reviewer's D20 closing rule; the A7a helper interface).

Every record a lane writes or reads has a schema, closed at every level, with examples accepted and
rejected; `sun check-examples` checks them all with the tool's own check and is itself a helper under A7a.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

import harness
from sun_core import schemas

ENTRY = os.path.join(harness.SCRIPTS, "sun")


def run(*argv, **env):
    full = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    full.update(env)
    proc = subprocess.run(["/bin/sh", ENTRY, "check-examples"] + list(argv), env=full, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL, cwd=os.path.dirname(harness.PLUGIN))
    return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


def open_objects(node, path=""):
    """Every object schema that is not closed: no `additionalProperties`, or one that is true."""
    found = []
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            if node.get("additionalProperties", True) is True:
                found.append(path or "/")
        for key, value in node.items():
            found += open_objects(value, path + "/" + key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found += open_objects(value, "%s/%d" % (path, index))
    return found


class Examples(harness.Case):
    def test_CR5_every_example_of_every_schema_is_accepted_or_rejected_as_it_should_be(self):
        code, out, err = run()
        self.assertEqual(code, 0, out + err)
        doc = json.loads(out)
        self.assertEqual((doc["ok"], doc["schemas"], doc["failures"]), (True, len(schemas.NAMES), []))
        self.assertGreaterEqual(doc["valid"], 2 * len(schemas.NAMES))
        self.assertGreaterEqual(doc["invalid"], 2 * len(schemas.NAMES))
        self.assertEqual(err, "")

    def test_CR5_every_schema_is_closed_at_every_level(self):
        for name in schemas.NAMES:
            schema = schemas.load(name)
            still_open = open_objects(schema)
            self.assertEqual(still_open, [], "%s is not closed at %s" % (name, still_open[:3]))

    def test_A7a_the_validator_fails_on_an_example_that_misbehaves_and_keeps_its_exit_codes(self):
        copy = os.path.join(self.tmp, "references")
        shutil.copytree(schemas.references_dir(), copy)
        os.rename(os.path.join(copy, "examples", "input", "valid", "minimal.json"),
                  os.path.join(copy, "examples", "input", "invalid", "minimal.json"))
        code, out, _err = run("--references", copy)
        self.assertEqual(code, 4)
        self.assertEqual(json.loads(out)["failures"], ["input/invalid/minimal.json: accepted"])
        shutil.rmtree(os.path.join(copy, "examples", "settings", "invalid"))
        code, out, _err = run("--references", copy)
        self.assertIn("settings: no rejected example", json.loads(out)["failures"])
        code, out, err = run("--no-such-flag")
        self.assertEqual((code, out), (2, ""))
        code, out, err = run("--help")
        self.assertEqual(code, 0)
        self.assertIn("Side effects: none; it only reads.", out)

    def test_E16_15_every_response_of_the_check_of_examples_carries_interface_version_1(self):
        # E16-15: "`interface_version` 1 in every CLI response"; the check of examples is a command of the tool
        copy = os.path.join(self.tmp, "references-e16-15")
        shutil.copytree(schemas.references_dir(), copy)
        os.rename(os.path.join(copy, "examples", "input", "valid", "minimal.json"),
                  os.path.join(copy, "examples", "input", "invalid", "minimal.json"))
        for argv, exit_code in (((), 0), (("--references", copy), 4)):
            with self.subTest(argv=argv):
                code, out, _err = run(*argv)
                self.assertEqual(code, exit_code)
                doc = json.loads(out)
                self.assertEqual(doc.get("interface_version"), 1, "no interface_version in the response")
                self.assertEqual((doc.get("tool"), doc.get("command"), doc.get("exit")), ("sun-v2", "check-examples", exit_code))


if __name__ == "__main__":
    unittest.main()
