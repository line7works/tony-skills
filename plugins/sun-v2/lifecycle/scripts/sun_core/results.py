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
        self.not_returned = {}            # a pairs field: [(index, key)] of the members whose value was not returned (G23-7)

    def safe(self):
        """What may be written of the result: the tool's own words and copies, and nothing held."""
        return dict((name, kept.safe) for name, kept in self.fields.items() if kept.safe is not None)

    def held(self, name):
        kept = self.fields.get(name)
        return kept.held if kept is not None else None


def place_of(field):
    """A field's declared place; `[]` is the top level, the whole answer (G19-12)."""
    place = field.get("place")
    return tuple(place) if isinstance(place, list) else (field.get("name"),)


def _members(node, path):
    """The values at a place that steps through a list (`"*"`): one per member, in order; None where a step is missing."""
    if not path:
        return [node]
    part, rest = path[0], path[1:]
    if part == "*":
        if not isinstance(node, list):
            return None
        out = []
        for item in node:
            found = _members(item, rest)
            if found is None:
                return None
            out += found
        return out
    if isinstance(node, dict) and part in node:
        return _members(node[part], rest)
    if isinstance(node, list) and isinstance(part, int) and 0 <= part < len(node):
        return _members(node[part], rest)
    return None


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
    def __init__(self, declaration, raw, register, hosting_env=False):
        self.decl = declaration
        # the builder of the one keep construction that saves a hosting environment's values (its `hosting_env` mark): RK19's
        # floor applies to its secret pair list and to no other (G22-3)
        self.hosting_env = hosting_env
        self.raw = raw
        self.register = register
        self.kind = None
        self.text = None
        self.doc = None
        self.found = None
        self.bad = False              # the result is `malformed`, whatever else stands in it
        self.salvaged = {}            # an answer that cannot be decoded whole: {place: (kind, start, end, value)}
        self._secrets_read = False
        self.protected_text = None    # a declaration's whole answer named protected text: in memory only (SEC-4, A147)
        self.secret_lists = {}        # a secret list field's members, kept, in memory only (G20-6; SEC-4 as A150 words it)
        self.not_returned = {}        # a pairs field's members with no value returned: [(index, key)] (G23-7)
        self._classify()

    def _secret_members(self):
        """The names of the top-level members that are declared secret fields' places, and no other."""
        out = set()
        for field in self._fields(True):
            path = list(place_of(field))
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
        if self.decl.get("answer") == "protected text":
            # SEC-4 (A147): a command whose declaration names its whole answer `protected text` is read whole as protected
            # content, in memory: no field is read from it, and nothing of it is kept here (G19-8)
            try:
                self.protected_text = raw.stdout.decode("utf-8")
            except UnicodeDecodeError:
                self.protected_text = None
            self.doc, self.found = {}, {}
            return
        try:
            self.text = raw.stdout.decode("utf-8")
            self.doc = json.loads(self.text) if self.text.strip() else {}
            self.found = jsonspan.spans(self.text) if self.text.strip() else {}
        except (UnicodeDecodeError, ValueError):
            self.doc, self.found, self.bad = None, None, True
            # an answer that cannot be decoded whole: a declared secret field whose place stands complete before the damage
            # is still read from that place (the reviewer's D8-M, check 3; the owner's pick, brief-27 item 3)
            self.salvaged = _before_the_damage(raw.stdout, self._secret_members())
        if not self.bad and not isinstance(self.doc, dict) and not any(place_of(f) == () for f in self.decl.get("fields") or []):
            self.bad = True                 # an answer that is no object, where no field's place is the whole answer

    def _fields(self, secret):
        return [f for f in self.decl.get("fields") or [] if (f.get("disposition") == "secret") == secret]

    def _place(self, field):
        path = place_of(field)
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
        path = place_of(field)
        if path not in self.salvaged:
            return None
        kind, start, end, node = self.salvaged[path]
        return kind, start, end, node, path

    def secrets(self):
        """Every secret field of the result, read before any other field (SEC-4, SEC-12)."""
        self._secrets_read = True
        out = []
        for field in self._fields(True):
            required = self.kind in (field.get("required_in") or [])
            if "*" in place_of(field):
                out.append(self._secret_list(field, required))
                continue
            at = self._place(field) if self.found is not None else self._salvaged_place(field)
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

    def _secret_list(self, field, required):
        """A secret list field (SEC-4 as A150 words it; G20-6): each member checked by the type's validator, and each entered
        in the register as a secret field's value is, as a component of the list's one value (for a list of key and text
        pairs, G19-29, each member's text is the secret). A list that fails is kept whole at the least length or over, the
        texts in it at that length or over its components, and makes the result `malformed`, as SEC-4 has a failing value."""
        members = _members(self.doc, list(place_of(field))) if isinstance(self.doc, (dict, list)) else None
        if members is None:
            if required:
                self.bad = True
            return SecretRead(field["name"], NO_VALUE)
        pairs = field.get("pairs") if isinstance(field.get("pairs"), dict) else None
        if pairs:
            members = self._returned(field, members, pairs)
            passed = members is not None and all(isinstance(m.get(pairs.get("value")), str) for m in members)
            members = members if members is not None else []
            texts = [m.get(pairs.get("value")) for m in members if isinstance(m, dict)]
        else:
            passed = all(_valid(field, m) for m in members)
            texts = list(members)
        raw = json.dumps(members, sort_keys=True, ensure_ascii=False)
        texts = [t if isinstance(t, str) else json.dumps(t) for t in texts if isinstance(t, (str, int, float)) and not isinstance(t, bool)]
        if passed:
            components = []
            for text in texts:
                if pairs and self.hosting_env and _count_bytes(text) < LEAST_LENGTH:
                    # RK19 (A153): a hosting environment's saved value under the least length makes no entry. "Apply RK19 only to
                    # saved hosting environment values; other valid secret-list members must enter the register regardless of
                    # their short length" (the reviewer's F3, G22-3)
                    continue
                for piece in (text, text.strip()):
                    if piece and piece not in components:
                        components.append(piece)
            self.secret_lists[field["name"]] = [[m[pairs["key"]], m[pairs["value"]]] for m in members] if pairs else list(members)
            return SecretRead(field["name"], "kept", raw, False, True, components)
        self.bad = True
        if _count_bytes(raw) < LEAST_LENGTH:
            return SecretRead(field["name"], DROPPED)
        components = [t for t in texts if _count_bytes(t) >= LEAST_LENGTH]
        return SecretRead(field["name"], "kept", raw, False, False, components)

    def _returned(self, field, members, pairs):
        """A pairs field's members whose value is returned (G23-7): a member with no value (absent, or null) is no pair, and is
        noted by its place and key for the keep to set apart or fail on. None where a member is no object or its key fails."""
        if not all(isinstance(m, dict) and _valid(field, m.get(pairs.get("key"))) for m in members):
            return None
        out, skipped = [], []
        for index, m in enumerate(members):
            if m.get(pairs.get("value")) is None:
                skipped.append((index, m[pairs["key"]]))
            else:
                out.append(m)
        if skipped:
            self.not_returned[field["name"]] = skipped
        return out

    def _definite(self, kind):
        definite = self.decl.get("definite") or {}
        if kind in (definite.get("success") or []):
            return "success"
        if kind in (definite.get("refusals") or []):
            return "refusal"
        return None

    def _where(self, field, plain):
        """J6c: a field whose place steps through one list (`"*"`) and carries a `where` filter with `one`. The filter's each
        condition names a declared field of this declaration, its key: an `equal` field whose place is read inside a member
        and whose value is settled from the row's literal or a parameter (`equals_value`, as `calls.call` settles it, a
        saved answer reaching it as a parameter). A member matches where each key's value equals that value; with
        `"holds": true`, where the key's value is a list one item of which equals it. Equality only, no pattern, no other
        operator. Exactly one member matching: (its value at the rest of the place,). None matching, or no list at the
        place: None (the field stands nowhere). More than one, or a filter the declaration does not let it apply: False, and
        the result is `malformed`, as GOV-1 has it: the tool never picks one of several."""
        place, where = list(place_of(field)), field.get("where")
        if field.get("one") is not True or place.count("*") != 1 or not isinstance(where, list) or not where:
            return False
        cut = place.index("*")
        found = _members(self.doc, place[:cut]) if isinstance(self.doc, (dict, list)) else None
        if found is None or found[0] is None:
            return None
        if not isinstance(found[0], list):
            return False
        by_name = dict((f.get("name"), f) for f in plain)
        conditions = []
        for c in where:
            key = by_name.get(c.get("field")) if isinstance(c, dict) else None
            if (key is None or key is field or set(c) - {"field", "holds"} or c.get("holds", True) is not True
                    or "*" in place_of(key) or key.get("disposition") != "equal"
                    or not isinstance(key.get("equals"), dict) or not set(key["equals"]) <= {"literal", "param"}
                    or not isinstance(key.get("equals_value"), (str, int, float, bool))):
                return False
            conditions.append((list(place_of(key)), key["equals_value"], c.get("holds") is True))

        def meets(item, path, want, holds):
            got = _members(item, path)
            if got is None or len(got) != 1:
                return False
            if holds:
                return isinstance(got[0], list) and any(x == want and type(x) is type(want) for x in got[0])
            return got[0] == want and type(got[0]) is type(want)
        matched = [item for item in found[0] if all(meets(item, p, w, h) for p, w, h in conditions)]
        if not matched:
            return None
        if len(matched) > 1:
            return False
        value = _members(matched[0], place[cut + 1:])
        if value is None or len(value) != 1 or value[0] is None:
            return None
        return (value[0],)

    def finish(self):
        """Every other field. Call after `secrets()` and after custody was taken of each kept one."""
        if not self._secrets_read:
            self.secrets()
        if self.kind == "timeout":
            return Result("timeout")
        if self.bad:
            return Result("malformed")
        fields = {}
        plain = self._fields(False)
        keys = set(c.get("field") for f in plain for c in (f.get("where") if isinstance(f.get("where"), list) else [])
                   if isinstance(c, dict))
        for field in plain:
            name = field["name"]
            if name in keys:
                continue                    # a `where` filter's key is read only through its filter (J6c)
            if "where" in field:
                picked = self._where(field, plain)
                if picked is False:
                    return Result("malformed")
                if picked is None:
                    if self.kind in (field.get("required_in") or []):
                        return Result("malformed")
                    continue
                at = (None, None, None, picked[0])
            elif "*" in place_of(field):
                # a held field holding a list: one value per member of a list in the answer, each by its type's validator,
                # and held whole (G19-25; the control room's item 8): no ground proves a list
                found = _members(self.doc, list(place_of(field)))
                if found is None:
                    if self.kind in (field.get("required_in") or []):
                        return Result("malformed")
                    continue
                pairs = field.get("pairs")
                if isinstance(pairs, dict):
                    # a held list of key and text pairs (G19-29): each member an object whose key passes the field's
                    # validator and whose value is any text; a member whose value is not returned is no pair (G23-7)
                    found = self._returned(field, found, pairs)
                    if found is None or not all(isinstance(v.get(pairs.get("value")), str) for v in found):
                        return Result("malformed")
                    found = [[v[pairs["key"]], v[pairs["value"]]] for v in found]
                elif field.get("lists") is True:
                    # a held list whose members are each a list of values (G23-6: a key's targets), each value by the validator
                    if not all(isinstance(v, list) and all(_valid(field, x) for x in v) for v in found):
                        return Result("malformed")
                elif not all(_valid(field, v) for v in found):
                    return Result("malformed")
                if field.get("disposition") != "held":
                    return Result("malformed")
                fields[name] = Kept("held", held=found)
                continue
            else:
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
        for name, members in self.secret_lists.items():
            fields[name] = Kept("secret", held=members)          # held in memory for the step that needs it (SEC-4, SEC-7)
        alternative = self.kind in (self.decl.get("alternatives") or [])
        result = Result(self.kind, fields, "refusal" if alternative else self._definite(self.kind), alternative)
        result.protected_text = self.protected_text
        result.not_returned = dict(self.not_returned)
        return result
