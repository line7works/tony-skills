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


def errors(answer, root=None):
    return validate.errors_for(answer, load(root), PREFIX)
