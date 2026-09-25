"""A build doc's structure, its protected lines, and the in-place extension (contract section 8).

The form is `references/templates/build-doc.md`, read and rendered through `station_core/templates.py`
(E14-12); this module only locates what the lane needs in a doc that already exists:

    structure(text)          the header, the body cut at every `## ` heading (each slice with its
                             name, short name and `Status:` lines), the `Plan: inspected` lines, and
                             where the five ledger sections start; nothing inside a fence counts
    protected(text)          the lines a revision may never change: every slice's `Status:` lines
                             by slice, every `Plan: inspected` line in order, and every line from the
                             first ledger heading to the end, each byte for byte with its ending. A
                             `Status:` or `Plan: inspected` line is known by its label in any case
                             and at any indent (round 2, R4): a hand-typed `status: built` is
                             protected as `Status: built` is
    protected_changes(a, b)  every protected line of `a` that `b` would change, drop or add to
    slice_block(values, nl)  one slice section as `templates.render_build_doc` lays it out
    extend(text, ...)        the doc with new slices appended after the last slice (a slice of the
                             same name replaced where it lies), and the header's `Constraints:` and
                             `Out of scope:` items the answer adds; nothing else moves, and nothing
                             the answer carries is dropped: a `Constraints:` line is inserted after
                             `Intent:` when the doc has none, and an item counts as present only
                             when it equals an item already there, whole (`items_of`)

Every function takes and returns text; none writes a file. None judges what a doc says (E14-4).
"""
import re

from station_core import templates

LEDGER = templates.LEDGER_SECTIONS
SLICE = templates.BUILD["slice"]
STAMP = "Plan: inspected"
STATUS = "Status:"


def newline_of(text):
    first = text.find("\n")
    return "\r\n" if first > 0 and text[first - 1] == "\r" else "\n"


def _bare(line):
    return line.rstrip("\r\n")


def is_status(bare):
    """A `Status:` line, whatever its case or indent."""
    return bare.lstrip().casefold().startswith(STATUS.casefold())


def is_stamp(bare):
    """A `Plan: inspected` line, whatever its case or indent."""
    return bare.lstrip().casefold().startswith(STAMP.casefold())


def status_value(bare):
    return bare.lstrip()[len(STATUS):].strip()


def structure(text):
    """The doc cut into its header, its body chunks and its ledger tail.

    A body chunk runs from a `## ` heading to the next `## ` heading (or the ledger sections): a
    slice chunk when the heading reads `## Slice <name> <dash> <short name>`, any other chunk
    otherwise, kept as found. A line inside a ``` fence is never a heading, a slice or a ledger
    heading. The ledger tail starts at the first of the five ledger headings.
    """
    lines = text.splitlines(True)
    bare = [_bare(l) for l in lines]
    fenced = []
    inside = False
    for line in bare:
        if line.startswith("```"):
            fenced.append(True)
            inside = not inside
            continue
        fenced.append(inside)
    ledger_start = next((i for i, l in enumerate(bare) if l in LEDGER and not fenced[i]), None)
    body_end = len(lines) if ledger_start is None else ledger_start
    starts = [i for i in range(body_end) if bare[i].startswith("## ") and not fenced[i]]
    header_end = starts[0] if starts else body_end
    chunks, slices = [], []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else body_end
        match = SLICE.match(bare[start])
        chunk = {"start": start, "end": end, "slice": None}
        if match:
            statuses = [i for i in range(start, end) if is_status(bare[i]) and not fenced[i]]
            sl = {"name": match.group(1), "short": match.group(2), "start": start, "end": end,
                  "status_indexes": statuses,
                  "status_index": statuses[0] if statuses else None,
                  "status_line": bare[statuses[0]] if statuses else None,
                  "status": status_value(bare[statuses[0]]) if statuses else None}
            chunk["slice"] = sl["name"]
            slices.append(sl)
        chunks.append(chunk)
    stamps = [bare[i] for i in range(body_end) if is_stamp(bare[i])]
    return {"lines": lines, "bare": bare, "slices": slices, "chunks": chunks, "ledger_start": ledger_start,
            "header_end": header_end, "body_end": body_end, "stamps": stamps}


