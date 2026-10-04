"""The second reading's reader: the one module of vertical-v2 that imports the vendored CommonMark reader (the E15
lane contract A13; contract section 5, "Two readings", and section 15, "Runtime").

    tokens(text) -> the reader's token stream for the text (a byte order mark at its start dropped first, as the
        line reader drops it)
    headings(stream) -> [(level, name, line)]: every heading in document order, ATX and Setext alike, wherever it
        stands (a list item and a block quote included); `name` is its rendered text, `line` its first line (1-based)
    paragraph_lines(stream) -> [(line, text, exact)]: every rendered line of every paragraph, wherever it stands;
        `exact` is False when the paragraph's rendered lines cannot all be mapped to source lines (below)
    raw_lines(stream, headings_only=False) -> [(line, text)]: every heading's rendered name and (unless
        `headings_only`) every paragraph's rendered line, BEFORE whitespace runs are collapsed, with the line each
        carries above: the characters the reader renders, character references decoded (the E15 lane contract A16,
        the second reading's refusal (d), `readings.py`; the notes candidates, `readings.notes_unlisted`)
    identity() -> {"preset", "versions", "files", "python"}: what was loaded, for the vendored tree's test

The reader is `markdown-it-py` 3.0.0 with `mdurl` 0.1.2, unpacked unmodified under `scripts/vendor/` and pinned by
`vendor/VENDOR.json` (each wheel's sha256 and each file's, held by `tests/test_vendor.py`); nothing is installed and
nothing is fetched. It is loaded once, with `vendor/` first on `sys.path` for that import only (the path is restored
at once, whatever happens), with the optional `linkify_it` import blocked so no package from outside `vendor/` is
run, and it is refused (exit 1, a defect of the package) unless both modules come from `vendor/` at the pinned
versions. It parses with the `commonmark` preset: CommonMark only, raw HTML on, no table, no strikethrough, no
linkify, no typographic replacement.

RENDERED TEXT (A13). A heading's name and a paragraph's lines are taken from the inline tokens: text (character
references and backslash escapes already decoded by the reader) and code spans' text are kept; emphasis, strong
emphasis, links and images are markup and only their text is kept; an inline HTML token is removed; a soft or hard
line break ends a rendered line. Each rendered line then has its runs of whitespace collapsed to one space and is
trimmed (`str.split`, so a no-break space or any other Unicode space is a space too). A heading's lines are joined
into one name. A paragraph's rendered line carries the source line it starts on when the reader's line endings can
all be counted (the breaks and any line ending inside an inline HTML token); when one cannot (a code span, a link
destination or a link title running over a line ending), every line of that paragraph carries the paragraph's first
line and is marked not exact, so a reader never takes such a line's number as its own (the E15 lane contract A14,
C1A8-1: `readings.py` stops on a label line there). An inline token of a kind not named here is a defect of the
package (exit 1), never skipped.
"""
import os
import sys

from station_core import driver

VENDOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor")
PINS = {"markdown_it": "3.0.0", "mdurl": "0.1.2"}
PRESET = "commonmark"
BOM = "﻿"
TEXT = ("text", "text_special", "code_inline")
BREAKS = ("softbreak", "hardbreak")
MARKUP = ("em_open", "em_close", "strong_open", "strong_close", "link_open", "link_close")

_loaded = {}


def _load():
    """(the MarkdownIt instance, the two modules), loaded once from `vendor/` (module docstring)."""
    if _loaded:
        return _loaded["md"], _loaded["modules"]
    saved = list(sys.path)
    blocked = "linkify_it" not in sys.modules
    if blocked:
        sys.modules["linkify_it"] = None      # the reader's optional import fails, so nothing outside vendor/ runs
    sys.path.insert(0, VENDOR)
    try:
        import markdown_it
        import mdurl
    except ImportError as exc:
        raise driver.Defect("the vendored CommonMark reader under scripts/vendor/ did not import (%s): the package is "
                            "damaged; reinstall vertical-v2" % exc)
    finally:
        sys.path[:] = saved
        if blocked and "linkify_it" in sys.modules and sys.modules["linkify_it"] is None:
            del sys.modules["linkify_it"]
    modules = {"markdown_it": markdown_it, "mdurl": mdurl}
    home = os.path.realpath(VENDOR) + os.sep
    for name, module in sorted(modules.items()):
        where = os.path.realpath(getattr(module, "__file__", "") or "")
        if not where.startswith(home) or getattr(module, "__version__", None) != PINS[name]:
            raise driver.Defect("the CommonMark reader's module %s was not the vendored copy at version %s (it came "
                                "from %s, version %r): vertical-v2 reads only with the reader under scripts/vendor/"
                                % (name, PINS[name], where or "nowhere", getattr(module, "__version__", None)))
    _loaded["md"] = markdown_it.MarkdownIt(PRESET)
    _loaded["modules"] = modules
    return _loaded["md"], modules


def identity():
    md, modules = _load()
    return {"preset": PRESET, "versions": dict((n, m.__version__) for n, m in modules.items()),
            "files": dict((n, m.__file__) for n, m in modules.items()), "python": list(sys.version_info[:3])}


def tokens(text):
    md, modules = _load()
    return md.parse(text[1:] if text.startswith(BOM) else text)


def _collapse(text):
    return " ".join(text.split())


def _render(children):
    """([raw text of each rendered line], [line endings consumed before each rendered line], line endings counted)."""
    lines, starts, state = [""], [0], {"consumed": 0}

    def walk(kids):
        for kid in kids:
            if kid.type in BREAKS:
                state["consumed"] += 1
                lines.append("")
                starts.append(state["consumed"])
            elif kid.type in TEXT:
                lines[-1] += kid.content
            elif kid.type == "html_inline":
                state["consumed"] += kid.content.count("\n")
            elif kid.type == "image":
                walk(kid.children or [])
            elif kid.type in MARKUP:
                pass
            else:
                raise driver.Defect("the CommonMark reader produced an inline token vertical-v2 does not know (%r): "
                                    "the package is damaged; reinstall vertical-v2" % kid.type)

    walk(children or [])
    return lines, starts, state["consumed"]


def headings(stream):
    out = []
    for index, token in enumerate(stream):
        if token.type == "heading_open":
            lines, starts, consumed = _render(stream[index + 1].children)
            out.append((int(token.tag[1:]), _collapse(" ".join(lines)), token.map[0] + 1))
    return out


def paragraph_lines(stream):
    out = []
    for index, token in enumerate(stream):
        if token.type != "paragraph_open":
            continue
        first, after = token.map[0] + 1, token.map[1] + 1
        lines, starts, consumed = _render(stream[index + 1].children)
        exact = consumed == after - first - 1
        for text, start in zip(lines, starts):
            out.append((first + start if exact else first, _collapse(text), exact))
    return out


def raw_lines(stream, headings_only=False):
    out = []
    for index, token in enumerate(stream):
        if token.type == "heading_open":
            lines, starts, consumed = _render(stream[index + 1].children)
            out.append((token.map[0] + 1, " ".join(lines)))
        elif token.type == "paragraph_open" and not headings_only:
            first, after = token.map[0] + 1, token.map[1] + 1
            lines, starts, consumed = _render(stream[index + 1].children)
            exact = consumed == after - first - 1
            for text, start in zip(lines, starts):
                out.append((first + start if exact else first, text))
    return out
