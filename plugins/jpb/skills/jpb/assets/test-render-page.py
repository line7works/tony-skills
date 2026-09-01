#!/usr/bin/env python3
"""Regression check for render-page.py against the PRD-length fixture.

The 2026-08-11 live run showed the renderer sectioning on every H2, so a
PRD-length brief exploded into one panel per brief heading. This asserts
the Step 11 contract: one Brief panel, one tab per box section, Judges and
Summary — nothing sectioned from inside the brief.

Usage: python3 assets/test-render-page.py   (from the repo root)
"""
import re, subprocess, sys, tempfile, os

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = os.path.join(root, "assets")
out = tempfile.NamedTemporaryFile(suffix=".html", delete=False).name
subprocess.run([sys.executable, os.path.join(a, "render-page.py"),
                os.path.join(a, "fixtures", "prd-run-fixture.md"),
                os.path.join(a, "jpb-page-template.html"),
                os.path.join(a, "jpb-vendor-styles.json"),
                os.path.join(a, "jpb-wordmark.png"), out], check=True)
page = open(out).read()
tabs = re.findall(r'<a href="#([^"]+)"[^>]*>([^<]*)</a>', page)
labels = [t[1] for t in tabs]

expected = ["Brief", "GPT", "Fable", "Gemini ✕", "Judges", "Summary"]
assert labels == expected, f"tab bar wrong: {labels} != {expected}"
assert page.count('id="brief"') == 1, "expected exactly one Brief panel"
assert page.count('<section class="panel"') + page.count('<section class="panel dropped"') == 6, "panel count wrong"
# brief-internal headings must be demoted, not sectioned
assert 'id="1-vision"' not in page and "Economy and pr" not in "".join(labels)
# fenced fake heading must not create anything
assert 'id="not-a-heading"' not in page
# fenced CONTRACT headings must not cut: the brief's fence quotes
# "## Reconciliation" and "## GPT box — ..." — all brief content through
# the economy section must stay inside the single Brief panel
brief_panel = re.search(r'<section class="panel" id="brief".*?</section>', page, re.S).group(0)
assert "Economy and pricing" in brief_panel, "brief content leaked out of the Brief panel (fence-blind cut)"
assert "not a heading" in brief_panel and "dangerous" in brief_panel
# cost table parses the run-doc em-dash format: label and value in separate cells
assert "<td>GPT</td><td>$0 — subscription</td>" in page, "cost row misparsed"
assert "<td>OpenRouter total</td><td>$0.032051</td>" in page, "cost total misparsed"
os.unlink(out)

# fermentation-era YAML cost format: `fable: "$0 — subscription"` must keep the
# quoted value whole, not split at its internal em dash
ferm = os.path.join(root, "docs", "jpb-fermentation-station-2026-08-09.md")
if os.path.exists(ferm):
    out2 = tempfile.NamedTemporaryFile(suffix=".html", delete=False).name
    subprocess.run([sys.executable, os.path.join(a, "render-page.py"), ferm,
                    os.path.join(a, "jpb-page-template.html"),
                    os.path.join(a, "jpb-vendor-styles.json"),
                    os.path.join(a, "jpb-wordmark.png"), out2], check=True)
    page2 = open(out2).read()
    assert "<td>Fable</td><td>$0 — subscription</td>" in page2, "YAML cost row misparsed"
    assert "<td>OpenRouter total</td><td>$0.00914</td>" in page2, "YAML cost total misparsed"
    assert 'fable: "$0' not in page2, "quoted YAML cost value split at em dash"
    os.unlink(out2)
print("render-page fixture check: PASS")
