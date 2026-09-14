"""The answer-key match forms of lane contract section 5.9 (recheck-v2 E7, lane CHECKS).

Standard library only, Python 3.9.

    match(expected, actual) -> (bool, [reason, ...])

`expected` is a partial document written in the key's vocabulary; `actual` is the document a
run produced. Every reason is annotated with the JSON path where the comparison failed.

| Form                     | Meaning                                                                   |
|--------------------------|---------------------------------------------------------------------------|
| scalar                   | equal (booleans never equal numbers)                                       |
| object                   | every expected key matches; extra actual keys allowed unless `$exact` true |
| array                    | same length, element-wise, in order                                        |
| `{"$unordered": [...]}`  | same multiset, any order (each expected element consumes one actual one)   |
| `{"$contains": [...]}`   | each expected element matches some actual element                          |
| `{"$len": n}`            | array length (a string or object is measured the same way)                 |
| `"$any"`                 | key present, any value                                                     |
| `"$absent"`              | key absent                                                                 |
| `{"$re": "pattern"}`     | string matches the regular expression (`re.search`)                        |
| `{"$in": [...]}`         | value equals one of these                                                  |
| `{"$not": X}`            | X does not match                                                           |

`validate_form(expected)` checks the syntax of a key's `expected` without an actual document:
every `$`-key is one of the forms above with the right operand type, an operator object holds
nothing else, and the only `$`-strings are `"$any"` and `"$absent"`.
"""
import re

OPERATORS = ("$unordered", "$contains", "$len", "$re", "$in", "$not")
STRING_FORMS = ("$any", "$absent")
_MISSING = object()


def _fmt(value):
    text = repr(value)
    return text if len(text) <= 80 else text[:77] + "..."


def _join(path, key):
    if isinstance(key, int):
        return "%s[%d]" % (path, key)
    return "%s.%s" % (path, key) if path else key


def _scalar_equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    return a == b


def _operator_of(expected):
    """Return the operator key of an operator object, else None."""
    if not isinstance(expected, dict):
        return None
    ops = [k for k in expected if k in OPERATORS]
    return ops[0] if ops else None


def _match(expected, actual, path, reasons):
    # ---- the two string forms ----------------------------------------------------------
    if expected == "$any":
        if actual is _MISSING:
            reasons.append("%s: expected the key to be present" % path)
            return False
        return True
    if expected == "$absent":
        if actual is not _MISSING:
            reasons.append("%s: expected the key to be absent, got %s" % (path, _fmt(actual)))
            return False
        return True
    if actual is _MISSING:
        reasons.append("%s: key absent, expected %s" % (path, _fmt(expected)))
        return False

    # ---- operator objects ----------------------------------------------------------------
    op = _operator_of(expected)
    if op is not None:
        operand = expected[op]
        if op == "$len":
            try:
                n = len(actual)
            except TypeError:
                reasons.append("%s: $len against a value with no length: %s" % (path, _fmt(actual)))
                return False
            if n != operand:
                reasons.append("%s: expected length %r, got %r" % (path, operand, n))
                return False
            return True
        if op == "$re":
            if not isinstance(actual, str):
                reasons.append("%s: $re against a non-string: %s" % (path, _fmt(actual)))
                return False
            if re.search(operand, actual) is None:
                reasons.append("%s: %s does not match /%s/" % (path, _fmt(actual), operand))
                return False
            return True
        if op == "$in":
            if any(_scalar_equal(actual, choice) if not isinstance(choice, (dict, list)) else actual == choice
                   for choice in operand):
                return True
            reasons.append("%s: %s is not one of %s" % (path, _fmt(actual), _fmt(operand)))
            return False
        if op == "$not":
            inner = []
            if _match(operand, actual, path, inner):
                reasons.append("%s: %s matched the negated form %s" % (path, _fmt(actual), _fmt(operand)))
                return False
            return True
        if op in ("$unordered", "$contains"):
            if not isinstance(actual, list):
                reasons.append("%s: %s against a non-array: %s" % (path, op, _fmt(actual)))
                return False
            if op == "$unordered" and len(actual) != len(operand):
                reasons.append("%s: expected %d elements in any order, got %d" % (path, len(operand), len(actual)))
                return False
            used = set()
            ok = True
            for i, exp_el in enumerate(operand):
                found = None
                for j, act_el in enumerate(actual):
                    if j in used:
                        continue
                    if _match(exp_el, act_el, _join(path, j), []):
                        found = j
                        break
                if found is None:
                    reasons.append("%s: no %selement matches expected[%d] = %s"
                                   % (path, "unused " if op == "$unordered" else "", i, _fmt(exp_el)))
                    ok = False
                else:
                    used.add(found)
            return ok

    # ---- plain objects -------------------------------------------------------------------
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            reasons.append("%s: expected an object, got %s" % (path, _fmt(actual)))
            return False
        exact = expected.get("$exact", False)
        ok = True
        for key, exp_val in expected.items():
            if key == "$exact":
                continue
            if not _match(exp_val, actual.get(key, _MISSING), _join(path, key), reasons):
                ok = False
        if exact:
            extra = sorted(k for k in actual if k not in expected)
            if extra:
                reasons.append("%s: extra keys under $exact: %s" % (path, ", ".join(extra)))
                ok = False
        return ok

    # ---- arrays --------------------------------------------------------------------------
    if isinstance(expected, list):
        if not isinstance(actual, list):
            reasons.append("%s: expected an array, got %s" % (path, _fmt(actual)))
            return False
        if len(expected) != len(actual):
            reasons.append("%s: expected %d elements, got %d" % (path, len(expected), len(actual)))
            return False
        ok = True
        for i, (e, a) in enumerate(zip(expected, actual)):
            if not _match(e, a, _join(path, i), reasons):
                ok = False
        return ok

    # ---- scalars -------------------------------------------------------------------------
    if not _scalar_equal(expected, actual):
        reasons.append("%s: expected %s, got %s" % (path, _fmt(expected), _fmt(actual)))
        return False
    return True


