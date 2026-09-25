"""The scope doc's ledger reader (rulings E14-10 and E14-11).

    read(text) -> [{"id", "tag", "section", "text", "source", "reason", "line", "raw"}, ...]

Reads the four ledger sections of a scope doc (the form in `references/templates/scope-doc.md`):

- `Decisions:` lines, each `- <text> \u2014 decided (<source>)`, `- <text> \u2014 assumed (<why>)`, or
  `- <text> \u2014 parked: <needs research | needs prototype | waiting on <x>>`; the tag is
  `decided`, `assumed` or `parked`, `source` the parenthesis or the parked reason in full, and
  `reason` the parked reason's kind (`needs research`, `needs prototype`, `waiting on`);
- `Out of scope:` items (tag `out-of-scope`), `Research:` items (tag `research`) and `Open:` items
  (tag `open`), each written inline after its label or as `- ` lines under it.

A label with nothing after it holds no item. `Intent:` and `Next:` are not ledger sections.

Every line carries a stable id: a prefix for its section and twelve hex digits of the SHA-256 of
the item's text (for a Decisions line, the text before its tag), with `-2`, `-3` appended to a
repeated text in the same section. The id follows the item, not its position and not its tag: a
line added above it, or the same item moved from `parked` to `decided`, keeps its id. That is
what lets a later station pass a decided line forward by id (E14-11).

A line in a ledger section that the reader cannot tag is refused, quoted with its line number,
never dropped and never guessed: `LedgerRefused` lists every such line at once. A document with no
`Decisions:` label is refused the same way.
"""
import hashlib
import re

D = "\u2014"
LABELS = (("Decisions:", "Decisions"), ("Out of scope:", "Out of scope"), ("Research:", "Research"),
          ("Open:", "Open"))
OTHER_LABELS = ("Intent:", "Next:")
PREFIX = {"Decisions": "dec", "Out of scope": "oos", "Research": "res", "Open": "open"}
TAG_OF_SECTION = {"Out of scope": "out-of-scope", "Research": "research", "Open": "open"}
DECIDED = re.compile(r"^- (?P<text>.+?) %s (?P<tag>decided|assumed) \((?P<detail>.*)\)$" % D)
PARKED = re.compile(r"^- (?P<text>.+?) %s parked: (?P<detail>.+)$" % D)
TAGS = ("decided", "assumed", "parked", "out-of-scope", "research", "open")


class LedgerRefused(ValueError):
    """Lines the reader cannot tag. `lines` is [{"line", "raw", "why"}]."""

    def __init__(self, lines):
        self.lines = list(lines)
        ValueError.__init__(self, "the ledger holds %d line(s) it cannot tag: %s" % (
            len(self.lines), "; ".join("line %d %r (%s)" % (row["line"], row["raw"], row["why"])
                                       for row in self.lines)))


def _decision(raw):
    """(text, tag, source, reason) for one Decisions line, or a why-not string."""
    match = DECIDED.match(raw)
    # the tag is the LAST dash-separated tag on the line: a text may itself hold the dash
    last = raw.rfind(" %s " % D)
    if match and raw.rfind(" %s %s (" % (D, match.group("tag"))) == last:
        detail = match.group("detail")
        if not detail.strip():
            return "a %s line with an empty %s" % (match.group("tag"),
                                                  "source" if match.group("tag") == "decided" else "why")
        return match.group("text"), match.group("tag"), detail, None
    match = PARKED.match(raw)
    if match and raw.rfind(" %s parked: " % D) == last:
        detail = match.group("detail")
        if detail in ("needs research", "needs prototype"):
            return match.group("text"), "parked", detail, detail
        if detail.startswith("waiting on ") and detail[len("waiting on "):].strip():
            return match.group("text"), "parked", detail, "waiting on"
        return "a parked line whose reason is none of: needs research, needs prototype, waiting on <x>"
    if not raw.startswith("- "):
        return "not a list line ('- ...')"
    return "no tag: a Decisions line ends in ' %s decided (<source>)', ' %s assumed (<why>)' or ' %s parked: <reason>'" % (D, D, D)


def _id(section, text, seen):
    digest = hashlib.sha256(("%s\0%s" % (section, text.strip())).encode("utf-8")).hexdigest()[:12]
    base = "%s-%s" % (PREFIX[section], digest)
    seen[base] = seen.get(base, 0) + 1
    return base if seen[base] == 1 else "%s-%d" % (base, seen[base])


def read(text):
    lines = [raw.rstrip("\r\n") for raw in text.splitlines(True)]
    section = None
    out, refused, seen = [], [], {}
    found_decisions = False
    for number, raw in enumerate(lines, 1):
        label = next(((lab, name) for lab, name in LABELS if raw.startswith(lab)), None)
        if label:
            section = label[1]
            found_decisions = found_decisions or section == "Decisions"
            rest = raw[len(label[0]):].strip()
            if rest and section != "Decisions":
                out.append(_item(section, rest, number, raw, seen))
            elif rest:
                refused.append({"line": number, "raw": raw, "why": "a Decisions item goes on its own '- ' line"})
            continue
        if any(raw.startswith(lab) for lab in OTHER_LABELS) or raw.startswith("#"):
            section = None
            continue
        if section is None or not raw.strip():
            continue
        if section == "Decisions":
            got = _decision(raw)
            if isinstance(got, str):
                refused.append({"line": number, "raw": raw, "why": got})
                continue
            text_, tag, source, reason = got
            out.append({"id": _id(section, text_, seen), "tag": tag, "section": section, "text": text_,
                        "source": source, "reason": reason, "line": number, "raw": raw})
            continue
        if raw.startswith("- ") and raw[2:].strip():
            out.append(_item(section, raw[2:].strip(), number, raw, seen))
        else:
            refused.append({"line": number, "raw": raw, "why": "an item under %s is a '- ' line" % section})
    if not found_decisions:
        refused.append({"line": 1, "raw": "", "why": "the document has no 'Decisions:' label"})
    if refused:
        raise LedgerRefused(refused)
    return out


def _item(section, text, number, raw, seen):
    return {"id": _id(section, text, seen), "tag": TAG_OF_SECTION[section], "section": section,
            "text": text, "source": None, "reason": None, "line": number, "raw": raw}


def counts(lines):
    """{tag: n} for every tag of the ledger, zero included."""
    out = dict((tag, 0) for tag in TAGS)
    for row in lines:
        out[row["tag"]] += 1
    return out


def by_id(lines):
    return dict((row["id"], row) for row in lines)
