"""What a row states, and when a manifest may be built from it (the frame's ROW-1, ROW-2, ROW-3, with the
build-time halves of OP-2, OP-3, OP-10, OP-11, EV-4, EV-6, ORD-1 to ORD-4, KEEP-4, SEC-3, SEC-4, SEC-8,
SEC-12, RISK-1 and RISK-2), and the owner's ruling on a secret's alphabet (A142: a secret field whose registered
alphabet admits white space, a control character or a format character fails the build, the row and the provider
named; `chars.py`).

A row is a JSON object with the twenty-five entries of ROW-1's table, every one present and none
empty. For its kind each entry is required (R: the row states it), forbidden (F: the row writes the
word `none`), or applies by a condition (O: stated where the condition holds, `none` where it does
not). `admit(row, ...)` returns the findings of one row, each naming the row and the entry; a lane's
rows are read, and a manifest built from them, only where there are none.

Entry names, in the table's order:

    id, kind, phase      one entry of the table, three keys
    thing                its role, how its identity is read, its tracked state; or the output field it refers to
    planning_test        what the look reads of its place or its thing
    before_test, after_test
    construction         {"id": "C1".."C7", ...}: for C2 and C5 the document cited, for C5 each condition the
                         refusal covers, for C3, C6 and C7 (and a shortcut's add or put-back) each accepted risk
    commands             each declared command, by its provider's declaration
    repo_commands        each command that can change a repository
    after_check, output, needs, condition, lost_answer, way_back, reverse_inputs, span, mode,
    safe_content, answers, review_file, owner_names, keep_scope, keeps_required, content_classes, form_lines
"""
from . import chars, results

NONE = "none"
KINDS = ("check", "build", "keep", "create", "change", "move", "owner step", "owner answer", "adopt")
EFFECT_KINDS = ("build", "keep", "create", "change", "move")
OWNER_KINDS = ("owner step", "owner answer")
LEVELS = ("state", "made", "passed", "answered")

# SEC-3's environment row: a name is passed "never for `PATH` or any other name that chooses which program or which
# code a child runs". The frame names `PATH` and leaves the rest to the build: these are the names, and the
# prefixes, of the settings the system's loader, the shells, git and the common interpreters read to choose a
# program or code (a choice of the build, listed in its report).
CHOOSES_CODE = frozenset((
    "PATH", "BASH_ENV", "ENV", "SHELL", "SHELLOPTS", "EDITOR", "VISUAL", "PAGER",
    "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE", "PYTHONEXECUTABLE", "PYTHONINSPECT",
    "PERL5LIB", "PERLLIB", "PERL5OPT", "RUBYLIB", "RUBYOPT", "GEM_HOME", "GEM_PATH", "NODE_OPTIONS", "NODE_PATH",
    "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH", "DEVELOPER_DIR", "SDKROOT", "TOOLCHAINS",
    "GIT_EXEC_PATH", "GIT_SSH", "GIT_SSH_COMMAND", "GIT_ASKPASS", "SSH_ASKPASS", "GIT_EDITOR", "GIT_PAGER",
    "GIT_SEQUENCE_EDITOR", "GIT_CONFIG", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT", "GIT_TEMPLATE_DIR", "GIT_EXTERNAL_DIFF",
))
CHOOSES_CODE_PREFIXES = ("DYLD_", "LD_", "GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")


def chooses_code(name):
    """Whether an environment name chooses which program or which code a child runs (SEC-3)."""
    return isinstance(name, str) and (name in CHOOSES_CODE or name.startswith(CHOOSES_CODE_PREFIXES))
TREATMENTS = ("then not applicable", "then not needed")
CONSTRUCTIONS = {"build": ("C1",), "keep": ("C1",), "create": ("C2",), "change": ("C3", "C4", "C5", "C6"), "move": ("C7",)}
RISK_OF = {"C3": "RK2", "C6": "RK3", "C7": "RK4"}
RK3_ROWS = ("T20", "T21", "V10", "V11")           # the four rows RK3 names (the catalog's Part 6)
ADOPTABLE_OUTPUT = "project folder"               # the one output adoption is offered for (OP-10; A6)
PLACEMENTS = ("in place", "at the end")
MODES = ("read back", "on his word")

ENTRIES = ("id_kind_phase", "thing", "planning_test", "before_test", "after_test", "construction", "commands",
           "repo_commands", "after_check", "output", "needs", "condition", "lost_answer", "way_back",
           "reverse_inputs", "span", "mode", "safe_content", "answers", "review_file", "owner_names", "keep_scope",
           "keeps_required", "content_classes", "form_lines")
