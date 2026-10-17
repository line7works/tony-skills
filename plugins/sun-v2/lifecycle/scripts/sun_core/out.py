"""The command line's one way out (the contract's E16-15; the frame's SEC-12, SEC-5).

Standard output carries one JSON document and nothing else; diagnostics go to standard error. Every
text in either is passed against what the invocation may not show: before the startup checks have
passed, the values of the withheld read (a line that holds one gives way whole to the fixed words);
after them, the register (the fixed words stand in the value's place). The whole document is then
passed once more as it will be written; where a value still stands in it, in a key or anywhere
else, less is written, down to nothing at all.
"""
import json

from . import exits, screen as screenmod, texts


def plugin_version():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    plugin = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    try:
        with open(os.path.join(plugin, ".claude-plugin", "plugin.json"), "rb") as fh:
            return json.loads(fh.read().decode("utf-8")).get("version") or "unknown"
    except (OSError, ValueError):
        return "unknown"


class Printer(object):
    def __init__(self, world, command):
        self.world = world
        self.command = command
        self.view = None                       # the withheld read's view, once it is made
        self.register = screenmod.Screen()     # the invocation's register (the same object the session holds)
        self.passed = False                    # the startup checks have passed

    # ---- what a text is passed against ----------------------------------------------------------
    def _screens(self):
        screens = [self.register]
        if not self.passed and self.view is not None:
            screens.append(self.view.values)
        return screens

    def _holds(self, text):
        return any(s.holds(text) for s in self._screens())

    def text(self, value):
        """One text as it may be written."""
        if not isinstance(value, str):
            return value
        if not self.passed:
            for screen in self._screens():
                if screen.holds(value):
                    words = screen.words()
                    return "" if self._holds(words) else words
            return value
        out = self.register.redact(value)
        return "" if self._holds(out) else out

    def _walk(self, node):
        if isinstance(node, str):
            return self.text(node)
        if isinstance(node, list):
            return [self._walk(item) for item in node]
        if isinstance(node, dict):
            return dict((key, self._walk(value)) for key, value in node.items())
        return node

    def envelope(self, **fields):
        doc = {"interface_version": texts.INTERFACE_VERSION, "plugin_version": plugin_version(), "tool": texts.TOOL,
               "command": self.command}
        doc.update(fields)
        return doc

    def emit(self, code, **fields):
        """Write the one document and return the exit code."""
        doc = self._walk(self.envelope(exit=code, **fields))
        if "lines" in doc:
            doc["lines"] = [line for line in doc["lines"] if line]
        words = self.text(texts.WITHHELD)
        ladder = [doc, {"interface_version": texts.INTERFACE_VERSION, "lines": [words] if words else []}, {}]
        for candidate in ladder:
            rendered = json.dumps(candidate, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            if not self._holds(rendered):
                self.world.output.out(rendered)
                return code
        return code

    def document(self, doc):
        """A whole document of the tool's own (identity, the examples' check), passed like every line."""
        doc = self._walk(doc)
        words = self.text(texts.WITHHELD)
        for candidate in (doc, {"interface_version": texts.INTERFACE_VERSION, "lines": [words] if words else []}, {}):
            rendered = json.dumps(candidate, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            if not self._holds(rendered):
                self.world.output.out(rendered)
                return

    def error(self, line):
        """One diagnostic line on standard error, passed like every other line."""
        line = self.text(line)
        if line and not self._holds(line + "\n"):
            self.world.output.err(line + "\n")

    def exception(self, exc, operation=None):
        """An exception is reported as its type and the operation; its message is never printed (SEC-5)."""
        where = " in operation %s" % operation if operation else ""
        self.error(texts.DEFECT + type(exc).__name__ + where)
        return exits.GENERAL
