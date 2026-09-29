"""The forms test that matters most (lane L, brief 3.6 and required test 7).

`build-v2`'s own reader reads the rendered build doc the way its `contract` phase does (the doc
read, then each slice found by name, with its status, requirements and named paths), and the
records importer reads it through the resolver and the CLI only: `import-legacy --dry-run` on a
scratch copy, which writes nothing. Both run on a new doc and on an extended one. In the installed
shape neither sibling sits beside this core, and the tests say so as skipped.
"""
import importlib.util
import os
import shutil
import sys
import unittest

import bplib
import testlib

testlib.add_scripts_to_path()

from station_core import records_link  # noqa: E402

BUILD_V2 = testlib.checkout_sibling("build-v2")
RECORDS = testlib.records_root()


def build_v2_doc_reader():
    """build-v2's `build_core/doc.py`, loaded from the checkout sibling by path (read only)."""
    path = os.path.join(BUILD_V2, "skills", "build-v2", "scripts", "build_core", "doc.py")
    spec = importlib.util.spec_from_file_location("build_v2_doc_reader", path)
    module = importlib.util.module_from_spec(spec)
    saved = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    return module


class _Rendered(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("bp-forms-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def rendered(self, files, answer):
        ws = testlib.git_workspace(self.tmp, "ws", files)
        run = bplib.Run(self.tmp, ws)
        run.to_harvest()
        code, out, err = run.record(answer)
        self.assertEqual(code, 0, (out, err))
        code, out, err = run.write()
        self.assertEqual(code, 0, (out, err))
        return ws, out["doc"]

    def new_doc(self):
        return self.rendered(bplib.base_files(), bplib.clean_answer())

    def extended_doc(self):
        return self.rendered(bplib.base_files(build=bplib.BUILD_FILLED), bplib.extension_answer())


@unittest.skipIf(BUILD_V2 is None, "no build-v2 beside this core (the installed shape): its reader "
                                   "cannot be loaded here, and this is reported as skipped, not passed")
class BuildV2Reads(_Rendered):

    def contract_view(self, ws, doc_path, name):
        reader = build_v2_doc_reader()
        text = reader.read(ws, os.path.relpath(doc_path, ws))
        entry = reader.find_slice(text, name)
        return reader, text, entry

    def test_every_slice_of_a_new_doc_with_its_status(self):
        ws, path = self.new_doc()
        reader, text, entry = self.contract_view(ws, path, "A")
        self.assertEqual([(e["name"], e["status"]) for e in reader.parse(text)], [("A", "not started")])
        self.assertEqual(entry["title"], "Count turns")
        self.assertEqual(reader.requirements(entry), ["R1 %s `spin(n)` returns `n + 1`" % bplib.D,
                                                      "R2 %s the count lives in memory only" % bplib.D])
        # the inline `Footprint:` form of the template gives this reader no named paths (see the report)
        self.assertEqual(reader.named_paths(entry), [])

    def test_every_slice_of_an_extended_doc_with_its_status(self):
        ws, path = self.extended_doc()
        reader, text, entry = self.contract_view(ws, path, "B")
        self.assertEqual([(e["name"], e["status"]) for e in reader.parse(text)],
                         [("A", "in progress"), ("B", "not started")])
        self.assertEqual(reader.requirements(entry), ["R2 %s `reset()` returns 0" % bplib.D])


@unittest.skipIf(RECORDS is None, "no records component beside this core (the installed shape): the "
                                  "importer cannot be reached here, and this is reported as skipped")
class TheImporterReads(_Rendered):

    def dry_run(self, ws, path):
        copy_ws = os.path.join(self.tmp, "importer-copy")
        shutil.copytree(ws, copy_ws, symlinks=True)
        before = testlib.tree_digest(copy_ws)
        client = records_link.open_client(testlib.CORE, records_root=RECORDS)
        body = client.import_legacy(copy_ws, os.path.relpath(path, ws), dry_run=True)
        self.assertEqual(before, testlib.tree_digest(copy_ws), "the dry run wrote nothing")
        return body

    def test_a_new_doc(self):
        ws, path = self.new_doc()
        body = self.dry_run(ws, path)
        self.assertEqual((body["dry_run"], body["ambiguous"], body["slices"]), (True, 0, 1))
        self.assertEqual(body["counts"].get("card_observed"), 1)

    def test_an_extended_doc(self):
        ws, path = self.extended_doc()
        body = self.dry_run(ws, path)
        self.assertEqual((body["dry_run"], body["ambiguous"], body["slices"]), (True, 0, 2))
        self.assertEqual(body["counts"].get("card_observed"), 2)
        self.assertEqual(body["counts"].get("finding_raised"), 1)


if __name__ == "__main__":
    unittest.main()