KEYS = ("id", "kind", "phase") + ENTRIES[1:]

# ROW-1's table, one string per entry, one letter per kind in the order of KINDS.
#                      check build keep create change move step answer adopt
TABLE = {
    "id_kind_phase":   "RRRRRRRRR",
    "thing":           "RRRRRRRFR",
    "planning_test":   "FRRRRRFFR",
    "before_test":     "FRRRRRFFF",
    "after_test":      "FRRRRROFF",
    "construction":    "FRRRRRFFF",
    "commands":        "OOOROOOFF",
    "repo_commands":   "FOOOOOFFF",
    "after_check":     "FRRRRRFFF",
    "output":          "RRRRRRRRR",
    "needs":           "OOOOOOOOO",
    "condition":       "OOOOOOOOO",
    "lost_answer":     "FFFRFFFFF",
    "way_back":        "FFFFRRRFF",
    "reverse_inputs":  "FFFFOOOFF",
    "span":            "FFFFOFFFF",
    "mode":            "FFFFFFRFF",
    "safe_content":    "FFFFFFRRF",
    "answers":         "FFFFFFFRF",
    "review_file":     "FFFFFFOOF",
    "owner_names":     "FFFFFFFFR",
    "keep_scope":      "FFRFFFFFF",
    "keeps_required":  "FFFFOOOFF",
    "content_classes": "RRRRRRRRR",
    "form_lines":      "RRRRRRRRR",
}


def letter(entry, kind):
    return TABLE[entry][KINDS.index(kind)]


def is_none(value):
    return value == NONE


def stated(value):
    """An entry is stated when it is neither the word `none` nor empty."""
    return not is_none(value) and value not in (None, "", [], {})


def tests_of(row):
    out = []
    for key in ("planning_test", "before_test", "after_test", "after_check"):
        if isinstance(row.get(key), list):
            out.extend((key, c) for c in row[key] if isinstance(c, dict))
    thing = row.get("thing")
    if isinstance(thing, dict) and isinstance(thing.get("passes"), list):
        out.extend(("thing", c) for c in thing["passes"] if isinstance(c, dict))
    return out


def command_names_used(row):
    """The local names of the commands a row's tests, its construction and its thing refer to."""
    used = [c.get("command") for _k, c in tests_of(row) if c.get("read") == "command"]
    construction = row.get("construction")
    if isinstance(construction, dict):
        for key in ("command", "builder", "status_command"):
            if construction.get(key):
                used.append(construction[key])
    thing = row.get("thing")
    if isinstance(thing, dict):
        if thing.get("command"):
            used.append(thing["command"])
        for key in ("identity_read", "name_form", "found_things"):
            if isinstance(thing.get(key), dict) and thing[key].get("command"):
                used.append(thing[key]["command"])
        for other in thing.get("also") if isinstance(thing.get("also"), list) else []:
            if isinstance(other, dict) and isinstance(other.get("read"), dict) and other["read"].get("command"):
                used.append(other["read"]["command"])        # EV-3's read of a thing named by a held id
    scope = row.get("keep_scope")
    if isinstance(scope, dict) and isinstance(scope.get("source_identity_read"), dict):
        used.append(scope["source_identity_read"].get("command"))
    for item in row.get("reverse_inputs") if isinstance(row.get("reverse_inputs"), list) else []:
        if isinstance(item, dict) and item.get("read") == "command":
            used.append(item.get("command"))
    lost = row.get("lost_answer")
    if isinstance(lost, dict) and lost.get("command"):
        used.append(lost["command"])
    return [u for u in used if u]


def _o_condition(entry, row):
    """Whether an O entry's condition holds for this row; None where the entry has no condition
    beyond the row's own statement (a need, a condition)."""
    kind = row.get("kind")
    if entry == "after_test":
        return row.get("mode") == "read back"
    if entry == "commands":
        construction = row.get("construction") if isinstance(row.get("construction"), dict) else {}
        return bool(command_names_used(row)) or construction.get("id") in ("C4", "C5", "C6")
    if entry == "repo_commands":
        commands = row.get("commands") if isinstance(row.get("commands"), list) else []
        return any(isinstance(c, dict) and (c.get("declaration") or {}).get("changes_repository") for c in commands)
    if entry == "reverse_inputs":
        return isinstance(row.get("way_back"), dict) and "reverse" in row["way_back"]
    if entry == "span":
        thing = row.get("thing") if isinstance(row.get("thing"), dict) else {}
        return thing.get("span") is True and isinstance(row.get("way_back"), dict) and "reverse" in row["way_back"]
    if entry == "review_file":
        content = row.get("safe_content") if isinstance(row.get("safe_content"), dict) else {}
        return content.get("needs_review") is True
    if entry == "keeps_required":
        thing = row.get("thing") if isinstance(row.get("thing"), dict) else {}
        return thing.get("retires") is True
    return None


