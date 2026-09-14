"""checkpoint.schema.json copies definitions from the two source schemas; this test catches drift.

The result schema's definitions are copied under their own names. The input schema's are copied
under the prefix input_ (its location definition differs from the result's: a workspace-relative
file versus any non-empty string), with every internal "#/$defs/<name>" reference rewritten to
"#/$defs/input_<name>" so the copies stay self-contained. A copy must equal its source after
that one documented rewrite, and both new schemas must resolve no cross-file reference.
"""
import json
import os
import unittest

import testlib

INPUT_DEFS = ["contained_relative_path", "claim", "location", "record_provenance", "item", "item_ref", "grant", "waiver_grant"]
RESULT_DEFS = ["location", "evidence", "verification", "adjudication", "grant_mark", "item_result", "new_defect", "identity_full"]
OWN_DEFS = ["integrity", "item_state", "verifier_call"]


def rewrite_refs(node, prefix):
    if isinstance(node, dict):
        return {k: ("#/$defs/" + prefix + v[len("#/$defs/"):] if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/") else rewrite_refs(v, prefix))
                for k, v in node.items()}
    if isinstance(node, list):
        return [rewrite_refs(v, prefix) for v in node]
    return node


def refs_in(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref":
                out.append(v)
            else:
                refs_in(v, out)
    elif isinstance(node, list):
        for v in node:
            refs_in(v, out)
    return out


class CopiedDefinitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inp = testlib.load_json(os.path.join(testlib.REF, "input.schema.json"))
        cls.res = testlib.load_json(os.path.join(testlib.REF, "result.schema.json"))
        cls.cp = testlib.load_json(os.path.join(testlib.REF, "checkpoint.schema.json"))
        cls.rc = testlib.load_json(os.path.join(testlib.REF, "receipt.schema.json"))

    def test_result_definitions_verbatim(self):
        for name in RESULT_DEFS:
            self.assertIn(name, self.cp["$defs"], name)
            self.assertEqual(self.cp["$defs"][name], self.res["$defs"][name],
                             "checkpoint $defs/%s drifted from result.schema.json" % name)

    def test_input_definitions_under_prefix(self):
        for name in INPUT_DEFS:
            copy_name = "input_" + name
            self.assertIn(copy_name, self.cp["$defs"], copy_name)
            self.assertEqual(self.cp["$defs"][copy_name], rewrite_refs(self.inp["$defs"][name], "input_"),
                             "checkpoint $defs/%s drifted from input.schema.json $defs/%s" % (copy_name, name))

    def test_no_unexpected_definition(self):
        expected = set(RESULT_DEFS) | {"input_" + n for n in INPUT_DEFS} | set(OWN_DEFS)
        self.assertEqual(set(self.cp["$defs"]), expected)

    def test_self_contained(self):
        for name, schema in (("checkpoint", self.cp), ("receipt", self.rc)):
            refs = refs_in(schema, [])
            self.assertTrue(refs, name)
            for ref in refs:
                self.assertTrue(ref.startswith("#/$defs/"), "%s carries a cross-file reference: %s" % (name, ref))
                self.assertIn(ref[len("#/$defs/"):], schema["$defs"], "%s dangles: %s" % (name, ref))

    def test_integrity_blocks_agree(self):
        a = dict(self.cp["$defs"]["integrity"]); b = dict(self.rc["$defs"]["integrity"])
        a.pop("description"); b.pop("description")
        self.assertEqual(a, b, "the receipt carries the same integrity block as the checkpoint (section 11)")

    def test_source_schemas_untouched_by_the_copy(self):
        """The copies are read from the sources, never the reverse: the sources keep their own $ref names."""
        self.assertEqual(self.inp["$defs"]["item"]["properties"]["location"]["$ref"], "#/$defs/location")
        self.assertEqual(self.res["$defs"]["item_result"]["properties"]["location"]["$ref"], "#/$defs/location")
        self.assertNotEqual(self.inp["$defs"]["location"], self.res["$defs"]["location"],
                            "the two location definitions differ, which is why the input copies carry a prefix")

    def test_serialization_style(self):
        for name in ("checkpoint.schema.json", "receipt.schema.json"):
            with open(os.path.join(testlib.REF, name), "rb") as fh:
                raw = fh.read()
            self.assertEqual(raw, (json.dumps(json.loads(raw), indent=2, ensure_ascii=True) + "\n").encode("utf-8"),
                             "%s is not the folder's json.dumps(indent=2) style" % name)


if __name__ == "__main__":
    unittest.main()
