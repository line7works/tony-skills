#!/usr/bin/env python3
"""The deterministic check runner for the recheck-v2 E7 evals (lane contract section 8).

    uvx --with jsonschema python3 run-checks.py [--out DIR] [--lane NAME ...] [--json]

Standard library plus jsonschema. The generators and the unit tests run as subprocesses under
/usr/bin/python3 (3.9.6, the contract's runtime) when it exists. Git runs only inside the
throwaway repositories the generators create under --out.

Steps (each PASS or FAIL; exit 0 only when every step passes):

1. Build every lane twice into the SAME --out path (ruling E7-1); compare each case's
   tree_sha256 between the two builds and the manifests.
2. Validate every input.json against input.schema.json; the verdict must equal the manifest's
   input_validates; for invalid cases the key's invalid_fields must each match a validator
   error path (ruling E7-7: equal, or the error's path is a parent of it).
3. Tell scan over every workspace: the banned strings of section 3 as whole words or phrases,
   case-insensitive (ruling E7-5), minus each case's tells_allowed as exact strings.
4. Key shape: every key file parses; every case exists in a manifest and every manifest case
   has a key entry; every requirement id is R1 to R43; every top-level key of expected is a
   property of result.schema.json; every match form is one of section 5.9's; _coverage present;
   runs_at is E7, E9, or E10, or a list of those (ruling E7-11).
5. Coverage: merged from every key's _coverage; every requirement R1 to R43 has a case (R22 may
   point at E9; R27 is served by the trigger set); every section 16 check code has a case (D1 at
   E9, T1 by the trigger set). Writes answer-key/coverage.json and coverage.md when every lane
   is selected; both print every runs_at value of every case (ruling E7-11).
6. Identity now: for every key entry with deterministic_now.identity_matches_pin, compute the
   workspace identity with fixturelib.identity_of and compare with input.json's pin.
7. Checkpoint now: for every key entry with deterministic_now.checkpoint, run the section 11
   integrity check (ported from references/examples/validate-examples.py, plus the carried
   item 11 predecessor link) and compare the verdict class (valid, tolerated, corrupt).
8. test_fixturelib.py and test_match.py pass.
9. Every build.py answers --help with exit 0, --list, an unknown --case with exit 2, and runs
   from a different working directory.

--json prints one object {"steps": [{step, name, pass, detail, failures: [{lane, case, side,
detail}]}]} where side is fixture, key, runner, or contract.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EVALS = os.path.dirname(HERE)
FIXTURES = os.path.join(EVALS, "fixtures")
LIB_DIR = os.path.join(FIXTURES, "_lib")
KEY_DIR = os.path.join(EVALS, "answer-key")
TRIGGER = os.path.join(EVALS, "trigger-set", "requests.json")
REFS = os.path.join(os.path.dirname(EVALS), "skills", "recheck-v2", "references")
GEN_PYTHON = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable

sys.path.insert(0, HERE)
sys.path.insert(0, LIB_DIR)
from match import validate_form  # noqa: E402
import fixturelib  # noqa: E402

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.stderr.write("jsonschema is required: run as  uvx --with jsonschema python3 run-checks.py\n")
    sys.exit(2)

TELLS = ["answer key", "expected", "planted", "not_fixed", "missed_case", "verification_blocked",
         "missing_evidence", "should report", "the verifier should", "this case tests"]
REQUIREMENTS = ["R%d" % i for i in range(1, 44)]
CHECK_CODES = ["F1", "F2", "F3", "F4", "F5", "F6", "S1", "S2", "S3", "S4", "I1", "I2", "I3", "I4", "I5",
               "A1", "A2", "A3", "V1", "V2", "V3", "V4", "X1", "X2", "C1", "C2", "C3", "C4", "C5",
               "W1", "W2", "W3", "W4", "U1", "M1", "D1", "T1"]
E9_ONLY = {"R22": "D1", "D1": "R22"}      # delivery fixture: adapter-only, E9
TRIGGER_SERVED = {"R27": "T1", "T1": "R27"}  # trigger set (A6a), not a fixture case
RUNS_AT = ("E7", "E9", "E10")


def runs_at_values(value):
    """Ruling E7-11: runs_at is one of RUNS_AT or a list of them. Returns the list of values in
    RUNS_AT order, or None when the value has any other shape."""
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or not values:
        return None
    if any(v not in RUNS_AT for v in values) or len(set(values)) != len(values):
        return None
    return [v for v in RUNS_AT if v in values]


class Step:
    def __init__(self, number, name):
        self.step = number
        self.name = name
        self.failures = []
        self.notes = []

    def fail(self, lane, case, side, detail):
        self.failures.append({"lane": lane, "case": case, "side": side, "detail": detail})

    def report(self, detail):
        return {"step": self.step, "name": self.name, "pass": not self.failures,
                "detail": detail + ("" if not self.notes else "; " + "; ".join(self.notes)),
                "failures": self.failures}


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run(cmd, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def lanes_available():
    return sorted(d for d in os.listdir(FIXTURES)
                  if os.path.isdir(os.path.join(FIXTURES, d)) and not d.startswith("_")
                  and os.path.exists(os.path.join(FIXTURES, d, "build.py")))


def case_dirs(out, lane):
    lane_out = os.path.join(out, lane)
    if not os.path.isdir(lane_out):
        return []
    return sorted(os.path.join(lane_out, c) for c in os.listdir(lane_out)
                  if os.path.isfile(os.path.join(lane_out, c, "manifest.json")))


# ---- step 1: build twice into the same path ------------------------------------------------

def step1(out, lanes):
    st = Step(1, "build twice, determinism")
    summaries = {}
    for lane in lanes:
        build = os.path.join(FIXTURES, lane, "build.py")
        lane_out = os.path.join(out, lane)
        rounds = []
        for n in (1, 2):
            code, so, se = run([GEN_PYTHON, build, "--out", lane_out, "--json"])
            if code != 0:
                st.fail(lane, None, "fixture", "build %d exited %d: %s" % (n, code, se.strip()[-300:]))
                break
            try:
                summary = json.loads(so)
            except ValueError:
                st.fail(lane, None, "fixture", "build %d printed non-JSON on stdout with --json" % n)
                break
            if se.strip():
                st.notes.append("%s build %d wrote to stderr: %s" % (lane, n, se.strip()[:120]))
            manifests = {}
            for row in summary.get("cases", []):
                mp = os.path.join(row["path"], "manifest.json")
                if not os.path.exists(mp):
                    st.fail(lane, row["case"], "fixture", "build %d: no manifest.json at %s" % (n, row["path"]))
                    continue
                manifests[row["case"]] = read_json(mp)
                if manifests[row["case"]]["tree_sha256"] != row["tree_sha256"]:
                    st.fail(lane, row["case"], "fixture", "build %d: --json tree_sha256 differs from manifest.json" % n)
            rounds.append((summary, manifests))
        if len(rounds) == 2:
            (s1, m1), (s2, m2) = rounds
            ids1 = [r["case"] for r in s1["cases"]]
            ids2 = [r["case"] for r in s2["cases"]]
            if ids1 != ids2:
                st.fail(lane, None, "fixture", "case list differs between builds: %s vs %s" % (ids1, ids2))
            for cid in ids1:
                if cid not in m1 or cid not in m2:
                    continue
                if m1[cid]["tree_sha256"] != m2[cid]["tree_sha256"]:
                    st.fail(lane, cid, "fixture", "tree_sha256 differs between two builds into the same path: %s vs %s"
                            % (m1[cid]["tree_sha256"][:12], m2[cid]["tree_sha256"][:12]))
                elif m1[cid] != m2[cid]:
                    diff = sorted(k for k in set(m1[cid]) | set(m2[cid]) if m1[cid].get(k) != m2[cid].get(k))
                    st.fail(lane, cid, "fixture", "manifest differs between builds in %s" % diff)
                if m1[cid].get("case") != cid or m1[cid].get("lane") != lane:
                    st.fail(lane, cid, "fixture", "manifest case/lane (%r/%r) do not name the case dir and lane"
                            % (m1[cid].get("case"), m1[cid].get("lane")))
            summaries[lane] = s2
    n_cases = sum(len(s["cases"]) for s in summaries.values())
    return st.report("%d lanes built twice into %s, %d cases compared" % (len(summaries), out, n_cases)), summaries


# ---- keys ----------------------------------------------------------------------------------

def load_keys(lanes):
    """Return (entries_by_case, coverage_by_lane, problems) for the selected lanes."""
    entries, coverage, problems = {}, {}, []
    for lane in lanes:
        path = os.path.join(KEY_DIR, lane + ".json")
        if not os.path.exists(path):
            problems.append((lane, None, "key", "answer-key/%s.json is missing" % lane))
            continue
        try:
            doc = read_json(path)
        except ValueError as exc:
            problems.append((lane, None, "key", "answer-key/%s.json does not parse: %s" % (lane, exc)))
            continue
        if not isinstance(doc, list):
            problems.append((lane, None, "key", "answer-key/%s.json is not a JSON array" % lane))
            continue
        for e in doc:
            if not isinstance(e, dict) or "case" not in e:
                problems.append((lane, None, "key", "an entry without a case id"))
                continue
            if e["case"] == "_coverage":
                coverage[lane] = e
                continue
            if e["case"] in entries:
                problems.append((lane, e["case"], "key", "duplicate key entry"))
            e["_lane_file"] = lane
            entries[e["case"]] = e
        if lane not in coverage:
            problems.append((lane, None, "key", "no _coverage element"))
        elif doc[-1].get("case") != "_coverage":
            problems.append((lane, None, "key", "_coverage is not the last element"))
    return entries, coverage, problems


# ---- step 2: input validation ------------------------------------------------------------------

def error_paths(errors):
    """JSON paths of validator errors, as (path, exact_only) pairs.

    A 'required' or 'additionalProperties' error is reported by jsonschema at the parent; the
    property it names is appended to the path and that path matches exactly only, so a
    root-level missing property cannot match every field through the parent rule.
    """
    paths = []
    for err in errors:
        base = ""
        for part in err.absolute_path:
            base = "%s[%d]" % (base, part) if isinstance(part, int) else ("%s.%s" % (base, part) if base else part)
        names = []
        if err.validator == "required":
            names = re.findall(r"'([^']+)' is a required property", err.message)
        elif err.validator == "additionalProperties":
            names = re.findall(r"'([^']+)'", err.message)
        if names:
            for name in names:
                paths.append((("%s.%s" % (base, name)) if base else name, True))
        else:
            paths.append((base, False))
    return paths


def field_matches(field, paths):
    """Ruling E7-7: equal, or the error's path is a parent of the field."""
    for p, exact_only in paths:
        if p == field:
            return True
        if exact_only:
            continue
        if p == "" or field.startswith(p + ".") or field.startswith(p + "["):
            return True
    return False