def finding(row, entry, words):
    return {"row": row.get("id") if isinstance(row, dict) else None, "entry": entry, "finding": words}


def _table_findings(row):
    out = []
    kind = row.get("kind")
    for entry in ENTRIES:
        keys = ("id", "kind", "phase") if entry == "id_kind_phase" else (entry,)
        for key in keys:
            if key not in row:
                out.append(finding(row, key, "the entry is left out"))
                continue
            value = row[key]
            if value in (None, "", [], {}):
                out.append(finding(row, key, "the entry is left empty"))
                continue
            rule = letter(entry, kind)
            if rule == "R" and is_none(value):
                out.append(finding(row, key, "a required entry is written none"))
            elif rule == "F" and not is_none(value):
                out.append(finding(row, key, "a forbidden entry is stated"))
            elif rule == "O":
                holds = _o_condition(entry, row)
                if holds is True and is_none(value):
                    out.append(finding(row, key, "the entry is written none where its condition holds"))
                elif holds is False and not is_none(value):
                    out.append(finding(row, key, "the entry is stated where its condition does not hold"))
    for key in row:
        if key not in KEYS:
            out.append(finding(row, key, "not an entry of a row"))
    return out


def _construction_findings(row, as_reverse=False):
    out = []
    kind, construction = row.get("kind"), row.get("construction")
    if kind not in CONSTRUCTIONS:
        return out
    if not isinstance(construction, dict):
        return [finding(row, "construction", "not a construction")]
    cid = construction.get("id")
    if cid not in CONSTRUCTIONS[kind]:
        return [finding(row, "construction", "a construction OP-2 does not give its kind")]
    risks = construction.get("risks") if isinstance(construction.get("risks"), list) else []
    before = row.get("before_test") if isinstance(row.get("before_test"), list) else []
    name_free = [c for c in before if isinstance(c, dict) and c.get("read") == "name-free"]
    wanted = set()
    if cid in RISK_OF:
        wanted.add(RISK_OF[cid])
    if name_free:
        # a shortcut's add or put-back: RK5, and RK13 beside it, whose window is RK5's (RISK-1; the owner's ruling A63)
        wanted.update(("RK5", "RK13"))
    for risk in risks:
        if risk not in wanted:
            out.append(finding(row, "construction", "an accepted risk that does not cover its construction"))
    for risk in sorted(wanted):
        if risk not in risks:
            out.append(finding(row, "construction", "its construction's window is carried under no accepted risk (RISK-2)"))
    if cid == "C6" and row.get("id") not in RK3_ROWS:
        out.append(finding(row, "construction", "a read-then-ask on a row RK3 does not name (RISK-2)"))
    if cid in ("C2", "C5") and not construction.get("document"):
        out.append(finding(row, "construction", "no document is cited"))
    listed = construction.get("conditions") if isinstance(construction.get("conditions"), list) else []
    for condition in before:
        if not isinstance(condition, dict):
            continue
        covered = condition.get("id") in listed
        if cid == "C5" and not covered:
            out.append(finding(row, "construction", "the cited refusal does not cover the whole before-test (RISK-2)"))
        if condition.get("on") == "other" and condition.get("read") != "name-free":
            enforced = (cid == "C4" and condition.get("enforced") == "in the same request") or (cid == "C5" and covered)
            if not enforced:
                out.append(finding(row, "before_test", "a condition on something the effect does not change, which the "
                                                       "construction does not enforce (RISK-2)"))
    return out