def protected(text):
    st = structure(text)
    return {"status": [(s["name"], [st["lines"][i] for i in s["status_indexes"]]) for s in st["slices"]],
            "stamps": [st["lines"][i] for i in range(st["body_end"]) if is_stamp(st["bare"][i])],
            "ledger": st["lines"][st["ledger_start"]:] if st["ledger_start"] is not None else []}


def protected_changes(before, after):
    """[{"line", "what"}]: each protected line of `before` that `after` would not keep byte for byte."""
    a, b = protected(before), protected(after)
    out = []
    after_status = {}
    for name, lines in b["status"]:
        after_status.setdefault(name, lines)
    for name, lines in a["status"]:
        if not lines:
            continue
        if name not in after_status:
            out.append({"line": _bare(lines[0]), "what": "slice %s and its Status line would be dropped" % name})
        elif after_status[name] != lines:
            shown = next((l for l in lines if l not in after_status[name]), lines[0])
            out.append({"line": _bare(shown), "what": "slice %s's Status lines would read %r" % (
                name, [_bare(l) for l in after_status[name]])})
    if a["stamps"] != b["stamps"]:
        for index in range(max(len(a["stamps"]), len(b["stamps"]))):
            old = a["stamps"][index] if index < len(a["stamps"]) else None
            new = b["stamps"][index] if index < len(b["stamps"]) else None
            if old != new:
                out.append({"line": _bare(old if old is not None else new),
                            "what": "a Plan: inspected line would be %s" % (
                                "dropped or changed" if old is not None else "added")})
                break
    if a["ledger"] != b["ledger"]:
        for index in range(max(len(a["ledger"]), len(b["ledger"]))):
            old = a["ledger"][index] if index < len(a["ledger"]) else None
            new = b["ledger"][index] if index < len(b["ledger"]) else None
            if old != new:
                shown = old if old is not None and _bare(old).strip() else new
                if shown is None or not _bare(shown).strip():
                    shown = old if old is not None else new
                out.append({"line": _bare(shown) or "(a blank line)",
                            "what": "a line under the five ledger sections would be %s" % (
                                "changed or dropped" if old is not None else "added")})
                break
    return out


def slice_values(sl, requirement_text, criterion_row):
    """The values `templates.render_build_doc` takes for one slice of the answer."""
    deps = sl.get("depends_on") or []
    return {"name": sl["name"], "short": sl["short"], "goal": sl["goal"],
            "requirements": [requirement_text[i] for i in sl["requirements"]],
            "criteria": [(criterion_row[i]["text"], criterion_row[i]["verify"].strip()) for i in sl["criteria"]],
            "footprint": ", ".join(sl["footprint"]), "not_in_slice": sl["not_in_slice"],
            "depends_on": ", ".join("Slice %s" % d for d in deps) if deps else "nothing",
            "status": "not started"}


def slice_block(values, nl="\n"):
    """One slice section, heading to its trailing blank line, laid out by the shared renderer."""
    rendered = templates.render_build_doc("x", "x", "x", "x", [], [values])
    lines = rendered.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("## Slice "))
    stop = lines.index(LEDGER[0])
    return [l + nl for l in lines[start:stop]]


def constraints_value(constraints, assumptions, open_questions):
    """The `Constraints:` value: the constraint lines, then `Assumed:` and `Open:` (contract section 8)."""
    parts = []
    if constraints:
        parts.append("; ".join(c.rstrip(".") for c in constraints))
    if assumptions:
        parts.append("Assumed: " + "; ".join(a.rstrip(".") for a in assumptions))
    if open_questions:
        parts.append("Open: " + "; ".join(q.rstrip(".") for q in open_questions))
    return ". ".join(parts) + "." if parts else ""


MARKERS = re.compile(r"(?:^|\. )(?:Assumed|Open): ")