def step2(out, lanes, entries):
    st = Step(2, "input.json validates per manifest and key")
    validator = Draft202012Validator(read_json(os.path.join(REFS, "input.schema.json")))
    n = 0
    for lane in lanes:
        for cdir in case_dirs(out, lane):
            m = read_json(os.path.join(cdir, "manifest.json"))
            cid = m["case"]
            ipath = os.path.join(cdir, m.get("input", "input.json"))
            if not os.path.exists(ipath):
                st.fail(lane, cid, "fixture", "input.json missing")
                continue
            try:
                doc = read_json(ipath)
            except ValueError as exc:
                st.fail(lane, cid, "fixture", "input.json does not parse: %s" % exc)
                continue
            n += 1
            errors = list(validator.iter_errors(doc))
            valid = not errors
            if valid != bool(m.get("input_validates")):
                st.fail(lane, cid, "fixture", "validator says %s but manifest input_validates is %s%s"
                        % (valid, m.get("input_validates"),
                           "" if valid else ": " + "; ".join(e.message[:80] for e in errors[:3])))
            key = entries.get(cid)
            if key is None:
                continue
            if "input_validates" in key and bool(key["input_validates"]) != valid:
                st.fail(lane, cid, "key", "key input_validates is %s but the validator says %s" % (key["input_validates"], valid))
            dn = key.get("deterministic_now") or {}
            if "input_validates" in dn and bool(dn["input_validates"]) != valid:
                st.fail(lane, cid, "key", "deterministic_now.input_validates is %s but the validator says %s" % (dn["input_validates"], valid))
            if not valid:
                fields = dn.get("invalid_fields")
                if not fields:
                    st.fail(lane, cid, "key", "invalid input but the key names no invalid_fields")
                else:
                    paths = error_paths(errors)
                    for f in fields:
                        if not field_matches(f, paths):
                            st.fail(lane, cid, "key", "invalid_fields entry %r matches no validator error path %s" % (f, sorted({p for p, _ in paths})))
    return st.report("%d inputs validated" % n)


