"""The visual (ruling E14-6, the local half): plain HTML rendered from the doc's own content.

`render(doc_text)` reads the architecture doc (never the answer): its title, the walkthrough
target, the v0 drawing (components, data flow, diagram), the poured-concrete doors and the
deferred list, each line that is not struck through. The page is a body only, `<title>` first (the
page contract of the harness's artifact tool), every value escaped, no style, no script, no
link, no image and no external resource. The design stays plain; it evolves run by run in the
doc's hands, never in this file's.
"""
import html

from . import docs

LABELS = ("Components:", "Data flow:", "Diagram:")


def _esc(value):
    return html.escape(value, quote=True)


def _live(lines):
    return [l for l in lines if l.strip() and not l.startswith("~~") and not l.startswith("- ~~")]


def parts(doc_text):
    title, header, sections = docs.split(doc_text)
    out = {"title": title[-1][2:] if title and title[-1].startswith("# ") else title[-1], "who": None,
           "drawing": {}, "poured": [], "deferred": []}
    for heading, body in sections:
        live = _live(body)
        if heading == docs.WALK:
            out["who"] = next((l for l in live if l.startswith("Who:")), None)
        elif heading == docs.DRAWING:
            for label in LABELS:
                line = next((l for l in live if l.startswith(label)), None)
                if line is not None:
                    out["drawing"][label[:-1]] = line[len(label):].strip()
        elif heading == docs.POURED:
            out["poured"] = [l[2:] for l in live if l.startswith("- ")]
        elif heading == docs.DEFERRED:
            out["deferred"] = [l[2:] for l in live if l.startswith("- ")]
    return out


def render(doc_text):
    p = parts(doc_text)
    rows = ["<title>%s</title>" % _esc(p["title"]), "<h1>%s</h1>" % _esc(p["title"]),
            "<h2>Walkthrough target</h2>", "<p>%s</p>" % _esc(p["who"] or "")]
    rows.append("<h2>v0 drawing</h2>")
    components = p["drawing"].get("Components", "")
    rows.append("<h3>Components</h3>")
    rows.append("<ul>%s</ul>" % "".join("<li>%s</li>" % _esc(c) for c in components.split("; ") if c.strip()))
    rows.append("<h3>Data flow</h3>")
    rows.append("<p>%s</p>" % _esc(p["drawing"].get("Data flow", "")))
    rows.append("<h3>Diagram</h3>")
    rows.append("<pre>%s</pre>" % _esc(p["drawing"].get("Diagram", "")))
    rows.append("<h2>Poured concrete (one-way doors)</h2>")
    rows.append("<ul>%s</ul>" % "".join("<li>%s</li>" % _esc(x) for x in p["poured"]))
    rows.append("<h2>Deferred</h2>")
    rows.append("<ul>%s</ul>" % "".join("<li>%s</li>" % _esc(x) for x in p["deferred"]))
    return "\n".join(rows) + "\n"
