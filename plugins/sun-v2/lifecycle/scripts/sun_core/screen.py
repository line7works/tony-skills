"""What a line is passed against before it is written (the frame's SEC-12: the register, and the
values of the withheld read).

An entry holds a value whole, each component its source declares, and the percent-encoded and base64
forms of each. A text "holds" an entry when any of those forms stands in it. The frame sets no floor
on how short a value may be and still be held by a line (the contract's A33, A36), and none is set
here; the one thing left out is a value of no length, which no text can be said to hold.

`Screen` is the plain set of entries. The secret register of an invocation is a `Screen`; so is the
set of values the withheld read holds for printing only, and the set of values the disproof reads of
other runs gave. They are kept apart because the frame keeps them apart: a withheld-read value is no
entry of the register, and no check of a name or of an input sees it.
"""
import base64
import re
import urllib.parse

from . import texts


def forms_of(value):
    """The value whole, percent-encoded and in base64, as SEC-11 and SEC-12 name the forms."""
    if not value:
        return []
    out = [value]
    for quoted in (urllib.parse.quote(value, safe=""), urllib.parse.quote_plus(value, safe="")):
        out.append(quoted)
        out.append(re.sub(r"%[0-9A-F]{2}", lambda m: m.group(0).lower(), quoted))
    raw = value.encode("utf-8")
    for encode in (base64.b64encode, base64.urlsafe_b64encode):
        text = encode(raw).decode("ascii")
        out.append(text)
        out.append(text.rstrip("="))
    seen, unique = set(), []
    for item in out:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


class Entry(object):
    def __init__(self, value, components=(), ref=None, source=""):
        self.value = value
        self.components = [c for c in components if c]
        self.ref = ref          # the reference of its disproof record, where it has one (SEC-6)
        self.source = source    # a fixed word of the tool's: where the value came from
        forms = []
        for item in [value] + self.components:
            for form in forms_of(item):
                if form not in forms:
                    forms.append(form)
        self.forms = forms


class Screen(object):
    def __init__(self):
        self.entries = []

    def add(self, value, components=(), ref=None, source=""):
        if not isinstance(value, str) or not value:
            return None
        for entry in self.entries:
            if entry.value == value and entry.components == [c for c in components if c]:
                if ref and not entry.ref:
                    entry.ref = ref
                return entry
        entry = Entry(value, components, ref, source)
        self.entries.append(entry)
        return entry

    def extend(self, other):
        for entry in other.entries:
            self.add(entry.value, entry.components, entry.ref, entry.source)

    def hit(self, text):
        """The first entry a text holds, in any form; None where it holds none."""
        if not isinstance(text, str):
            return None
        for entry in self.entries:
            for form in entry.forms:
                if form in text:
                    return entry
        return None

    def holds(self, text):
        return self.hit(text) is not None

    def holds_any(self, texts_):
        return any(self.holds(t) for t in texts_)

    def words(self, entry=None):
        """The fixed words of withholding, with the reference of the disproof record where there is
        one; nothing at all where those words would themselves hold an entry."""
        text = texts.WITHHELD
        if entry is not None and entry.ref:
            text = "%s (record %s)" % (texts.WITHHELD, entry.ref)
        if self.holds(text):
            text = texts.WITHHELD
        return "" if self.holds(text) else text

    def redact(self, text):
        """`text` with the fixed words in the place of every value it holds (a form, the CLI's
        output and an error carry the words in the value's place; the form is still rendered)."""
        if not isinstance(text, str) or not self.entries:
            return text
        for _ in range(64):
            entry = self.hit(text)
            if entry is None:
                return text
            words = self.words(entry)
            longest = sorted((f for f in entry.forms if f in text), key=len, reverse=True)[0]
            text = text.replace(longest, words)
        return "" if self.holds(text) else text

    def line(self, text):
        """A line of fixed text before the startup checks pass: printed whole, or giving way whole
        to the fixed words of withholding (SEC-12, the withheld read)."""
        if not self.holds(text):
            return text
        return self.words()