def _command_findings(row, providers, held_outputs, in_look):
    out = []
    commands = row.get("commands") if isinstance(row.get("commands"), list) else []
    names = {}
    for command in commands:
        if not isinstance(command, dict) or not command.get("name") or not isinstance(command.get("use"), str):
            out.append(finding(row, "commands", "a command is not declared by a provider"))
            continue
        provider, _, name = command["use"].partition(".")
        decl = ((providers.get(provider) or {}).get("commands") or {}).get(name)
        if not isinstance(decl, dict):
            out.append(finding(row, "commands", "a command with no declaration"))
            continue
        names[command["name"]] = decl
        for field in decl.get("fields") or []:
            if field.get("disposition") not in results.TYPES.get(field.get("type"), ()):
                out.append(finding(row, "commands", "a disposition SEC-4 does not give its type"))
            if field.get("disposition") == "secret" and "alphabet" in field and chars.alphabet_admits_barred(field.get("alphabet")):
                # the owner's ruling on PS46 (A142): "A declaration whose secret field's registered alphabet admits any white
                # space, any control character or any format character fails its manifest build, and the row is named"; his
                # pick's words: "The tool names the provider". The names are the declaration's own fixed words (SEC-1).
                out.append(finding(row, "commands", "a secret field whose registered alphabet admits white space, a control "
                                                    "character or a format character (SEC-4; the owner's ruling, A142): "
                                                    "provider %s, command %s, field %s" % (provider, name, field.get("name"))))
        effects = decl.get("effects", 0)
        if not isinstance(effects, int) or effects > 1:
            out.append(finding(row, "commands", "a command that does more than one thing, with the rest not turned off (OP-1)"))
        for side in decl.get("side_effects") or []:
            if not side.get("turned_off_by"):
                word = ("a secret-writing side effect that cannot be turned off (SEC-8)" if side.get("secret_writing")
                        else "a command that does more than one thing, with the rest not turned off (OP-1)")
                out.append(finding(row, "commands", word))
        if decl.get("secret_output") == "in place":
            out.append(finding(row, "commands", "a tool that cannot be pointed at a staging path (SEC-8)"))
        if decl.get("repository_writes") == "unlisted":
            out.append(finding(row, "commands", "a builder whose repository writes are neither turned off nor listed (OP-11)"))
        registered = decl.get("env") or {}
        for env_name, spec in registered.items():
            if spec.get("class") == "passed" and (env_name in ((providers.get(provider) or {}).get("credential_env") or [])
                                                  or not spec.get("reason")):
                out.append(finding(row, "commands", "a passed environment name that carries a credential or gives no reason"))
            if spec.get("class") == "passed" and chooses_code(env_name):
                out.append(finding(row, "commands", "a passed environment name that chooses which program or which code a child runs (SEC-3)"))
        slots = set(s.get("slot") for s in decl.get("protected_inputs") or [])
        params = command.get("params") if isinstance(command.get("params"), dict) else {}
        for param, value in params.items():
            if not isinstance(value, dict):
                continue
            reference = value.get("output")
            if reference and reference in held_outputs and decl.get("via") == "request":
                # SEC-2: a held value goes back to the provider that issued it in the frame's own request, to that provider's
                # fixed host and to no other
                if not isinstance(held_outputs, dict) or held_outputs.get(reference) != provider:
                    out.append(finding(row, "commands", "a held value goes back only to the provider that issued it (SEC-2)"))
                continue
            if reference and reference in held_outputs and param not in slots:
                where = "an environment value" if any(s.get("param") == param for s in registered.values() if isinstance(s, dict)) else "an argument"
                out.append(finding(row, "commands", "a template that puts a held or a secret field into %s (SEC-3)" % where))
    used = command_names_used(row)
    for name in used:
        if name not in names:
            out.append(finding(row, "commands", "a test or a construction names a command the row does not declare"))
    if in_look:
        for key, condition in tests_of(row):
            if key == "planning_test" and condition.get("read") == "command":
                decl = names.get(condition.get("command")) or {}
                if any(f.get("disposition") == "secret" for f in decl.get("fields") or []):
                    out.append(finding(row, "planning_test", "a command with a secret field in a look (SEC-12)"))
                if decl.get("effects", 0) != 0:
                    out.append(finding(row, "planning_test", "a look that would change something (RUN-5)"))
    repo = row.get("repo_commands")
    changing = [c["name"] for c in commands if isinstance(c, dict) and (c.get("declaration") or names.get(c.get("name")) or {}).get("changes_repository")]
    if isinstance(repo, list) and repo != changing:
        out.append(finding(row, "repo_commands", "the list is not the row's repository-changing commands, in order (OP-11)"))
    if is_none(repo) and changing:
        out.append(finding(row, "repo_commands", "the entry is written none where its condition holds"))
    return out


