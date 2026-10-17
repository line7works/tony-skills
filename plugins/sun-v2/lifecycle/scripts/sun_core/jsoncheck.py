"""The tool's own check of its own schema files (RUN-1; the owner's ruling, A47: standard library only).

It knows the keywords of JSON Schema 2020-12 that the fourteen frozen schemas use, and no other: a schema
that uses any other keyword is refused as a schema (`schema_errors`), so that no keyword is ever silently
ignored. `errors(schema, document)` gives [{path, rule}] for every finding, the value never quoted (SEC-5).
"""
import re

KEYWORDS = frozenset(("$schema", "$id", "title", "description", "$defs", "$ref", "type", "enum", "const",
                      "properties", "required", "additionalProperties", "propertyNames", "minProperties",
                      "maxProperties", "items", "minItems", "maxItems", "uniqueItems", "maxLength", "minLength",
                      "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "oneOf", "anyOf",
                      "allOf", "not"))
TYPES = ("object", "array", "string", "integer", "number", "boolean", "null")
_patterns = {}


def _type_of(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _is(value, kind):
    actual = _type_of(value)
    if kind == "number":
        return actual in ("integer", "number")
    if kind == "integer" and actual == "number":
        return float(value).is_integer()
    return actual == kind


def _equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_equal(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


def _pattern(text):
    if text not in _patterns:
        _patterns[text] = re.compile(text)
    return _patterns[text]


def _length(text):
    """JSON Schema counts code points; Python's str is code points."""
    return len(text)


def schema_errors(schema, path="#"):
    """Every place where `schema` is not a schema this check can apply in full."""
    out = []
    if isinstance(schema, bool):
        return out
    if not isinstance(schema, dict):
        return [path + ": not a schema"]
    for key, value in schema.items():
        where = "%s/%s" % (path, key)
        if key not in KEYWORDS:
            out.append(where + ": a keyword this check does not know")
        elif key in ("properties", "$defs"):
            if not isinstance(value, dict):
                out.append(where + ": not an object")
            else:
                for name, sub in value.items():
                    out += schema_errors(sub, "%s/%s" % (where, name))
        elif key in ("items", "additionalProperties", "propertyNames", "not"):
            out += schema_errors(value, where)
        elif key in ("oneOf", "anyOf", "allOf"):
            if not isinstance(value, list) or not value:
                out.append(where + ": not a list of schemas")
            else:
                for i, sub in enumerate(value):
                    out += schema_errors(sub, "%s/%d" % (where, i))
        elif key == "type":
            kinds = value if isinstance(value, list) else [value]
            if not kinds or any(k not in TYPES for k in kinds):
                out.append(where + ": an unknown type")
        elif key == "$ref":
            if not isinstance(value, str) or not value.startswith("#/$defs/"):
                out.append(where + ": a reference this check does not follow")
        elif key == "pattern":
            try:
                _pattern(value)
            except (re.error, TypeError):
                out.append(where + ": not a pattern")
        elif key == "required":
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                out.append(where + ": not a list of names")
        elif key == "enum":
            if not isinstance(value, list):
                out.append(where + ": not a list")
        elif key in ("minProperties", "maxProperties", "minItems", "maxItems", "maxLength", "minLength"):
            if not (isinstance(value, int) and not isinstance(value, bool) and value >= 0):
                out.append(where + ": not a count")
        elif key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                out.append(where + ": not a number")
        elif key == "uniqueItems":
            if not isinstance(value, bool):
                out.append(where + ": not a truth value")
    return out


class Checker(object):
    def __init__(self, schema):
        found = schema_errors(schema)
        if found:
            raise ValueError("not a schema this check can apply: " + found[0])
        self.root = schema

    def _resolve(self, ref):
        node = self.root
        for part in ref[2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return node

    def errors(self, document):
        out = []
        self._check(self.root, document, "", out)
        out.sort(key=lambda row: (row["path"], row["rule"]))
        return out

    def _valid(self, schema, value):
        found = []
        self._check(schema, value, "", found)
        return not found

    def _check(self, schema, value, path, out):
        if schema is True:
            return
        if schema is False:
            out.append({"path": path or "/", "rule": "false"})
            return

        def fail(rule, where=None):
            out.append({"path": (where if where is not None else path) or "/", "rule": rule})
        if "$ref" in schema:
            self._check(self._resolve(schema["$ref"]), value, path, out)
        if "type" in schema:
            kinds = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_is(value, k) for k in kinds):
                fail("type")
                return
        if "enum" in schema and not any(_equal(value, e) for e in schema["enum"]):
            fail("enum")
        if "const" in schema and not _equal(value, schema["const"]):
            fail("const")
        for key, rule in (("oneOf", 1), ("anyOf", 0), ("allOf", -1)):
            if key in schema:
                passed = sum(1 for sub in schema[key] if self._valid(sub, value))
                if (rule == 1 and passed != 1) or (rule == 0 and passed < 1) or (rule == -1 and passed != len(schema[key])):
                    fail(key)
        if "not" in schema and self._valid(schema["not"], value):
            fail("not")
        if isinstance(value, dict):
            props = schema.get("properties") or {}
            for name in schema.get("required") or []:
                if name not in value:
                    fail("required")
            for name, item in value.items():
                where = "%s/%s" % (path, name)
                if name in props:
                    self._check(props[name], item, where, out)
                elif "additionalProperties" in schema:
                    self._check(schema["additionalProperties"], item, where, out)
                if "propertyNames" in schema:
                    self._check(schema["propertyNames"], name, where, out)
            if "minProperties" in schema and len(value) < schema["minProperties"]:
                fail("minProperties")
            if "maxProperties" in schema and len(value) > schema["maxProperties"]:
                fail("maxProperties")
        if isinstance(value, list):
            if "items" in schema:
                for i, item in enumerate(value):
                    self._check(schema["items"], item, "%s/%d" % (path, i), out)
            if "minItems" in schema and len(value) < schema["minItems"]:
                fail("minItems")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                fail("maxItems")
            if schema.get("uniqueItems"):
                for i in range(len(value)):
                    if any(_equal(value[i], value[j]) for j in range(i)):
                        fail("uniqueItems")
                        break
        if isinstance(value, str):
            if "maxLength" in schema and _length(value) > schema["maxLength"]:
                fail("maxLength")
            if "minLength" in schema and _length(value) < schema["minLength"]:
                fail("minLength")
            if "pattern" in schema and not _pattern(schema["pattern"]).search(value):
                fail("pattern")
        if _type_of(value) in ("integer", "number"):
            if "minimum" in schema and value < schema["minimum"]:
                fail("minimum")
            if "maximum" in schema and value > schema["maximum"]:
                fail("maximum")
            if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
                fail("exclusiveMinimum")
            if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
                fail("exclusiveMaximum")
