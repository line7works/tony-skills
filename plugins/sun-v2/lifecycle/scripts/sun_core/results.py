"""What a provider's result may carry (the frame's SEC-4; SEC-5).

A value a provider returns is held unless a ground proves it safe: A, a fixed word on the list its
declaration wrote before the run; B, equality with safe content the invocation already holds; C,
equality with a name in the owner's settings. No value is safe because of its shape, and no ground
proves a value that holds an entry of the register.

A field is read only from its declared place in the tool's structured answer; an undeclared field
is dropped; nothing a tool prints beyond that is kept. A declared field that fails its validator, a
required field that is missing, or a fixed field off its list, turns the whole result into kind
`malformed` with nothing kept, but for one thing: a secret. An exit the declaration does not list is a
fixed field off its list: the answer is still read for its secret fields' places (D8-U, A140).

`Parser.secrets()` is made first and reads only the secret fields, before any other field of the
result: each value at a secret field's place is `kept` (it passed its validator, or failed it and
is at the least length or over), is no value at all, or is a failing value under the least length
and dropped. The caller takes custody of each kept one (the register, the protected record, the
search, the disproof record, the receipt; SEC-12) before `Parser.finish()` reads anything else.
"""
import json
import re
import urllib.parse

from . import jsonspan

LEAST_LENGTH = 8                       # bytes; the owner's ruling A34, the number the frame's author wrote
KINDS = ("not-found", "auth", "conflict", "terms", "timeout", "malformed", "other")
TYPES = {                              # type -> the dispositions it may have (SEC-4's table)
    "exit": ("fixed",), "kind": ("fixed",), "state": ("fixed",), "flag": ("fixed",),
    "count": ("equal", "held"), "time": ("held",), "id": ("equal", "held", "secret"),
    "name": ("fixed", "equal", "held"), "hash": ("equal", "held"), "address": ("fixed", "equal", "held", "secret"),
}
DIFFERS = "differs from what the tool holds"       # the fixed fact an `equal` field keeps when it is not equal
NO_VALUE = "no such value"
DROPPED = "under the least length, dropped"
# the one receipt given with no result: a start the runner refused after the step record that a receipt is due, the file it
# found being gone as it started it, so that no child was started (SEC-12, A109, A110)
NO_CHILD = "no child started"


class Raw(object):
    """What the runner hands the parser: the exit status and standard output, or why there is none."""

    def __init__(self, exit_code, stdout, timed_out=False, oversize=False, killed=False):
        self.exit_code = exit_code
        self.stdout = stdout
        self.timed_out = timed_out
        self.oversize = oversize
        self.killed = killed


class Kept(object):
    """One declared field as the frame keeps it. `safe` is the tool's own word or copy where a
    ground proved the value; `held` is the value itself, in memory only, where none did."""

    def __init__(self, disposition, safe=None, held=None, equal=None):
        self.disposition = disposition
        self.safe = safe
        self.held = held
        self.equal = equal

    @property
    def is_held(self):
        return self.held is not None


class SecretRead(object):
    def __init__(self, name, outcome, raw=None, is_text=True, passed=False, components=()):
        self.name = name
        self.outcome = outcome            # "kept", NO_VALUE or DROPPED
        self.raw = raw                    # the value as it was read: the text itself, or the whole non-text value
        self.is_text = is_text
        self.passed = passed
        self.components = list(components)


class Result(object):
    def __init__(self, kind, fields=None, definite=None, alternative=False):
        self.kind = kind                  # "success", or one of the seven kinds
        self.fields = fields or {}
        self.definite = definite          # "success", "refusal", or None for an indefinite result
        self.alternative = alternative    # a definite refusal the declaration lists as an alternative result

    def safe(self):
        """What may be written of the result: the tool's own words and copies, and nothing held."""
        return dict((name, kept.safe) for name, kept in self.fields.items() if kept.safe is not None)

    def held(self, name):
        kept = self.fields.get(name)
        return kept.held if kept is not None else None


def _count_bytes(text):
    return len(text.strip().encode("utf-8"))


