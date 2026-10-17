"""Where a value stands in a JSON text, as the answer writes it (the frame's SEC-4: the least length
is counted on what the tool read at the field's place in the tool's structured answer).

`span_at(text, path)` gives the (start, end) of the value at a path of keys and indexes, or None
where nothing stands there. `leaves(text, start, end)` gives every text and every number that
stands in a value, at any depth, each as (kind, start, end); the names of an object's fields are
not among them.
"""
import json

_WS = " \t\r\n"


class Bad(ValueError):
    pass


def _skip_ws(text, i):
    while i < len(text) and text[i] in _WS:
        i += 1
    return i


def _string_end(text, i):
    if text[i] != '"':
        raise Bad()
    i += 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == '"':
            return i + 1
        i += 1
    raise Bad()


def _value_end(text, i, visit=None, path=()):
    """The index just past the value starting at `i`; calls visit(path, kind, start, end) for each value."""
    i = _skip_ws(text, i)
    if i >= len(text):
        raise Bad()
    start, ch = i, text[i]
    if ch == '"':
        end, kind = _string_end(text, i), "text"
    elif ch == "{":
        kind = "object"
        i = _skip_ws(text, i + 1)
        if i < len(text) and text[i] == "}":
            end = i + 1
        else:
            while True:
                i = _skip_ws(text, i)
                key_end = _string_end(text, i)
                key = json.loads(text[i:key_end])
                i = _skip_ws(text, key_end)
                if i >= len(text) or text[i] != ":":
                    raise Bad()
                i = _value_end(text, i + 1, visit, path + (key,))
                i = _skip_ws(text, i)
                if i < len(text) and text[i] == ",":
                    i += 1
                    continue
                if i < len(text) and text[i] == "}":
                    end = i + 1
                    break
                raise Bad()
    elif ch == "[":
        kind = "list"
        i = _skip_ws(text, i + 1)
        if i < len(text) and text[i] == "]":
            end = i + 1
        else:
            index = 0
            while True:
                i = _value_end(text, i, visit, path + (index,))
                index += 1
                i = _skip_ws(text, i)
                if i < len(text) and text[i] == ",":
                    i += 1
                    continue
                if i < len(text) and text[i] == "]":
                    end = i + 1
                    break
                raise Bad()
    else:
        end = i
        while end < len(text) and text[end] not in _WS + ",]}":
            end += 1
        word = text[i:end]
        if word in ("true", "false"):
            kind = "truth"
        elif word == "null":
            kind = "null"
        else:
            try:
                float(word)
            except ValueError:
                raise Bad()
            kind = "number"
    if visit is not None:
        visit(path, kind, start, end)
    return end


def spans(text):
    """{path: (kind, start, end)} for every value of a JSON text; raises Bad where it does not parse."""
    found = {}
    end = _value_end(text, 0, lambda path, kind, start, stop: found.__setitem__(path, (kind, start, stop)))
    if _skip_ws(text, end) != len(text):
        raise Bad()
    return found


def leaves(found, path):
    """Every text and number standing in the value at `path`, at any depth: [(kind, start, end)]."""
    out = []
    for other, (kind, start, end) in found.items():
        if len(other) > len(path) and other[:len(path)] == tuple(path) and kind in ("text", "number"):
            out.append((kind, start, end))
    return sorted(out, key=lambda item: item[1])