def _other_findings(row, as_reverse):
    out = []
    kind = row.get("kind")
    for need in row.get("needs") if isinstance(row.get("needs"), list) else []:
        if not isinstance(need, dict) or need.get("level") not in LEVELS:
            out.append(finding(row, "needs", "a level ORD-1 does not have"))
        elif need.get("level") == "answered" and not need.get("value"):
            out.append(finding(row, "needs", "a need at the answered level names no value"))
    if kind == "adopt":
        output = row.get("output") if isinstance(row.get("output"), dict) else {}
        if output.get("name") != ADOPTABLE_OUTPUT:
            out.append(finding(row, "output", "adoption is offered for the local project folder and for no other output (OP-10)"))
    if kind == "owner step":
        if row.get("mode") not in MODES and not is_none(row.get("mode")):
            out.append(finding(row, "mode", "not a mode of an owner step"))
        thing = row.get("thing") if isinstance(row.get("thing"), dict) else {}
        if thing.get("stands_in_for") and not thing.get("ruling"):
            out.append(finding(row, "thing", "an owner step stands in for an effect the tool will not run, and no ruling is cited (ROW-2)"))
    span = row.get("span")
    if isinstance(span, dict):
        if span.get("placement") not in PLACEMENTS:
            out.append(finding(row, "span", "not a placement"))
        if span.get("placement") == "at the end" and span.get("ordered") is True:
            out.append(finding(row, "span", "`at the end` is declared for a file the row marks as ordered (EV-6)"))
    way_back = row.get("way_back")
    if isinstance(way_back, dict):
        if "reverse" in way_back:
            reverse = way_back["reverse"]
            if not isinstance(reverse, dict) or reverse.get("kind") not in ("change", "move", "owner step", "build"):
                out.append(finding(row, "way_back", "a reverse EV-4 does not allow"))
            elif not as_reverse:
                for found in admit(reverse, {}, set(), as_reverse=True, skip_commands=True):
                    out.append(finding(row, "way_back", "a reverse EV-4 does not allow: %s" % found["finding"]))
        elif not way_back.get("none"):
            out.append(finding(row, "way_back", "neither a reverse nor `none` with its reason"))
    elif not is_none(way_back):
        out.append(finding(row, "way_back", "neither a reverse nor `none` with its reason"))
    return out


def admit(row, providers, held_outputs, as_reverse=False, skip_commands=False):
    """The findings of one row; [] where a manifest may be built from it."""
    if not isinstance(row, dict):
        return [finding({}, "row", "not a row")]
    if row.get("kind") not in KINDS:
        return [finding(row, "kind", "not one of the nine kinds (OP-2)")]
    out = _table_findings(row)
    out += _construction_findings(row, as_reverse)
    if not skip_commands:
        out += _command_findings(row, providers, held_outputs, in_look=True)
    out += _other_findings(row, as_reverse)
    out += _validator_findings(row)
    return out


def _validator_findings(row):
    """ROW-1: the row states "any validator that makes content of a file on this machine safe (SEC-1)"; a `local` mark that
    names a validator the row does not declare, or one the tool does not have, fails the build naming the entry."""
    from . import values
    classes = row.get("content_classes") if isinstance(row.get("content_classes"), dict) else {}
    declared = classes.get("validators") if isinstance(classes.get("validators"), list) else []
    out = []
    for name in values.validators_named(dict((k, v) for k, v in row.items() if k != "content_classes")):
        if name not in declared:
            out.append(finding(row, "content_classes", "a validator the row does not declare"))
        elif name not in values.VALIDATORS:
            out.append(finding(row, "content_classes", "a validator the tool does not have"))
    return out


def checklist_findings(lane):
    """ROW-3: every item of the lane's checklist is answered by a row, by a form line, or by a
    stated reason that it is not that lane's. An item may say what the answering row must state
    (`must`: entries the row has to hold as given), so that a pointer to a row that exists and does
    not answer the item is a finding too."""
    out = []
    by_id = dict((r.get("id"), r) for r in lane.get("rows") or [] if isinstance(r, dict))
    lines = lane.get("form_changes") if isinstance(lane.get("form_changes"), dict) else {}
    for item in lane.get("checklist") or []:
        name = item.get("item") if isinstance(item, dict) else None
        answer = item.get("answered_by") if isinstance(item, dict) else None
        if not isinstance(answer, dict) or not answer:
            out.append({"item": name, "finding": "unanswered"})
            continue
        if "row" in answer:
            row = by_id.get(answer["row"])
            if row is None:
                out.append({"item": name, "finding": "names a row that does not exist"})
                continue
            for key, want in (item.get("must") or {}).items():
                have = row.get(key)
                if isinstance(want, dict) and isinstance(have, dict):
                    ok = all(have.get(k) == v for k, v in want.items())
                else:
                    ok = have == want
                if not ok:
                    out.append({"item": name, "finding": "names a row that does not answer it"})
                    break
        elif "form_line" in answer:
            if answer["form_line"] not in lines:
                out.append({"item": name, "finding": "names a form line that does not exist"})
        elif not answer.get("reason"):
            out.append({"item": name, "finding": "unanswered"})
    return out
