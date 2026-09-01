#!/usr/bin/env python3
"""Render a JPB run doc to the arcade page per SKILL.md Step 11.
Usage: render_jpb.py <doc.md> <template.html> <styles.json> <wordmark.png> <out.html>
"""
import base64, html, json, re, sys

doc_path, tpl_path, styles_path, wordmark_path, out_path = sys.argv[1:6]
title_override = sys.argv[6] if len(sys.argv) > 6 else None
raw = open(doc_path).read()
tpl = open(tpl_path).read()
styles = json.load(open(styles_path))

# --- frontmatter ---
m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", raw, re.S)
fm_text, body = m.group(1), m.group(2)
def fm_get(key):
    m2 = re.search(rf"^{key}:\s*(.*)$", fm_text, re.M)
    return m2.group(1).strip() if m2 else ""
status = fm_get("status")
run_date = fm_get("run_date")
# cost block: lines indented under "cost:"
cost_lines = []
cm = re.search(r"^cost:\n((?:[ \t]+.*\n?)+)", fm_text, re.M)
COST_LABELS = {"deepseek": "DeepSeek", "grok": "Grok", "openrouter_total": "OpenRouter total", "fable": "Fable", "opus": "Opus", "gpt": "GPT", "gemini": "Gemini", "note": "Note"}
if cm:
    for ln in cm.group(1).strip().splitlines():
        ln = re.sub(r"^\s*-\s*", "", ln.strip())
        # Two committed conventions. YAML "key: value" (fermentation-era, value may
        # itself contain an em dash inside quotes) is checked FIRST — the em-dash
        # split on "- <Label> — <cost>" (asteroid-era) would otherwise cut a quoted
        # value like `fable: "$0 — subscription"` at the wrong place.
        km = re.match(r"^(\w+):\s*(.+)$", ln)
        m3 = re.match(r"^(.+?) — (.+)$", ln)
        if km:
            kk = km.group(1)
            cost_lines.append((COST_LABELS.get(kk, kk), km.group(2).strip().strip('"')))
        elif m3:
            cost_lines.append((m3.group(1).strip(), m3.group(2).strip().strip('"')))
        else:
            cost_lines.append((ln.strip().strip('"'), ""))

# --- split body into top-level sections ---
# Only contract headings are cut points. A PRD-length brief (and a box)
# carries its own H2s; those belong to the enclosing section and are
# demoted by md_block, never sectioned (Step 11 contract: ONE Brief panel).
JUDGE_PREFIXES = ("## Judge K tally", "## Judge G tally", "## Reconciliation", "## Debate card")
VENDOR_RE = re.compile(r"^## (GPT|Fable|Opus|Gemini|DeepSeek|Grok) box — (.+)$")
DROPPED_RE = re.compile(r"^## Dropped — (\w+) \((.+)\)$")
BRIEF_RE = re.compile(r"^## (The )?scrubbed brief\s*$", re.I)

def is_cut(ln):
    return bool(BRIEF_RE.match(ln) or VENDOR_RE.match(ln) or DROPPED_RE.match(ln)
                or ln.startswith(JUDGE_PREFIXES) or ln.startswith("## Verdicts"))

lines = body.splitlines()
# Fence-aware: a contract heading inside a fenced code block is content
# (a brief's code sample, a verbatim box quoting JPB headings), never a cut.
cuts, in_fence = [], False
for i, ln in enumerate(lines):
    if re.match(r"^\s*(```|~~~)", ln):
        in_fence = not in_fence
    elif not in_fence and is_cut(ln):
        cuts.append(i)
cuts.append(len(lines))
sections = []
for a, b in zip(cuts, cuts[1:]):
    sections.append((lines[a], "\n".join(lines[a+1:b]).strip()))

# --- minimal markdown -> html ---
def md_inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s