def _valid(field, value):
    """The field's own validator: it can refuse a value and never proves one."""
    kind = field.get("type")
    if kind == "kind":
        return value in KINDS
    if kind == "state":
        return isinstance(value, str) and value in (field.get("list") or [])
    if kind == "flag":
        return isinstance(value, bool)
    if kind == "count":
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0
    if kind in ("time", "hash"):
        return isinstance(value, str) and bool(field.get("form")) and re.match(field["form"], value) is not None
    if kind in ("id", "name"):
        if not isinstance(value, str) or not value or len(value) > int(field.get("max_length") or 0):
            return False
        # the whole value, to its last character: `$` would pass one line break at the end past any alphabet (the reviewer's
        # V1, check 3); `fullmatch` holds for every field the alphabet is applied to, whatever its disposition
        return re.fullmatch("[%s]+" % field.get("alphabet", ""), value) is not None if field.get("alphabet") else False
    if kind == "address":
        if not isinstance(value, str):
            return False
        try:
            parts = urllib.parse.urlsplit(value)
        except ValueError:
            return False
        return bool(parts.scheme and parts.netloc) and "@" not in parts.netloc and not parts.fragment
    return False


def _before_the_damage(stdout, names):
    """Where an answer cannot be decoded whole: each top-level member named in `names` (a declared secret field's own place)
    whose value is a complete JSON string standing before the damage, as {(name,): ("text", start, end, value)}.

    The answer is read as the decoder reads it: its bytes as UTF-8 up to the first that is not, then an object member by
    member, each member's name and value decoded whole, up to the first that cannot be, which is the damage; nothing past it
    is read. The text is never searched for a value-shaped string, and no member of another name is kept: a member of
    another name is decoded only to step past it. A member whose value the damage cuts off stands at no complete place. Where
    a name stands more than once, the last before the damage is the one, as the decoder keeps it."""
    try:
        text = stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        text = stdout[:exc.start].decode("utf-8")
    found = {}
    try:
        i = jsonspan._skip_ws(text, 0)
        if i >= len(text) or text[i] != "{":
            return found
        i += 1
        while True:
            i = jsonspan._skip_ws(text, i)
            key_end = jsonspan._string_end(text, i)
            key = json.loads(text[i:key_end])
            i = jsonspan._skip_ws(text, key_end)
            if i >= len(text) or text[i] != ":":
                return found
            start = jsonspan._skip_ws(text, i + 1)
            end = jsonspan._value_end(text, start)
            value = json.loads(text[start:end])          # the member's value decoded whole, or the damage is here
            if key in names:
                if isinstance(value, str) and text[start] == '"':
                    found[(key,)] = ("text", start, end, value)
                else:
                    found.pop((key,), None)
            i = jsonspan._skip_ws(text, end)
            if i < len(text) and text[i] == ",":
                i += 1
                continue
            return found
    except (ValueError, IndexError):
        return found