def items_of(value):
    """The items a `Constraints:` value already holds, each whole: the value is cut at its
    `Assumed:` and `Open:` markers (the form `constraints_value` renders) and every part at `; `,
    each item stripped of its closing period. Nothing finer: an item is present only when it equals
    one of these whole, so a shorter text inside a longer item is still added (a repeat is the
    safe side; a drop never is)."""
    out = set()
    for part in MARKERS.split(value):
        for item in part.split("; "):
            item = item.strip().rstrip(".").strip()
            if item:
                out.add(item)
    return out


def _new_items(items, have):
    return [x for x in items if x.strip().rstrip(".").strip() not in have]


def _header_edit(lines, header_end, nl, constraints, assumptions, open_questions, out_of_scope):
    head = list(lines[:header_end])
    bare = [_bare(l) for l in head]
    ci = next((i for i, l in enumerate(bare) if l.startswith("Constraints:")), None)
    value = bare[ci][len("Constraints:"):].strip() if ci is not None else ""
    have = items_of(value)
    extra = constraints_value(_new_items(constraints, have), _new_items(assumptions, have),
                              _new_items(open_questions, have))
    if extra and ci is not None:
        joined = (value.rstrip(".") + ". " + extra) if value else extra
        head[ci] = "Constraints: " + joined + nl
    elif extra:
        # the doc has no Constraints: line: insert one after Intent: (or after the title), so
        # nothing the answer carries is dropped (round 2, R4)
        at = next((i + 1 for i, l in enumerate(bare) if l.startswith("Intent:")), None)
        if at is None:
            at = next((i + 1 for i, l in enumerate(bare) if l.startswith("# ")), 0)
        if at > 0 and not head[at - 1].endswith("\n"):
            head[at - 1] = head[at - 1] + nl
        head[at:at] = ["Constraints: " + extra + nl]
        bare[at:at] = ["Constraints: " + extra]
        ci = at
    oi = next((i for i, l in enumerate(bare) if l.startswith("Out of scope:")), None)
    if out_of_scope:
        if oi is None:
            at = (ci + 1) if ci is not None else len(head)
            head[at:at] = ["Out of scope:" + nl] + ["- %s%s" % (o, nl) for o in out_of_scope]
            return head
        inline = bare[oi][len("Out of scope:"):].strip()
        items = [inline] if inline else []
        end = oi + 1
        while end < len(head) and _bare(head[end]).startswith("- "):
            items.append(_bare(head[end])[2:].strip())
            end += 1
        new = [o for o in out_of_scope if o.strip() not in items]
        if new:
            if inline:
                block = ["Out of scope:" + nl, "- %s%s" % (inline, nl)] + list(head[oi + 1:end])
            else:
                block = list(head[oi:end])
            block += ["- %s%s" % (o, nl) for o in new]
            head[oi:end] = block
    return head


def extend(text, blocks, constraints=(), assumptions=(), open_questions=(), out_of_scope=()):
    """`text` with `blocks` ([(slice name, lines)]) placed and the header items added.

    A block whose slice already has a chunk replaces that chunk where it stands; any other block
    is appended after the last body chunk, before the ledger sections. Every other chunk, a
    heading the form does not know included, stays byte for byte.
    """
    nl = newline_of(text)
    st = structure(text)
    lines = st["lines"]
    head = _header_edit(lines, st["header_end"], nl, list(constraints), list(assumptions),
                        list(open_questions), list(out_of_scope))
    chunks = [(c["slice"], list(lines[c["start"]:c["end"]])) for c in st["chunks"]]
    tail = list(lines[st["body_end"]:])
    placed = set()
    for name, block in blocks:
        at = next((i for i, (n, _) in enumerate(chunks) if n == name), None)
        if at is not None:
            chunks[at] = (name, list(block))
        else:
            chunks.append((name, list(block)))
        placed.add(name)
    out = head
    for name, block in chunks:
        if name in placed and out and _bare(out[-1]).strip():
            # a blank line before a placed section, and only there: every other byte stays as found
            if not out[-1].endswith("\n"):
                out[-1] = out[-1] + nl
            out.append(nl)
        out.extend(block)
    if tail and chunks and chunks[-1][0] in placed and out and _bare(out[-1]).strip():
        out.append(nl)
    return "".join(out + tail)
