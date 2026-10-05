"""The load-bearing form of ship-v2 (ruling E15-11): v1's `SHIP:` block, rendered and parsed here, and only here.

    render(fields) -> the block's text;  parse(text) -> fields;  parse then render gives the bytes back
    result_line(condition) -> `STOPPED (condition N: <which>)`, v1's words for the four stops
    hook_label(armed) -> `armed` or `NOT armed (run unwrapped)`
    summon(station, slice, doc), summon_goal(slice, doc) -> the lines that name a station (CR-26)

v1's form, line for line (its Output section):

    SHIP: <slice> <dash> <doc path>
    Hook: armed | NOT armed (run unwrapped)
    Result: ALL CLEAR | STOPPED (condition N: <which>)
    Build: <COMPLETE | PARTIAL | STOPPED>  <dot>  Signoff: <verdict | not reached>  <dot>  Recheck: <result | not run |
    not reached>  <dot>  Card: <the slice's Status: line>  <dot>  Laps: <0 | 1 | 2>
    (blank)
    Bottom line: <2-3 sentences>
    (blank, then only when any)
    Fixed: <finding> <dot> <file:line> <dot> <one line>          one line per fixed finding
    Remains: <finding> <dot> <severity> <dot> <what is needed>   one line per open finding
    SKILL NOTE: <what and why>

`Fixed` and `Remains` are omitted when empty, `SKILL NOTE` when there is none. The middle line separates its five
fields with v1's double-spaced middle dot; the `Fixed` and `Remains` lines with a single-spaced one.

THE EM DASH. v1's first line carries an em dash (U+2014). It is this module's one constant `D`, written as an escape
and typed nowhere in this core's files: standing rule 10's one named exception (the E15 lane contract E15-11), stated
in `references/ship-contract.md` section 8.

THE STATION NAMES. Every line that names a station names the v2 station (A2 Q5, CR-26): `/build-v2`, `/signoff-v2`,
`/recheck-v2`, `/ship-v2`; `summon` refuses any other name. The name is a value of the form; the form's bytes
around it are v1's.
"""
import re

D = "\u2014"
M = "\u00b7"
SEP = " %s " % M
WIDE = "  %s  " % M
V2 = ("build-v2", "signoff-v2", "recheck-v2", "ship-v2")
CONDITIONS = {1: "the extra lap is exhausted without ALL CLEAR", 2: "a fix would change the spec",
              3: "build-v2 stopped mid-slice", 4: "a fix wants files outside the slice scope"}
ARMED, NOT_ARMED = "armed", "NOT armed (run unwrapped)"
MIDDLE = re.compile(r"^Build: (.+?)%sSignoff: (.+?)%sRecheck: (.+?)%sCard: (.+?)%sLaps: (\d+)$"
                    % ((re.escape(WIDE),) * 4))
FIRST = re.compile(r"^SHIP: (\S+) %s (.+)$" % D)


class FormError(ValueError):
    """A text that does not read as the form, or a value the form cannot carry."""


def one_line(value, what):
    if not isinstance(value, str) or "\n" in value or "\r" in value or not value.strip():
        raise FormError("%s is one non-blank line of text" % what)
    return value


def field(value, what):
    """A value inside a dotted line: one line, holding no middle dot."""
    one_line(value, what)
    if M in value:
        raise FormError("%s holds the line's separator %r" % (what, M))
    return value


def result_line(condition):
    return "STOPPED (condition %d: %s)" % (condition, CONDITIONS[condition])


def hook_label(armed):
    return ARMED if armed else NOT_ARMED


def summon(station, slice_name, doc):
    if station not in V2:
        raise FormError("%r is not a v2 station: every line ship-v2 renders names the v2 stations" % (station,))
    return "/%s %s %s" % (station, slice_name, doc)


def summon_goal(slice_name, doc):
    return "/goal %s" % summon("ship-v2", slice_name, doc)


def render(fields):
    lines = ["SHIP: %s %s %s" % (field(fields["slice"], "the slice"), D, one_line(fields["doc"], "the doc")),
             "Hook: %s" % one_line(fields["hook"], "the hook"),
             "Result: %s" % one_line(fields["result"], "the result"),
             "Build: %s%sSignoff: %s%sRecheck: %s%sCard: %s%sLaps: %d" % (
                 field(fields["build"], "build"), WIDE, field(fields["signoff"], "signoff"), WIDE,
                 field(fields["recheck"], "recheck"), WIDE, field(fields["card"], "the card"), WIDE,
                 int(fields["laps"])),
             "", "Bottom line: %s" % one_line(fields["bottom_line"], "the bottom line")]
    rows = ["Fixed: %s%s%s%s%s" % (field(f["finding"], "a fixed finding"), SEP, field(f["location"], "its location"),
                                   SEP, field(f["line"], "its line")) for f in fields.get("fixed") or []]
    rows += ["Remains: %s%s%s%s%s" % (field(r["finding"], "an open finding"), SEP, field(r["severity"], "its severity"),
                                      SEP, field(r["needed"], "what is needed")) for r in fields.get("remains") or []]
    if fields.get("skill_note"):
        rows.append("SKILL NOTE: %s" % one_line(fields["skill_note"], "the skill note"))
    if rows:
        lines += [""] + rows
    return "\n".join(lines) + "\n"


def parse(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) < 6 or lines[4] != "":
        raise FormError("the text is not a SHIP: block")
    first = FIRST.match(lines[0])
    middle = MIDDLE.match(lines[3])
    if first is None or middle is None or not lines[1].startswith("Hook: ") or not lines[2].startswith("Result: ") \
            or not lines[5].startswith("Bottom line: "):
        raise FormError("the text is not a SHIP: block")
    out = {"slice": first.group(1), "doc": first.group(2), "hook": lines[1][len("Hook: "):],
           "result": lines[2][len("Result: "):], "build": middle.group(1), "signoff": middle.group(2),
           "recheck": middle.group(3), "card": middle.group(4), "laps": int(middle.group(5)),
           "bottom_line": lines[5][len("Bottom line: "):], "fixed": [], "remains": [], "skill_note": None}
    rest = lines[6:]
    if rest:
        if rest[0] != "":
            raise FormError("the block's rows follow one blank line")
        for line in rest[1:]:
            if line.startswith("Fixed: "):
                parts = line[len("Fixed: "):].split(SEP)
                if len(parts) != 3:
                    raise FormError("a Fixed line holds three fields")
                out["fixed"].append({"finding": parts[0], "location": parts[1], "line": parts[2]})
            elif line.startswith("Remains: "):
                parts = line[len("Remains: "):].split(SEP)
                if len(parts) != 3:
                    raise FormError("a Remains line holds three fields")
                out["remains"].append({"finding": parts[0], "severity": parts[1], "needed": parts[2]})
            elif line.startswith("SKILL NOTE: "):
                out["skill_note"] = line[len("SKILL NOTE: "):]
            else:
                raise FormError("a line the SHIP: block does not hold: %r" % line)
    return out