# ---- step 3: tell scan --------------------------------------------------------------------------

def step3(out, lanes):
    st = Step(3, "tell scan over every workspace")
    patterns = [(t, re.compile(r"(?<![A-Za-z0-9_])" + re.escape(t) + r"(?![A-Za-z0-9_])", re.IGNORECASE)) for t in TELLS]
    files = 0
    for lane in lanes:
        for cdir in case_dirs(out, lane):
            m = read_json(os.path.join(cdir, "manifest.json"))
            cid = m["case"]
            allowed = [a for a in m.get("tells_allowed", []) if a]
            ws = os.path.join(cdir, m.get("workspace", "workspace"))
            for root, dirs, names in os.walk(ws):
                dirs[:] = sorted(d for d in dirs if d != ".git")
                for name in sorted(names):
                    if name == ".git":
                        continue
                    full = os.path.join(root, name)
                    if os.path.islink(full):
                        continue
                    with open(full, "rb") as fh:
                        raw = fh.read()
                    try:
                        text = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        continue  # binary content
                    files += 1
                    scrubbed = text
                    for a in allowed:
                        scrubbed = scrubbed.replace(a, " ")
                    for tell, pat in patterns:
                        hit = pat.search(scrubbed)
                        if hit:
                            line = scrubbed.count("\n", 0, hit.start()) + 1
                            st.fail(lane, cid, "fixture", "%s:%d contains the tell %r: %r"
                                    % (os.path.relpath(full, ws), line, tell,
                                       scrubbed[max(0, hit.start() - 30):hit.end() + 30]))
    return st.report("%d text files scanned for %d banned strings (whole words, case-insensitive)" % (files, len(TELLS)))