def md_block(text):
    out, i, L = [], 0, text.splitlines()
    while i < len(L):
        ln = L[i]
        if not ln.strip():
            i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(L) and L[i].startswith("|"):
                raw_row = L[i].strip().strip("|")
                prot = re.sub(r"`[^`]*`", lambda m: m.group(0).replace("|", "\x00"), raw_row)
                rows.append([c.replace("\x00", "|").strip() for c in prot.split("|")]); i += 1
            out.append('<div class="tablewrap"><table>')
            hdr = rows[0]
            out.append("<tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in hdr) + "</tr>")
            for r in rows[1:]:
                if all(re.fullmatch(r"[-: ]*", c) for c in r): continue
                out.append("<tr>" + "".join((f'<td class="ct">{md_inline(c)}</td>' if re.fullmatch(r"(\d/6.{0,30}|unclustered|both|[KG] only|—|-|\d+)", c) else f"<td>{md_inline(c)}</td>") for c in r) + "</tr>")
            out.append("</table></div>")
            continue
        m2 = re.match(r"^(#{1,4}) (.+)$", ln)
        if m2:
            lvl = max(3, min(len(m2.group(1)) + 1, 4))  # demote under page h2, floor h3
            out.append(f"<h{lvl}>{md_inline(m2.group(2))}</h{lvl}>")
            i += 1; continue
        if re.match(r"^\s*(\d+\.|-) ", ln):
            ordered = bool(re.match(r"^\s*\d+\.", ln))
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(L) and (re.match(r"^\s*(\d+\.|-) ", L[i]) or (L[i].startswith("   ") and items)):
                if re.match(r"^\s*(\d+\.|-) ", L[i]):
                    items.append(re.sub(r"^\s*(\d+\.|-) ", "", L[i]))
                else:
                    items[-1] += " " + L[i].strip()
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{md_inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        para = [ln]
        i += 1
        while i < len(L) and L[i].strip() and not re.match(r"^(\||#|\s*(\d+\.|-) )", L[i]):
            para.append(L[i]); i += 1
        out.append(f"<p>{md_inline(' '.join(para))}</p>")
    return "\n".join(out)

# --- build panels + tabs ---
def sty(key):
    v = styles[key] if key in styles else styles["vendors"][key]
    return f'style="--accent:{v["accent"]};--tint:{v["tint"]}"', v

panels, tabs = [], []
judge_bits, summary_bits, verdict_bits = [], [], []
for heading, content in sections:
    vm, dm = VENDOR_RE.match(heading), DROPPED_RE.match(heading)
    if BRIEF_RE.match(heading):
        s, v = sty("brief")
        panels.append(f'<section class="panel" id="brief" {s}><span class="badge">BRIEF</span>'
                      f"<h2>Scrubbed brief</h2>{md_block(content)}</section>")
        tabs.append(("brief", "Brief", styles["brief"]["accent"]))
    elif vm:
        vendor, model = vm.group(1), vm.group(2)
        s, v = sty(vendor)
        panels.append(f'<section class="panel" id="box-{vendor.lower()}" {s}>'
                      f'<span class="badge">{v["badge"]}</span><h2>{vendor} box</h2>'
                      f'<p class="modelid">{html.escape(model)}</p>{md_block(content)}</section>')
        tabs.append((f"box-{vendor.lower()}", vendor, v["accent"]))
    elif dm:
        vendor, model = dm.group(1), dm.group(2)
        s, v = sty("dropped") if False else (f'style="--accent:{styles["dropped"]["accent"]};--tint:{styles["dropped"]["tint"]}"', styles["dropped"])
        panels.append(f'<section class="panel dropped" id="box-{vendor.lower()}" {s}>'
                      f'<span class="badge">DROPPED</span><h2>{vendor} box — dropped</h2>'
                      f'<p class="modelid">{html.escape(model)}</p><div class="dropreason">{md_block(content)}</div></section>')
        tabs.append((f"box-{vendor.lower()}", f"{vendor} ✕", styles["dropped"]["accent"]))
    elif heading.startswith(("## Judge K tally", "## Judge G tally")):
        judge_bits.append((md_inline(heading[3:]), md_block(content)))
    elif heading.startswith(("## Reconciliation", "## Debate card")):
        summary_bits.append(f"<h3>{md_inline(heading[3:])}</h3>" + md_block(content))
    elif heading.startswith("## Verdicts"):
        verdict_bits.append(f"<h3>{md_inline(heading[3:])}</h3>" + md_block(content))
    else:
        st, v = sty("summary")
        oid = re.sub(r"[^a-z0-9]+", "-", heading[3:].lower()).strip("-") or "other"
        panels.append(f'<section class="panel" id="{oid}" {st}><span class="badge">OTHER</span>'
                      f"<h2>{md_inline(heading[3:])}</h2>{md_block(content)}</section>")
        tabs.append((oid, heading[3:][:18], styles["summary"]["accent"]))

def collapse_clusters(html_text):
    parts = re.split(r"(?=<h4>)", html_text)
    out = [parts[0]]
    for part in parts[1:]:
        m3 = re.match(r"<h4>(.*?)</h4>(.*)", part, re.S)
        if m3:
            out.append(f'<details class="cluster" open><summary>{m3.group(1)}</summary>{m3.group(2)}</details>')
        else:
            out.append(part)
    return "".join(out)

if judge_bits:
    s, v = sty("judges")
    panels.append(f'<section class="panel" id="judges" {s}><span class="badge">JUDGES</span>'
                  f"<h2>Judge tallies</h2>" + ''.join(f'<h3>{h}</h3>{collapse_clusters(c)}' for h, c in judge_bits) + "</section>")
    tabs.append(("judges", "Judges", styles["judges"]["accent"]))
if summary_bits or cost_lines:
    s, v = sty("summary")
    cost_html = ""
    if cost_lines:
        notes = [val for k, val in cost_lines if k == "Note"]
        rows_c = [(k, val) for k, val in cost_lines if k != "Note"]
        cost_html = ('<h3>Cost actuals</h3><div class="tablewrap"><table><tr><th>Box</th><th>Cost</th></tr>'
                     + "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(val)}</td></tr>" for k, val in rows_c)
                     + "</table></div>"
                     + "".join(f'<p class="modelid">{html.escape(n)}</p>' for n in notes))
    panels.append(f'<section class="panel" id="summary" {s}><span class="badge">SUMMARY</span>'
                  f"<h2>Reconciliation &amp; debate</h2>{''.join(summary_bits)}{cost_html}</section>")
    tabs.append(("summary", "Summary", styles["summary"]["accent"]))
if verdict_bits:
    s, v = sty("verdicts")
    panels.append(f'<section class="panel" id="verdicts" {s}><span class="badge">VERDICTS</span>'
                  f"<h2>Verdicts</h2>{''.join(verdict_bits)}</section>")
    tabs.append(("verdicts", "Verdicts", styles["verdicts"]["accent"]))

tab_html = "\n  ".join(f'<a href="#{tid}" style="--tab-accent:{acc}">{label}</a>' for tid, label, acc in tabs)

# --- title from filename slug ---
slug = re.sub(r"\.md$", "", doc_path.split("/")[-1])
title_words = re.sub(r"^jpb-", "", re.sub(r"-\d{4}-\d{2}-\d{2}(-\d+)?$", "", slug))
title = title_override or " ".join(w.capitalize() for w in title_words.split("-"))

wm = base64.b64encode(open(wordmark_path, "rb").read()).decode()
page = (tpl.replace("{{TITLE}}", html.escape(title))
        .replace("{{RUN_DATE}}", html.escape(run_date))
        .replace("{{STATUS_LINE}}", " · resolved" if status == "closed" else "")
        .replace("{{WORDMARK_IMG}}", f'<img class="wordmark" alt="JPB" src="data:image/png;base64,{wm}">')
        .replace("{{TABS}}", tab_html)
        .replace("{{SECTIONS}}", "\n".join(panels)))
open(out_path, "w").write(page)
print(f"rendered {out_path}: {len(page)} bytes, {len(tabs)} tabs, status={status}")
