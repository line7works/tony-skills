"""The values a row and a manifest hold (the frame's RUN-6, RUN-8).

A row writes a value as one of these marks:

    {"literal": x}                 safe content written in the row: the fixed words of a declaration
    {"input": "description"}       the owner's own validated word (a dotted path into the saved inputs)
    {"name": 0}                    a name the summons carries, by its place
    {"location": "developer_root"} a machine location, from the one module that resolves them
    {"run": "id"}                  the run's own id, which the tool made
    {"fact": "has_database"}       a planning fact the look settled
    {"path": [V, ...]}             a path the tool builds from other values
    {"text": [V, ...]}             a text the tool builds from other values
    {"output": "name.field"}       a field of an output an operation of the same plan provides
    {"record": {...}}              a reference to a protected record
    {"saved": 0}                   in a reverse row: the input its forward row saved at that place of its
                                   `reverse_inputs` (LOG-2); a restore binds it to its own copy of that record (EV-5, EV-6)
    {"local": {"path": V, "validator": W}}
                                   the content of a file on this machine, read in-process at the look: safe where the
                                   validator the row declares has passed (SEC-1's fourth safe source), and otherwise
                                   protected, resting in a protected record the manifest refers to

When a manifest is built, `freeze` settles everything the look knows, so that every value in a
manifest is a literal, a reference to a protected record, or a reference to an output's field
(alone, or inside a path or a text built from them). `resolve` gives the value at run time, once
the outputs it refers to exist; a held field resolves to a `Held`, which is no text and can go
nowhere a text goes.
"""
import os
import re

# The validators a row may declare to make the content of a file on this machine safe (SEC-1; ROW-1). Each can refuse a
# value; the content is safe only where the one its row names has passed, and none can make a provider's value safe.
VALIDATORS = {
    "one line of plain words": re.compile(r"[A-Za-z0-9][A-Za-z0-9 .,:;'()/_+-]{0,199}"),
}


class Unsettled(Exception):
    """A value refers to an output that does not exist yet, or to nothing."""


class Held(object):
    """A held value in use: its protected record's reference, and nothing that prints."""

    def __init__(self, reference):
        self.reference = reference

    def __repr__(self):
        return "<held>"


def _dig(doc, dotted):
    node = doc
    for part in str(dotted).split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            raise Unsettled(dotted)
    return node


def freeze(value, look):
    """`value` with everything the look knows settled into literals. `look` has `inputs`, `names`,
    `locations` and `facts`."""
    if isinstance(value, list):
        return [freeze(v, look) for v in value]
    if not isinstance(value, dict):
        return value
    if "literal" in value or "output" in value or "record" in value:
        return dict(value)
    if "input" in value:
        return {"literal": _dig(look.inputs, value["input"])}
    if "name" in value:
        return {"literal": _dig(look.names, value["name"])}
    if "run" in value:
        return {"literal": look.run_id}
    if "location" in value:
        if value["location"] not in look.locations:
            raise Unsettled(value["location"])
        return {"literal": look.locations[value["location"]]}
    if "fact" in value:
        return {"literal": _dig(look.facts, value["fact"])}
    if "local" in value:
        reader = getattr(look, "local", None)
        where = freeze(value["local"].get("path"), look)
        if reader is None or not isinstance(where, dict) or "literal" not in where:
            raise Unsettled("a file on this machine the look cannot read")
        return reader(str(where["literal"]), value["local"].get("validator"))
    for key in ("path", "text"):
        if key in value:
            parts = [freeze(v, look) for v in value[key]]
            if all(isinstance(p, dict) and "literal" in p for p in parts):
                texts = [str(p["literal"]) for p in parts]
                return {"literal": os.path.join(*texts) if key == "path" else "".join(texts)}
            return {key: parts}
    return dict((k, freeze(v, look)) for k, v in value.items())


def is_mark(node):
    """Whether a node is one of the marks, by its one key and the shape of what it holds (a command's
    parameter may bear the same name as a mark's key)."""
    if not isinstance(node, dict) or len(node) != 1:
        return False
    key, held = list(node.items())[0]
    if key == "literal":
        return isinstance(held, (str, int, float, bool))
    if key in ("input", "location", "fact", "output"):
        return isinstance(held, str)
    if key == "name":
        return isinstance(held, (int, str)) and not isinstance(held, bool)
    if key == "run":
        return held == "id"
    if key in ("path", "text"):
        return isinstance(held, list)
    if key == "record":
        return isinstance(held, dict) and "fingerprint" in held
    if key == "saved":
        return isinstance(held, int) and not isinstance(held, bool) and held >= 0
    if key == "local":
        return isinstance(held, dict) and "path" in held and "validator" in held
    return False


def validators_named(node):
    """Every validator a `local` mark names, anywhere in a row's entries."""
    out = []
    if isinstance(node, list):
        for item in node:
            out += validators_named(item)
    elif isinstance(node, dict):
        if is_mark(node) and "local" in node:
            out.append(node["local"].get("validator"))
        else:
            for item in node.values():
                out += validators_named(item)
    return out


def freeze_all(node, look):
    """Every mark inside a row's entry frozen, wherever it stands."""
    if isinstance(node, list):
        return [freeze_all(v, look) for v in node]
    if isinstance(node, dict):
        if is_mark(node):
            return freeze(node, look)
        return dict((k, freeze_all(v, look)) for k, v in node.items())
    return node


def bind_saved(node, records):
    """Every {"saved": n} mark of a reverse row replaced by {"record": records[n]}. Raises Unsettled where n names no record."""
    if isinstance(node, list):
        return [bind_saved(v, records) for v in node]
    if isinstance(node, dict):
        if is_mark(node) and "saved" in node:
            if node["saved"] >= len(records):
                raise Unsettled("a saved input the forward operation did not save")
            return {"record": records[node["saved"]]}
        return dict((k, bind_saved(v, records)) for k, v in node.items())
    return node


def refers_to(node):
    """Every output field a value, or anything holding values, refers to."""
    out = []
    if isinstance(node, list):
        for item in node:
            out += refers_to(item)
    elif isinstance(node, dict):
        if is_mark(node) and "output" in node:
            out.append(node["output"])
        else:
            for item in node.values():
                out += refers_to(item)
    return out


def resolve(value, outputs):
    """The value now. `outputs` is {output name: {field: value or Held}} of what is bound."""
    if not isinstance(value, dict):
        return value
    if "literal" in value:
        return value["literal"]
    if "record" in value:
        return Held(value["record"])
    if "output" in value:
        name, _, field = value["output"].partition(".")
        if name not in outputs or field not in outputs[name]:
            raise Unsettled(value["output"])
        return outputs[name][field]
    for key in ("path", "text"):
        if key in value:
            parts = [resolve(v, outputs) for v in value[key]]
            if any(isinstance(p, Held) for p in parts):
                raise Unsettled("a held value is no part of a text")
            texts = [str(p) for p in parts]
            return os.path.join(*texts) if key == "path" else "".join(texts)
    raise Unsettled("not a value")
