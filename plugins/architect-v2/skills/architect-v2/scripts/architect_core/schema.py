"""The recorded answer's schema (`references/answer.schema.json`, CR-8), loaded from the skill root.

`errors(answer)` returns `[{path, message}]`, empty when the answer holds its shape; the content
checks that a schema cannot state are `recording.py`'s. jsonschema is the one declared
dependency; without it the command exits 3 through `station_core/validate.require_jsonschema`.
"""
import json
import os

from station_core import validate

from .common import PREFIX

FILE = "answer.schema.json"


def load(root=None):
    validate.require_jsonschema(PREFIX)
    path = os.path.join(validate.references_dir(root), FILE)
    if not os.path.isfile(path):
        raise validate.ReferenceUnavailable("reference unavailable: references/%s" % FILE)
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except ValueError as exc:
        raise validate.ReferenceUnavailable("reference unavailable: references/%s (%s)" % (FILE, exc))
    return doc


# Every line boundary `str.splitlines` knows (round 7 R2): the template reader splits the doc on
# each of them, so any one inside a value would put a bare line, or a heading, inside a field.
LINE_BOUNDARIES = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")
SEPARATOR = "answer text must contain no line separator"


def errors(answer, root=None):
    """The schema's findings, then one finding for every string of the answer, at every depth, that
    holds a line boundary (`LINE_BOUNDARIES`), whatever the field's own pattern says; sorted by path.
    `record-answer` refuses any finding (exit 4) before it writes anything."""
    findings = validate.errors_for(answer, load(root), PREFIX)

    def visit(value, path):
        if isinstance(value, str):
            if any(ch in LINE_BOUNDARIES for ch in value):
                findings.append({"path": path or "/", "message": SEPARATOR})
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, path + "/" + str(index))
        elif isinstance(value, dict):
            for key, item in value.items():
                token = str(key).replace("~", "~0").replace("/", "~1")
                visit(item, path + "/" + token)

    visit(answer, "")
    findings.sort(key=lambda row: (row["path"], row["message"]))
    return findings
