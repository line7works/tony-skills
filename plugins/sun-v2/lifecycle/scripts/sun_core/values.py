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
    {"clock": "date"}               the run's date by the tool's own clock, settled at the look and frozen into the manifest
    {"account": "<provider>"}       the account that provider's identity read proved equal to a name in his settings
                                   (SEC-4's ground C), from the manifest's accounts
    {"each": "path"}                in a family row, a field of the found thing a member is made for (`plan.expand_family`)
    {"project_memory": V}           the harness's memory store of the project folder V, as the machine-facts module resolves it
                                   (E16-12; G21-10)
    {"table": {"name": T, "by": F}} the value the lane's own table T holds for the planning fact F the look settled (G21-1);
                                   with `"cut": "line"`, inside a text, where T holds no entry for F the line of the text
                                   that holds it is left out (G22-7c, rows-rise's "a line with no command cut")
    {"checked": {"value": V, "validator": W}}
                                   a value filled into a row's text, checked by the validator W: one that fails refuses the
                                   input in the look (G21-6); one the look cannot read yet is checked there by the output it
                                   names, and again when it is resolved
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
    "a launch agent's label": re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}"),
    "a date": re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}"),
    "a shortcut's name": re.compile(r"[a-z0-9]{2,5}"),           # rise's shortcut: 2 to 5 lowercase letters or digits (G20-3)
    "a shortcut name": re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}"),     # set's T11: a found alias's name (rows-set 8, item 1; G23-19)
    # rise's L24 (R8; G21-6): a folder a shell line holds between double quotes, with no `"`, `$`, backtick, backslash or line break
    "a path a shell line may hold": re.compile(r'[^"$`\\\r\n]{1,1024}'),
}


class Unsettled(Exception):
    """A value refers to an output that does not exist yet, or to nothing."""


class Refused(Exception):
    """A value filled into a row's text fails the validator it is checked by (G21-6): the input is refused in the look."""

    def __init__(self, validator):
        Exception.__init__(self, validator)
        self.validator = validator


def check(validator, text):
    """`text` where the validator passes it; raises Refused otherwise (G21-6)."""
    pattern = VALIDATORS.get(validator)
    if pattern is None or not isinstance(text, str) or pattern.fullmatch(text) is None:
        raise Refused(validator)
    return text


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
    if "each" in value:
        raise Unsettled("a field of a found thing, outside a family's member")
    if "clock" in value:
        if not getattr(look, "date", None):
            raise Unsettled("the run's date")
        return {"literal": look.date}
    if "account" in value:
        accounts = getattr(look, "accounts", None)
        if accounts is None:
            return dict(value)               # the identity reads come later in the look; settled then (`plan.build`)
        if value["account"] not in accounts:
            raise Unsettled("an account no identity read proved")
        return {"literal": accounts[value["account"]]}
    if "project_memory" in value and is_mark(value):
        folder = freeze(value["project_memory"], look)
        resolver = getattr(look, "project_memory", None)
        found = resolver(str(folder["literal"])) if resolver and isinstance(folder, dict) and "literal" in folder else None
        if not found:
            raise Unsettled("the memory store of a project folder")
        return {"literal": found}
    if "table" in value and is_mark(value):
        # G21-1: the lane's own table, by a planning fact the look settled; a fact the table holds no entry for is a value
        # the look cannot settle
        table = (getattr(look, "tables", None) or {}).get(value["table"]["name"])
        key = _dig(look.facts, value["table"]["by"])
        if not isinstance(table, dict) or str(key) not in table:
            raise Unsettled("a fact the lane's table holds no entry for")
        return freeze(table[str(key)], look)
    if "checked" in value and is_mark(value):
        inner = freeze(value["checked"]["value"], look)
        if isinstance(inner, dict) and "literal" in inner and len(inner) == 1:
            return {"literal": check(value["checked"]["validator"], inner["literal"])}
        return {"checked": {"value": inner, "validator": value["checked"]["validator"]}}
    if "local" in value:
        reader = getattr(look, "local", None)
        where = freeze(value["local"].get("path"), look)
        if reader is None or not isinstance(where, dict) or "literal" not in where:
            raise Unsettled("a file on this machine the look cannot read")
        return reader(str(where["literal"]), value["local"].get("validator"))
    for key in ("path", "text"):
        if key in value:
            if key == "text" and any(_cut(v, look) for v in value[key]):
                return _text_cut(value[key], look)
            parts = [freeze(v, look) for v in value[key]]
            if all(isinstance(p, dict) and "literal" in p for p in parts):
                texts = [str(p["literal"]) for p in parts]
                return {"literal": os.path.join(*texts) if key == "path" else "".join(texts)}
            return {key: parts}
    return dict((k, freeze(v, look)) for k, v in value.items())