class Parser(object):
    def __init__(self, declaration, raw, register):
        self.decl = declaration
        self.raw = raw
        self.register = register
        self.kind = None
        self.text = None
        self.doc = None
        self.found = None
        self.bad = False              # the result is `malformed`, whatever else stands in it
        self.salvaged = {}            # an answer that cannot be decoded whole: {place: (kind, start, end, value)}
        self._secrets_read = False
        self._classify()

    def _secret_members(self):
        """The names of the top-level members that are declared secret fields' places, and no other."""
        out = set()
        for field in self._fields(True):
            path = list(field.get("place") or [field.get("name")])
            if len(path) == 1 and isinstance(path[0], str):
                out.add(path[0])
        return out

    def _classify(self):
        raw, decl = self.raw, self.decl
        if raw.timed_out:
            self.kind = "timeout"
            return
        if raw.killed or raw.exit_code is None or raw.oversize:
            self.kind, self.bad = "malformed", True
            return
        self.kind = (decl.get("exits") or {}).get(str(raw.exit_code))
        if self.kind is None or (self.kind != "success" and self.kind not in KINDS):
            # an exit the declaration does not list: the exit is a fixed field (SEC-4's type table) off its list, so the
            # whole result is `malformed` with nothing kept, "but for one thing: a secret. A value at a secret field's place
            # stays in the tool's custody whatever becomes of the rest of the result" (the reviewer's D8-U; A139, A140). The
            # structured answer is still read below, as it is beside an exit the declaration lists, and `secrets()` reads
            # its secret fields' places; `finish()` reads nothing else, the result being `malformed`
            self.kind, self.bad = "malformed", True
        try:
            self.text = raw.stdout.decode("utf-8")
            self.doc = json.loads(self.text) if self.text.strip() else {}
            self.found = jsonspan.spans(self.text) if self.text.strip() else {}
        except (UnicodeDecodeError, ValueError):
            self.doc, self.found, self.bad = None, None, True
            # an answer that cannot be decoded whole: a declared secret field whose place stands complete before the damage
            # is still read from that place (the reviewer's D8-M, check 3; the owner's pick, brief-27 item 3)
            self.salvaged = _before_the_damage(raw.stdout, self._secret_members())
        if not self.bad and not isinstance(self.doc, dict):
            self.bad = True

    def _fields(self, secret):
        return [f for f in self.decl.get("fields") or [] if (f.get("disposition") == "secret") == secret]

    def _place(self, field):
        path = tuple(field.get("place") or [field.get("name")])
        if self.found is None or path not in self.found:
            return None
        kind, start, end = self.found[path]
        node = self.doc
        for part in path:
            node = node[part]
        return kind, start, end, node, path

    def _salvaged_place(self, field):
        """A secret field's place in an answer that could not be decoded whole: read only where it stood complete before
        the damage (`_before_the_damage`); None where it did not, which gives the receipt as before."""
        path = tuple(field.get("place") or [field.get("name")])
        if path not in self.salvaged:
            return None
        kind, start, end, node = self.salvaged[path]
        return kind, start, end, node, path

    def secrets(self):
        """Every secret field of the result, read before any other field (SEC-4, SEC-12)."""
        self._secrets_read = True
        out = []
        for field in self._fields(True):
            at = self._place(field) if self.found is not None else self._salvaged_place(field)
            required = self.kind in (field.get("required_in") or [])
            if at is None or at[0] == "null":
                out.append(SecretRead(field["name"], NO_VALUE))
                if required:
                    self.bad = True
                continue
            kind, start, end, node, path = at
            is_text = kind == "text"
            raw = node if is_text else self.text[start:end]
            if _valid(field, node):
                components = [raw.strip()] if raw.strip() != raw else []
                if field.get("components") == "address" and is_text:
                    from . import channels
                    components += channels.address_components(raw)
                out.append(SecretRead(field["name"], "kept", raw, is_text, True, components))
                continue
            self.bad = True                                  # its own validator failed: malformed, kept or dropped
            if _count_bytes(raw) < LEAST_LENGTH:
                out.append(SecretRead(field["name"], DROPPED))
                continue
            components = [raw.strip()] if raw.strip() != raw else []
            if kind in ("list", "object"):
                for leaf_kind, leaf_start, leaf_end in jsonspan.leaves(self.found, path):
                    piece = self.text[leaf_start:leaf_end]
                    piece = json.loads(piece) if leaf_kind == "text" else piece
                    if _count_bytes(piece) >= LEAST_LENGTH and piece.strip() not in components:
                        components.append(piece)
                        if piece.strip() != piece:
                            components.append(piece.strip())
            out.append(SecretRead(field["name"], "kept", raw, is_text, False, components))
        return out

    def _definite(self, kind):
        definite = self.decl.get("definite") or {}
        if kind in (definite.get("success") or []):
            return "success"
        if kind in (definite.get("refusals") or []):
            return "refusal"
        return None

    def finish(self):
        """Every other field. Call after `secrets()` and after custody was taken of each kept one."""
        if not self._secrets_read:
            self.secrets()
        if self.kind == "timeout":
            return Result("timeout")
        if self.bad:
            return Result("malformed")
        fields = {}
        for field in self._fields(False):
            name = field["name"]
            at = self._place(field)
            if at is None or at[0] == "null":
                if self.kind in (field.get("required_in") or []):
                    return Result("malformed")
                continue
            value = at[3]
            if not _valid(field, value):
                return Result("malformed")
            disposition = field.get("disposition")
            shown = "true" if value is True else "false" if value is False else value
            caught = self.register.holds(shown) if isinstance(shown, str) else self.register.holds(str(shown))
            if disposition == "fixed":
                listed = field.get("list") if field.get("type") in ("state", "name", "address") else None
                if listed is not None and value not in listed:
                    return Result("malformed")
                if caught:
                    return Result("malformed")       # no ground proves it, and a fixed field has no other
                fields[name] = Kept("fixed", safe=shown)
            elif disposition == "equal":
                want = field.get("equals_value")
                wanted = want if isinstance(want, list) else [want]
                if not caught and any(value == w and type(value) is type(w) for w in wanted):
                    fields[name] = Kept("equal", safe=value, equal=True)
                else:
                    fields[name] = Kept("equal", safe=DIFFERS, held=value, equal=False)
            else:
                fields[name] = Kept("held", held=value)
        alternative = self.kind in (self.decl.get("alternatives") or [])
        return Result(self.kind, fields, "refusal" if alternative else self._definite(self.kind), alternative)
