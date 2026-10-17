"""The frozen schemas of the lifecycle's records, and the tool's own check of them (the contract's CR-5
reading of the reviewer's D20 closing rule; RUN-1 and the owner's ruling A47: no outside package).

Every record a lane writes or reads has a schema under `../../references/`, closed at every level:
a row, a lane's rows file, a provider's declaration, a manifest, a journal record, a preview, a
form position, a CLI response, an input, a checklist, the settings file. They are checked by
`jsoncheck.py`, the tool's own code.
"""
import json
import os

from . import jsoncheck

NAMES = ("journal-record", "row", "lane", "provider", "manifest", "input", "cli-response", "settings",
         "checklist", "form-position", "preview", "open-runs", "lock-record", "capabilities")
_cache = {}


class Invalid(ValueError):
    """A record failed its schema. `errors` is [{path, message}], sorted."""

    def __init__(self, name, errors):
        ValueError.__init__(self, "%s: %s at %s" % (name, errors[0]["rule"], errors[0]["path"]) if errors else name)
        self.name = name
        self.errors = errors


def references_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(os.path.dirname(here)), "references")


def load(name):
    if name not in NAMES:
        raise KeyError(name)
    path = os.path.join(references_dir(), name + ".schema.json")
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def validator(name):
    if name not in _cache:
        _cache[name] = jsoncheck.Checker(load(name))
    return _cache[name]


def errors(name, document):
    """[{path, rule}] for every finding, sorted. No message quotes a value: a value is not ours to print (SEC-5)."""
    return validator(name).errors(document)


def check(name, document):
    found = errors(name, document)
    if found:
        raise Invalid(name, found)
    return document
