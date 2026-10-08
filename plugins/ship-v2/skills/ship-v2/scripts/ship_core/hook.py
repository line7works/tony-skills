"""`hook`: the adapter's armed-or-not reading, recorded (v1's step 0; ruling E15-12; contract section 3.2).

The documented summon is `/goal /ship-v2 <slice> [doc]`; a skill cannot arm the Stop hook. The adapter's helper
(`adapters/<harness>/hook.py`) reads whether this session showed the Stop hook's confirmation and prints one reading
(`references/answer.schema.json`, kind `hook`), which this phase takes whole and records: refused (exit 5, nothing
written) when it is another harness's reading, or when a harness other than Claude Code claims an armed hook (on
Codex the reading is `Hook: NOT armed`, labelled honestly). Armed or not, the run proceeds identically; the `SHIP:`
block labels it (`forms.hook_label`), never claiming armed when it was not.
"""
from . import common, forms

ARMABLE = ("claude-code",)


def handler(ctx, args):
    """`hook --run-dir D --reading FILE`."""
    run = common.open_run(ctx, args.run_dir, ("selected",), "hook")
    reading, early = common.answer_file(ctx, run, args.reading, "hook", "hook reading")
    if early is not None:
        return early
    harness = common.harness(run)
    if reading["harness"] != harness:
        return common.refuse(ctx, run, "the hook reading is %r's and this run is driven from %r: the reading comes "
                                       "from this harness's own adapter" % (reading["harness"], harness))
    if reading["armed"] and harness not in ARMABLE:
        return common.refuse(ctx, run, "a reading from %r claims an armed Stop hook, which only Claude Code has: on "
                                       "this harness the hook reads `NOT armed`, labelled honestly" % harness)
    state = common.state(run)
    state["hook"] = {"harness": harness, "armed": bool(reading["armed"]), "label": forms.hook_label(reading["armed"]),
                     "how": reading["how"], "evidence": reading.get("evidence")}
    common.save(run, state, "hooked")
    return ctx.emit(ctx.envelope(next="visit --station build-v2", run_id=common.run_id(run), hook=state["hook"],
                                 summon=forms.summon_goal(state["slice"], state["doc"])))