# ---- step 4: key shape ---------------------------------------------------------------------------

def step4(out, lanes, entries, coverage, problems):
    st = Step(4, "answer-key shape")
    for lane, cid, side, detail in problems:
        st.fail(lane, cid, side, detail)
    result_props = set(read_json(os.path.join(REFS, "result.schema.json"))["properties"])
    manifest_cases = {}
    for lane in lanes:
        for cdir in case_dirs(out, lane):
            m = read_json(os.path.join(cdir, "manifest.json"))
            manifest_cases[m["case"]] = (lane, m)
    for cid, e in entries.items():
        lane = e["_lane_file"]
        if cid not in manifest_cases:
            st.fail(lane, cid, "key", "key case has no built manifest")
        else:
            m = manifest_cases[cid][1]
            if e.get("lane") not in (None, lane, m.get("lane")):
                st.fail(lane, cid, "key", "key lane %r differs from the lane file %r" % (e.get("lane"), lane))
            if sorted(e.get("checks", [])) != sorted(m.get("checks", [])):
                st.fail(lane, cid, "key", "key checks %s differ from manifest checks %s" % (e.get("checks"), m.get("checks")))
        for field in ("checks", "requirements", "runs_at", "expected"):
            if field not in e:
                st.fail(lane, cid, "key", "missing field %r" % field)
        for r in e.get("requirements", []):
            if r not in REQUIREMENTS:
                st.fail(lane, cid, "key", "requirement id %r is not R1 to R43" % r)
        if runs_at_values(e.get("runs_at")) is None:
            st.fail(lane, cid, "key", "runs_at %r is not one of %s or a list of them without repeats (ruling E7-11)"
                    % (e.get("runs_at"), RUNS_AT))
        exp = e.get("expected")
        if not isinstance(exp, dict):
            st.fail(lane, cid, "key", "expected is not an object")
        else:
            for k in exp:
                if k != "$exact" and k not in result_props:
                    st.fail(lane, cid, "key", "expected.%s is not a property of result.schema.json" % k)
            for p in validate_form(exp, "expected"):
                st.fail(lane, cid, "key", "match form: " + p)
        dn = e.get("deterministic_now")
        if dn is not None:
            if not isinstance(dn, dict):
                st.fail(lane, cid, "key", "deterministic_now is not an object")
            else:
                for k in dn:
                    if k not in ("identity_matches_pin", "input_validates", "invalid_fields", "checkpoint"):
                        st.fail(lane, cid, "key", "deterministic_now.%s is not a section 5.9 assertion" % k)
                cp = dn.get("checkpoint")
                if cp is not None and not (cp in ("valid", "tolerated") or (isinstance(cp, str) and cp.startswith("corrupt"))):
                    st.fail(lane, cid, "key", "deterministic_now.checkpoint %r is not valid | tolerated | corrupt: <reason>" % cp)
    for cid, (lane, m) in manifest_cases.items():
        if cid not in entries:
            st.fail(lane, cid, "key", "built case has no key entry")
    for lane, cov in coverage.items():
        for field in ("requirements", "checks"):
            if not isinstance(cov.get(field), dict):
                st.fail(lane, "_coverage", "key", "_coverage.%s is not an object" % field)
                continue
            for k, cases in cov[field].items():
                if field == "requirements" and k not in REQUIREMENTS:
                    st.fail(lane, "_coverage", "key", "_coverage names requirement %r" % k)
                if not isinstance(cases, list):
                    st.fail(lane, "_coverage", "key", "_coverage.%s.%s is not a list" % (field, k))
                    continue
                for c in cases:
                    if c not in entries:
                        st.fail(lane, "_coverage", "key", "_coverage.%s.%s names unknown case %r" % (field, k, c))
                    elif e_lacks(entries[c], field, k):
                        st.fail(lane, c, "key", "_coverage lists %s under %s but the entry does not" % (c, k))
        lane_entries = [e for e in entries.values() if e["_lane_file"] == lane]
        for e in lane_entries:
            for r in e.get("requirements", []):
                if e["case"] not in (cov.get("requirements") or {}).get(r, []):
                    st.fail(lane, e["case"], "key", "entry lists %s but _coverage does not" % r)
            for k in e.get("checks", []):
                if e["case"] not in (cov.get("checks") or {}).get(k, []):
                    st.fail(lane, e["case"], "key", "entry lists check %s but _coverage does not" % k)
    return st.report("%d key entries over %d lanes, %d built cases" % (len(entries), len(coverage), len(manifest_cases)))


