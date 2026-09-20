"""Finding identity (records E12 contract section 7).

A finding ID is `f1:` followed by the first 20 hex characters of the SHA-256 of the canonical
JSON of `[ledger_doc, slice, location_key, claim_key]`:

- `slice` is the canonical slice name, or `"none"`;
- `location_key` is `location.raw` with backticks removed, a glued parenthetical tag removed
  (E8-22: the tag is not part of the join key), internal whitespace collapsed, and case kept;
- `claim_key` is the claim with parentheses that wrap the whole field removed (E8-A28) and
  internal whitespace collapsed; with no claim it is the scenario the same way; with neither it
  is the empty string.

The ID is computed once, when the finding is raised, and stored in the event; nothing
recomputes it from a later record. The prefix is the version: a future scheme is `f2:` and both
can sit in one log, so `looks_like_id` accepts any `f<n>:` prefix while `finding_id` mints `f1:`
only.

`strip_parens` is the pilot's (`recheck_core/ledger.py`, `main` at
fc3945adfbbd793c5782c5be130a07aceadb1982), so the wrapping-parenthesis rule is the same one the
pilot's join key uses.

The tag rule has its own pattern here rather than the pilot's `ledger.LOCATION_RE`. The pilot's
pattern knows `file:line` and no line range, so it leaves a tag glued to a range
(`src/a.py:10-20 (wave 2)`, family L6 of section 11.1, which is "one location followed by a
parenthetical tag, with backticks or a range") inside the key, and a finding raised that way
would never join to a recheck line naming `src/a.py:10-20`. `TAGGED_LOCATION_RE` therefore
removes a tag glued to `file:N` or to `file:N-N` (hyphen or en dash, and the range text itself
stays in the key exactly as written). The pilot's own pattern is untouched and stays the strict
reader's in slice 2 (ruling E12-2).

The tag rule applies only to a field that names one location. A field naming several (family L4:
`,`, `;`, ` and `, ` + `) keeps its text whole, trailing parenthetical included, because nothing
there says which of the locations the parenthetical belongs to.
"""
import re

from . import canon

ID_PREFIX = "f1:"
ID_HEX = 20
ID_RE = re.compile(r"^f[1-9][0-9]*:[0-9a-f]{20}$")
NO_CLAIM = "()"  # the pilot's sentinel for a legacy entry without a claim (E8-22)
# one location, `file:N` or `file:N-N`, with a parenthetical tag glued to its end (E8-22, L6)
TAGGED_LOCATION_RE = re.compile(r"^(?P<loc>.+?:\d+(?:\s*[-–]\s*\d+)?)\s*\((?P<tag>[^()]*)\)$")
# the separators that make a location field name more than one location (section 11.3, L4)
MULTI_LOCATION_RE = re.compile(r"[,;]|\sand\s|\s\+\s")


def collapse(text):
    """Internal whitespace collapsed to single spaces, ends trimmed; case kept.

    A value that is not a string has no key of its own: the schema refuses it a moment later, and
    this returns the empty string rather than raising on the way there.
    """
    return " ".join(text.split()) if isinstance(text, str) else ""


def strip_parens(field):
    """Parentheses wrapping the whole field are not part of it; `()` is no field at all."""
    f = field.strip() if isinstance(field, str) else ""
    if f == NO_CLAIM:
        return None
    if len(f) >= 2 and f.startswith("(") and f.endswith(")"):
        return f[1:-1]
    return f


def location_key(location):
    """Section 7's location key, from a location object or a raw string.

    A parenthetical is dropped only when it is glued to one `file:N` or `file:N-N` location,
    which is what the pilot calls a legacy tag (E8-22). A parenthesis inside an unresolved
    location (`resolved` false: a file, a section, a described place) is part of the text and is
    kept, and so is one at the end of a field naming several locations.
    """
    raw = location.get("raw") if isinstance(location, dict) else location
    text = collapse(raw.replace("`", "") if isinstance(raw, str) else "")
    m = TAGGED_LOCATION_RE.match(text)
    if m is not None and not MULTI_LOCATION_RE.search(m.group("loc")):
        return m.group("loc").strip()
    return text


def claim_key(claim, scenario=None):
    """Section 7's claim key: the claim, else the scenario, else the empty string."""
    for field in (claim, scenario):
        if not isinstance(field, str):
            continue
        text = strip_parens(field)
        if text is None or not text.strip():
            continue
        return collapse(text)
    return ""


def identity_tuple(ledger_doc, slice_name, location, claim, scenario=None):
    """The four values hashed, in order, for a reader that wants to see them."""
    return [ledger_doc, slice_name or "none", location_key(location), claim_key(claim, scenario)]


def finding_id(ledger_doc, slice_name, location, claim, scenario=None):
    """The `f1:` finding ID of section 7."""
    key = identity_tuple(ledger_doc, slice_name, location, claim, scenario)
    return ID_PREFIX + canon.sha256_hex(canon.canonical_json(key))[:ID_HEX]


def id_of_event(event):
    """The finding ID an event of kind `finding_raised` or `defect_raised` computes to."""
    return finding_id(event.get("ledger_doc"), event.get("slice"), event.get("location"),
                      event.get("claim"), event.get("scenario"))


def looks_like_id(value):
    return isinstance(value, str) and ID_RE.match(value) is not None