def match(expected, actual, path="$"):
    """Match a partial expected document against an actual one.

    Returns (ok, reasons); reasons is empty when ok is True.
    """
    reasons = []
    ok = _match(expected, actual, path, reasons)
    return ok, reasons


def validate_form(expected, path="$"):
    """Return a list of syntax problems in a key's expected document (empty when well-formed)."""
    problems = []

    def walk(node, p):
        if isinstance(node, str):
            if node.startswith("$") and node not in STRING_FORMS:
                problems.append("%s: unknown string form %r" % (p, node))
            return
        if isinstance(node, list):
            for i, el in enumerate(node):
                walk(el, _join(p, i))
            return
        if not isinstance(node, dict):
            return
        dollar = [k for k in node if k.startswith("$")]
        ops = [k for k in dollar if k in OPERATORS]
        unknown = [k for k in dollar if k not in OPERATORS and k != "$exact"]
        for k in unknown:
            problems.append("%s: unknown operator key %r" % (p, k))
        if len(ops) > 1:
            problems.append("%s: several operators in one object: %s" % (p, ", ".join(ops)))
        if ops:
            op = ops[0]
            others = [k for k in node if k != op]
            if others:
                problems.append("%s: operator object %s carries other keys: %s" % (p, op, ", ".join(others)))
            operand = node[op]
            if op == "$len" and (isinstance(operand, bool) or not isinstance(operand, int) or operand < 0):
                problems.append("%s: $len needs a non-negative integer, got %s" % (p, _fmt(operand)))
            elif op == "$re":
                if not isinstance(operand, str):
                    problems.append("%s: $re needs a string pattern, got %s" % (p, _fmt(operand)))
                else:
                    try:
                        re.compile(operand)
                    except re.error as exc:
                        problems.append("%s: $re pattern does not compile: %s" % (p, exc))
            elif op in ("$in", "$unordered", "$contains"):
                if not isinstance(operand, list):
                    problems.append("%s: %s needs an array, got %s" % (p, op, _fmt(operand)))
                elif op != "$in":
                    for i, el in enumerate(operand):
                        walk(el, _join(p, i))
            elif op == "$not":
                walk(operand, p + ".$not")
            return
        if "$exact" in node and not isinstance(node["$exact"], bool):
            problems.append("%s: $exact must be a boolean" % p)
        for k, v in node.items():
            if k == "$exact":
                continue
            walk(v, _join(p, k))

    walk(expected, path)
    return problems