def e_lacks(entry, field, k):
    return k not in entry.get(field, [])


# ---- step 5: coverage -------------------------------------------------------------------------------

def step5(lanes, entries, coverage, write):
    st = Step(5, "coverage R1 to R43 and section 16 checks")
    req = {r: set() for r in REQUIREMENTS}
    chk = {c: set() for c in CHECK_CODES}
    for cov in coverage.values():
        for r, cases in (cov.get("requirements") or {}).items():
            if r in req and isinstance(cases, list):
                req[r].update(cases)
        for c, cases in (cov.get("checks") or {}).items():
            if isinstance(cases, list):
                chk.setdefault(c, set()).update(cases)
    trigger_ids = []
    if os.path.exists(TRIGGER):
        try:
            trigger_ids = [r["id"] for r in read_json(TRIGGER).get("requests", [])]
        except (ValueError, KeyError, TypeError):
            trigger_ids = []
    uncovered_req, uncovered_chk = [], []
    for r in REQUIREMENTS:
        if req[r]:
            continue
        if r in E9_ONLY:
            st.notes.append("%s points at E9 (%s, adapter-only)" % (r, E9_ONLY[r]))
        elif r in TRIGGER_SERVED and trigger_ids:
            st.notes.append("%s is served by the trigger set (%s, %d requests)" % (r, TRIGGER_SERVED[r], len(trigger_ids)))
        else:
            uncovered_req.append(r)
            st.fail(None, None, "key", "requirement %s has no case in any _coverage" % r)
    for c in CHECK_CODES:
        if chk.get(c):
            continue
        if c in E9_ONLY:
            continue
        if c in TRIGGER_SERVED and trigger_ids:
            continue
        uncovered_chk.append(c)
        st.fail(None, None, "key", "check %s has no case in any _coverage" % c)
    extra_checks = sorted(c for c in chk if c not in CHECK_CODES)
    for c in extra_checks:
        st.fail(None, None, "key", "_coverage names check %r, not a section 16 code" % c)
    doc = {
        "requirements": {r: sorted(req[r]) for r in REQUIREMENTS},
        "checks": {c: sorted(chk.get(c, ())) for c in CHECK_CODES},
        "runs_at": {cid: (runs_at_values(e.get("runs_at")) or e.get("runs_at")) for cid, e in sorted(entries.items())},
        "e9_only": {"R22": "D1 delivery fixture, E9"},
        "trigger_set": {"R27": "T1", "requests": trigger_ids},
        "uncovered_requirements": uncovered_req,
        "uncovered_checks": uncovered_chk,
        "lanes": sorted(coverage),
    }
    if write:
        with open(os.path.join(KEY_DIR, "coverage.json"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(doc, indent=2, sort_keys=True) + "\n")
        with open(os.path.join(KEY_DIR, "coverage.md"), "w", encoding="utf-8") as fh:
            fh.write(coverage_md(doc, entries, trigger_ids))
        st.notes.append("wrote answer-key/coverage.json and coverage.md")
    else:
        st.notes.append("coverage files not written (a --lane subset was selected)")
    by_case_req = sum(1 for r in REQUIREMENTS if req[r])
    by_case_chk = sum(1 for c in CHECK_CODES if chk.get(c))
    return st.report("%d/43 requirements and %d/%d checks have fixture cases; %d requirements and %d checks uncovered"
                     % (by_case_req, by_case_chk, len(CHECK_CODES), len(uncovered_req), len(uncovered_chk)))


def coverage_md(doc, entries, trigger_ids):
    def values(case):
        if case not in entries:
            return []
        return runs_at_values(entries[case].get("runs_at")) or []

    def runs(cases):
        seen = set()
        for c in cases:
            seen.update(values(c))
        return ", ".join(v for v in RUNS_AT if v in seen)
    rows = ["# Coverage (generated by checks/run-checks.py step 5)", "",
            "Merged from every `_coverage` element under `answer-key/`. Where each case runs is the key's `runs_at`;",
            "a case with a list (ruling E7-11) counts under every value listed, and a row's Runs at column is the",
            "union over its cases.", "",
            "## Requirements R1 to R43", "", "| Req | Cases | Runs at |", "|---|---|---|"]
    for r in REQUIREMENTS:
        cases = doc["requirements"][r]
        if cases:
            rows.append("| %s | %s | %s |" % (r, ", ".join("`%s`" % c for c in cases), runs(cases)))
        elif r in E9_ONLY:
            rows.append("| %s | (D1 delivery fixture) | E9 |" % r)
        elif r in TRIGGER_SERVED and trigger_ids:
            rows.append("| %s | trigger set: %s | E10/E11 (T1) |" % (r, ", ".join("`%s`" % t for t in trigger_ids)))
        else:
            rows.append("| %s | UNCOVERED | |" % r)
    rows += ["", "## Section 16 check codes", "", "| Check | Cases | Runs at |", "|---|---|---|"]
    for c in CHECK_CODES:
        cases = doc["checks"][c]
        if cases:
            rows.append("| %s | %s | %s |" % (c, ", ".join("`%s`" % x for x in cases), runs(cases)))
        elif c in E9_ONLY:
            rows.append("| %s | (delivery fixture) | E9 |" % c)
        elif c in TRIGGER_SERVED and trigger_ids:
            rows.append("| %s | trigger set (%d requests) | E10/E11 |" % (c, len(trigger_ids)))
        else:
            rows.append("| %s | UNCOVERED | |" % c)
    rows += ["", "## Where each case runs", "", "| Case | Runs at |", "|---|---|"]
    for cid in sorted(entries):
        rows.append("| `%s` | %s |" % (cid, ", ".join(values(cid)) or "(invalid runs_at)"))
    rows += ["", "Uncovered requirements: %s" % (", ".join(doc["uncovered_requirements"]) or "none"),
             "Uncovered checks: %s" % (", ".join(doc["uncovered_checks"]) or "none"), ""]
    return "\n".join(rows)


# ---- step 6: identity now ------------------------------------------------------------------------------

def normalize_commit(workspace, pin):
    try:
        return fixturelib._git(workspace, ["rev-parse", "--verify", "--quiet", pin + "^{commit}"]).strip() or None
    except fixturelib.FixtureError:
        return None


def step6(out, lanes, entries):
    st = Step(6, "identity against the pin")
    n = 0
    for lane in lanes:
        for cdir in case_dirs(out, lane):
            m = read_json(os.path.join(cdir, "manifest.json"))
            cid = m["case"]
            e = entries.get(cid)
            if e is None or "identity_matches_pin" not in (e.get("deterministic_now") or {}):
                continue
            n += 1
            want = bool(e["deterministic_now"]["identity_matches_pin"])
            ws = os.path.join(cdir, m.get("workspace", "workspace"))
            pin = read_json(os.path.join(cdir, "input.json")).get("source_identity")
            if not isinstance(pin, dict) or not pin:
                st.fail(lane, cid, "key", "deterministic_now.identity_matches_pin set but input.json carries no source_identity pin")
                continue
            actual = fixturelib.identity_of(ws)
            if actual != m.get("identity"):
                st.fail(lane, cid, "fixture", "identity_of(workspace) differs from manifest.identity (workspace changed after manifest)")
            mismatches = []
            for field, value in pin.items():
                if field == "commit":
                    full = normalize_commit(ws, value)
                    if full is None:
                        mismatches.append("commit %s unresolvable" % value[:12])
                    elif full != actual["commit"]:
                        mismatches.append("commit %s != %s" % (full[:12], actual["commit"][:12]))
                elif field not in actual:
                    mismatches.append("unknown pin field %s" % field)
                elif actual[field] != value:
                    mismatches.append("%s %s != %s" % (field, json.dumps(value)[:40], json.dumps(actual[field])[:40]))
            matched = not mismatches
            if matched != want:
                st.fail(lane, cid, "key", "identity_matches_pin expected %s, computed %s (%s)"
                        % (want, matched, "; ".join(mismatches) or "every pinned field equal"))
    return st.report("%d pinned cases compared with fixturelib.identity_of" % n)


# ---- step 7: checkpoint now --------------------------------------------------------------------------------

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def check_checkpoint(cp, log_lines):
    """Section 11 integrity, ported from validate-examples.py plus carried item 11.

    Returns 'ok', 'repair', or the first defect found. Item-state validity (section 11 step 4)
    is not part of this verdict: the key's vocabulary reserves 'corrupt' for the integrity check.
    """
    integrity = cp.get("integrity")
    if not isinstance(integrity, dict) or not all(k in integrity for k in ("seq", "prev", "self")):
        return "integrity block missing or incomplete"
    body = copy.deepcopy(cp)
    self_ = body["integrity"].pop("self")
    if hashlib.sha256(canon(body)).hexdigest() != self_:
        return "self digest does not recompute"
    seq, prev = integrity["seq"], integrity["prev"]
    rows = [l.split() for l in log_lines if l.strip()]
    if any(len(r) != 2 or not r[0].isdigit() for r in rows):
        return "log line with a shape other than <seq> <self>"
    if [int(r[0]) for r in rows] != list(range(len(rows))):
        return "log has a gap or a repeated seq"
    if rows and rows[-1] == [str(seq), self_]:
        if seq == 0:
            return "ok" if prev is None and len(rows) == 1 else "prev must be null at seq 0"
        return "ok" if len(rows) >= 2 and rows[-2][1] == prev else "prev is not the line before"
    if len(rows) >= 2 and rows[-2] == [str(seq), self_] and int(rows[-1][0]) == seq + 1:
        # the log announced a write whose rename never landed: tolerated only when the
        # predecessor link also holds (Appendix B carried item 11)
        if seq == 0:
            return "repair" if prev is None else "prev must be null at seq 0"
        if len(rows) >= 3 and rows[-3][1] == prev:
            return "repair"
        return "announced write ahead of the checkpoint, but prev is not the line before"
    return "(seq, self) is not the log's last line"


def checkpoint_verdict(run_dir):
    cp_path = os.path.join(run_dir, "checkpoint.json")
    log_path = os.path.join(run_dir, "checkpoint.log")
    if not os.path.exists(cp_path):
        return "corrupt: run/checkpoint.json does not exist"
    if not os.path.exists(log_path):
        return "corrupt: run/checkpoint.log does not exist"
    try:
        cp = read_json(cp_path)
    except ValueError as exc:
        return "corrupt: run/checkpoint.json does not parse: %s" % exc
    if not isinstance(cp, dict):
        return "corrupt: run/checkpoint.json is not an object"
    with open(log_path, "r", encoding="utf-8") as fh:
        log_lines = fh.read().splitlines()
    got = check_checkpoint(cp, log_lines)
    if got == "ok":
        return "valid"
    if got == "repair":
        return "tolerated"
    return "corrupt: " + got


def step7(out, lanes, entries):
    st = Step(7, "checkpoint integrity (section 11)")
    n = 0
    for lane in lanes:
        for cdir in case_dirs(out, lane):
            m = read_json(os.path.join(cdir, "manifest.json"))
            cid = m["case"]
            e = entries.get(cid)
            if e is None or "checkpoint" not in (e.get("deterministic_now") or {}):
                continue
            n += 1
            want = e["deterministic_now"]["checkpoint"]
            got = checkpoint_verdict(os.path.join(cdir, m.get("run_dir", "run")))
            want_class = want.split(":")[0].strip() if isinstance(want, str) else None
            got_class = got.split(":")[0]
            if want_class != got_class:
                st.fail(lane, cid, "key", "checkpoint: key says %r, runner computed %r" % (want, got))
    return st.report("%d checkpoints checked (self digest, chain, log, the tolerated state with its prev link)" % n)


# ---- step 8: unit tests --------------------------------------------------------------------------------------

def step8():
    st = Step(8, "unit tests: test_fixturelib.py and test_match.py")
    details = []
    for cwd, name in ((LIB_DIR, "test_fixturelib"), (HERE, "test_match")):
        if not os.path.exists(os.path.join(cwd, name + ".py")):
            st.fail(None, None, "runner" if name == "test_match" else "fixture", "%s.py is missing" % name)
            continue
        code, so, se = run([GEN_PYTHON, "-m", "unittest", name], cwd=cwd)
        tail = [l for l in se.splitlines() if l.strip()][-2:]
        details.append("%s: %s" % (name, " / ".join(tail)))
        if code != 0:
            st.fail(None, None, "runner" if name == "test_match" else "fixture", "%s failed (exit %d): %s" % (name, code, se.strip()[-400:]))
    return st.report("; ".join(details))


# ---- step 9: build.py interface ------------------------------------------------------------------------------

def step9(out, lanes, summaries):
    st = Step(9, "build.py interface (--help, --list, unknown --case, other cwd)")
    for lane in lanes:
        build = os.path.join(FIXTURES, lane, "build.py")
        code, so, se = run([GEN_PYTHON, build, "--help"], cwd="/")
        if code != 0:
            st.fail(lane, None, "fixture", "--help exited %d" % code)
        code, so, se = run([GEN_PYTHON, build, "--list"], cwd="/")
        listed = [l.strip() for l in so.splitlines() if l.strip()]
        if code != 0 or not listed:
            st.fail(lane, None, "fixture", "--list exited %d with %d ids" % (code, len(listed)))
        built = [r["case"] for r in summaries.get(lane, {}).get("cases", [])]
        if built and listed and listed != built:
            st.fail(lane, None, "fixture", "--list ids differ from the built cases: %s vs %s" % (listed, built))
        code, so, se = run([GEN_PYTHON, build, "--out", os.path.join(out, lane), "--case", "no-such-case-zz"], cwd="/")
        if code != 2:
            st.fail(lane, None, "fixture", "unknown --case exited %d, not 2" % code)
        if listed:
            first = listed[0]
            before = None
            mp = os.path.join(out, lane, first, "manifest.json")
            if os.path.exists(mp):
                before = read_json(mp)["tree_sha256"]
            code, so, se = run([GEN_PYTHON, build, "--out", os.path.join(out, lane), "--case", first, "--json"], cwd=tempfile.gettempdir())
            if code != 0:
                st.fail(lane, first, "fixture", "rebuild of one case from another cwd exited %d: %s" % (code, se.strip()[-200:]))
            else:
                try:
                    rows = json.loads(so)["cases"]
                    if before and rows and rows[0]["tree_sha256"] != before:
                        st.fail(lane, first, "fixture", "rebuild from another cwd changed tree_sha256")
                except (ValueError, KeyError, IndexError):
                    st.fail(lane, first, "fixture", "rebuild from another cwd printed no JSON summary")
    return st.report("%d generators exercised" % len(lanes))


# ---- main ---------------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="recheck-v2 E7 check runner (lane contract section 8)")
    ap.add_argument("--out", metavar="DIR", help="build directory (default: a fresh temp dir)")
    ap.add_argument("--lane", metavar="NAME", action="append", default=[], help="restrict to these lanes (repeatable)")
    ap.add_argument("--json", action="store_true", help="print one JSON object instead of the human report")
    args = ap.parse_args(argv)

    available = lanes_available()
    lanes = args.lane or available
    unknown = [l for l in lanes if l not in available]
    if unknown:
        sys.stderr.write("unknown lane(s): %s\navailable: %s\n" % (", ".join(unknown), ", ".join(available)))
        return 2
    out = os.path.abspath(args.out) if args.out else tempfile.mkdtemp(prefix="recheck-v2-e7-")
    os.makedirs(out, exist_ok=True)

    steps = []
    r1, summaries = step1(out, lanes)
    steps.append(r1)
    entries, coverage, problems = load_keys(lanes)
    steps.append(step2(out, lanes, entries))
    steps.append(step3(out, lanes))
    steps.append(step4(out, lanes, entries, coverage, problems))
    steps.append(step5(lanes, entries, coverage, write=(sorted(lanes) == available)))
    steps.append(step6(out, lanes, entries))
    steps.append(step7(out, lanes, entries))
    steps.append(step8())
    steps.append(step9(out, lanes, summaries))

    ok = all(s["pass"] for s in steps)
    if args.json:
        print(json.dumps({"steps": steps, "out": out, "ok": ok}, indent=2))
    else:
        for s in steps:
            print("%s  step %d  %s: %s" % ("PASS" if s["pass"] else "FAIL", s["step"], s["name"], s["detail"]))
            for f in s["failures"]:
                print("      [%s] %s%s: %s" % (f["side"], f["lane"] or "-", ("/" + f["case"]) if f["case"] else "", f["detail"]))
        print("%s: %d/%d steps passed (out: %s)" % ("OK" if ok else "FAILED", sum(s["pass"] for s in steps), len(steps), out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