def _cut(part, look):
    """Whether a part of a text is a table mark with the word `cut` whose table holds no entry for its fact (G22-7c)."""
    if not (is_mark(part) and "table" in part and part["table"].get("cut") == "line"):
        return False
    table = (getattr(look, "tables", None) or {}).get(part["table"]["name"])
    return not isinstance(table, dict) or str(_dig(look.facts, part["table"]["by"])) not in table


def _text_cut(parts, look):
    """A text with each line that holds a cut table mark left out, the line's own ending with it (G22-7c). The rest must
    settle to literals in the look, or the value is one the look cannot settle."""
    lines, line, cut = [], [], False
    for part in parts:
        if _cut(part, look):
            cut = True
            continue
        frozen = freeze(part, look)
        if not (isinstance(frozen, dict) and "literal" in frozen):
            raise Unsettled("a text with a line cut whose other parts the look cannot settle")
        pieces = str(frozen["literal"]).split("\n")
        for piece in pieces[:-1]:
            line.append(piece)
            if not cut:
                lines.append("".join(line) + "\n")
            line, cut = [], False
        line.append(pieces[-1])
    if line != [""] and line and not cut:
        lines.append("".join(line))
    return {"literal": "".join(lines)}


def is_mark(node):
    """Whether a node is one of the marks, by its one key and the shape of what it holds (a command's
    parameter may bear the same name as a mark's key)."""
    if not isinstance(node, dict) or len(node) != 1:
        return False
    key, held = list(node.items())[0]
    if key == "literal":
        return isinstance(held, (str, int, float, bool))
    if key in ("input", "location", "fact", "output", "account"):
        return isinstance(held, str)
    if key == "clock":
        return held == "date"
    if key == "each":
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
    if key == "project_memory":
        return isinstance(held, dict)
    if key == "table":
        return isinstance(held, dict) and set(held) in ({"name", "by"}, {"name", "by", "cut"})
    if key == "checked":
        return isinstance(held, dict) and set(held) == {"value", "validator"}
    if key == "read":
        # G23-5: a held field the row's own command read, made at the operation's time and going back to its issuer (SEC-2)
        return isinstance(held, dict) and set(held) == {"command", "field"}
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
        elif is_mark(node) and "checked" in node:
            out.append(node["checked"].get("validator"))
            out += validators_named(node["checked"].get("value"))
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
    """Every {"saved": n} mark of a reverse row replaced by {"record": records[n]}, or by the literal itself where records[n]
    is one: an input its forward row saved from safe content, which stays usable as text (SEC-1). Raises Unsettled where n
    names no record."""
    if isinstance(node, list):
        return [bind_saved(v, records) for v in node]
    if isinstance(node, dict):
        if is_mark(node) and "saved" in node:
            if node["saved"] >= len(records):
                raise Unsettled("a saved input the forward operation did not save")
            found = records[node["saved"]]
            return dict(found) if "literal" in found else {"record": found}
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
    if "read" in value and is_mark(value):
        raise Unsettled("a held field a command of the row reads when the operation runs")
    if "checked" in value and is_mark(value):
        found = resolve(value["checked"]["value"], outputs)
        try:
            return check(value["checked"]["validator"], found)
        except Refused:
            raise Unsettled("a value filled into a text fails its check")
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
