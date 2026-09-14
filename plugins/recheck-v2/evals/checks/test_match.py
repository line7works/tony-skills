"""Unit tests for match.py: every section 5.9 form with a passing and a failing example.

Run: python3 -m unittest test_match  (from this folder) or python3 test_match.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match import match, validate_form  # noqa: E402


class MatchForms(unittest.TestCase):
    def ok(self, expected, actual):
        result, reasons = match(expected, actual)
        self.assertTrue(result, reasons)
        self.assertEqual(reasons, [])

    def bad(self, expected, actual, fragment=None):
        result, reasons = match(expected, actual)
        self.assertFalse(result)
        self.assertTrue(reasons)
        if fragment:
            self.assertTrue(any(fragment in r for r in reasons), reasons)

    # scalar
    def test_scalar(self):
        self.ok("completed", "completed")
        self.ok(3, 3)
        self.ok(None, None)
        self.bad("completed", "stopped", "expected 'completed'")
        self.bad(1, True)   # booleans never equal numbers
        self.bad(True, 1)

    # object, with and without $exact
    def test_object(self):
        self.ok({"a": 1}, {"a": 1, "b": 2})
        self.bad({"a": 1}, {"a": 2}, "$.a")
        self.bad({"a": 1}, {"b": 1}, "key absent")
        self.bad({"a": 1}, [1], "expected an object")

    def test_object_exact(self):
        self.ok({"$exact": True, "a": 1}, {"a": 1})
        self.bad({"$exact": True, "a": 1}, {"a": 1, "b": 2}, "extra keys under $exact: b")

    # array
    def test_array(self):
        self.ok([1, {"x": "y"}], [1, {"x": "y", "z": 0}])
        self.bad([1, 2], [2, 1], "$[0]")
        self.bad([1, 2], [1, 2, 3], "expected 2 elements, got 3")
        self.bad([1], "not a list", "expected an array")

    # $unordered
    def test_unordered(self):
        self.ok({"$unordered": [{"k": "b"}, {"k": "a"}]}, [{"k": "a", "n": 1}, {"k": "b"}])
        self.bad({"$unordered": [{"k": "a"}, {"k": "a"}]}, [{"k": "a"}, {"k": "b"}], "no unused element")
        self.bad({"$unordered": [1]}, [1, 1], "expected 1 elements in any order, got 2")

    # $contains
    def test_contains(self):
        self.ok({"$contains": [{"kind": "status_line"}]},
                [{"kind": "punch_list_block", "path": "x"}, {"kind": "status_line", "path": "x"}])
        self.bad({"$contains": [{"kind": "waived_line"}]}, [{"kind": "status_line"}], "no element matches")
        self.bad({"$contains": [1]}, {"1": 1}, "against a non-array")

    # $len
    def test_len(self):
        self.ok({"$len": 0}, [])
        self.ok({"$len": 2}, ["a", "b"])
        self.bad({"$len": 1}, [], "expected length 1, got 0")
        self.bad({"$len": 1}, 5, "no length")

    # $any and $absent
    def test_any(self):
        self.ok({"reason": "$any"}, {"reason": None})
        self.bad({"reason": "$any"}, {}, "expected the key to be present")

    def test_absent(self):
        self.ok({"reason": "$absent"}, {"disposition": "fixed"})
        self.bad({"reason": "$absent"}, {"reason": "reproduces"}, "expected the key to be absent")

    # $re
    def test_re(self):
        self.ok({"$re": "/run/verifier/"}, "/tmp/x/run/verifier/raw.md")
        self.ok({"$re": "^stopped: "}, "stopped: reused run id")
        self.bad({"$re": "^stopped"}, "completed", "does not match")
        self.bad({"$re": "x"}, 12, "non-string")

    # $in
    def test_in(self):
        self.ok({"$in": ["partial", "not_clear"]}, "partial")
        self.bad({"$in": ["partial", "not_clear"]}, "all_clear", "is not one of")
        self.bad({"$in": [1]}, True)

    # $not
    def test_not(self):
        self.ok({"$not": "e3b0"}, "9be9")
        self.ok({"$not": {"$len": 0}}, [1])
        self.bad({"$not": "e3b0"}, "e3b0", "matched the negated form")

    # nesting and path annotation
    def test_nested_paths(self):
        expected = {"items": [{"location": {"line": 42}, "reason": "$absent"}]}
        actual = {"items": [{"location": {"file": "a", "line": 41}, "reason": "reproduces"}]}
        ok, reasons = match(expected, actual)
        self.assertFalse(ok)
        self.assertEqual(len(reasons), 2)
        self.assertTrue(reasons[0].startswith("$.items[0].location.line:"), reasons)
        self.assertTrue(reasons[1].startswith("$.items[0].reason:"), reasons)


class ValidateForm(unittest.TestCase):
    def test_well_formed(self):
        doc = {"status": "completed", "items": [{"reason": "$absent", "verification": {"method": "$any"}}],
               "records_written": {"$contains": [{"kind": "status_line"}]}, "rejected_grants": {"$len": 0},
               "run": {"run_dir": {"$re": "/run$"}}, "result": {"$in": ["partial"]},
               "x": {"$not": {"$unordered": [1, 2]}}, "y": {"$exact": True, "a": 1}}
        self.assertEqual(validate_form(doc), [])

    def test_malformed(self):
        self.assertTrue(validate_form({"a": "$maybe"}))
        self.assertTrue(validate_form({"a": {"$len": "3"}}))
        self.assertTrue(validate_form({"a": {"$len": -1}}))
        self.assertTrue(validate_form({"a": {"$re": "("}}))
        self.assertTrue(validate_form({"a": {"$re": 3}}))
        self.assertTrue(validate_form({"a": {"$in": "x"}}))
        self.assertTrue(validate_form({"a": {"$contains": [1], "b": 2}}))
        self.assertTrue(validate_form({"a": {"$contains": [1], "$len": 1}}))
        self.assertTrue(validate_form({"a": {"$regex": "x"}}))
        self.assertTrue(validate_form({"a": {"$exact": "yes"}}))
        self.assertTrue(validate_form({"a": {"$not": {"$bogus": 1}}}))


if __name__ == "__main__":
    unittest.main()
