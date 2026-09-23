"""The Opus-class model floor, enforced by the core (Astra's F5; v1 signoff Step 0, pick P5).

The floor is unchanged: reviewers run at Opus-class or better. What this module changes is WHO
establishes it. Before this fix the core recorded a verdict whatever `invocation.model` said, a
`floor_met: false` included, and nothing looked at the model the reviewer's answer named. Now:

- **The session's facts are the adapter's observed model id.** The class is computed here from
  `invocation.model.id` by the same map the adapters use (ruling E9-3; the Codex half provisional,
  as the pilot's lane settled it). The `floor_class` and `floor_met` the input carries are checked
  AGAINST that computation and never trusted in its place: a typed `floor_met: true` for a Haiku id
  is a disagreement, and a disagreement is refused.
- **The reviewer's facts are the readers result.** The answer's `model` is readers' effective
  model as the adapter's sidecar map hands it over (`answer_identity.model`). It must be
  established, at the floor, and the model the session recorded: a `claude-session` reader
  inherits the session's model, so any other id is a disagreement.
- **A false, null, missing or unestablished floor is a named stop** (`floor_refused`) before the
  reviewer request is emitted, before the answer is accepted, and again before anything is recorded.
  Nothing is written to the project. No model is upgraded, silently or otherwise, and eligibility is
  not changed: the map below is the adapters' map, moved where the core can apply it.

**Synthetic replay facts.** A seeded case replays a recorded answer without a live reviewer, so no
harness observed any model. Such a run may supply the facts through one explicit test interface,
honoured only with `SIGNOFF_TEST=1` in the environment: `SIGNOFF_TEST_REPLAY_MODEL=<model id>`
stands in for the observed model where the input or the answer carries none. The result names the
source as synthetic, and outside test mode the variable is ignored.
"""
import fnmatch
import os

FLOOR = "opus"
OPUS_PATTERNS = ("claude-opus-*", "claude-fable-*", "claude-mythos-*")
OPUS_IDS = ("gpt-6-astra", "gpt-5.6-sol")      # the Codex map, provisional (E9-3, E10-62)
BELOW = (("claude-sonnet-*", "sonnet"), ("claude-haiku-*", "haiku"))
UNKNOWN = "unknown"
REPLAY_FLAG = "SIGNOFF_TEST"
REPLAY_VAR = "SIGNOFF_TEST_REPLAY_MODEL"
STOP_CODE = "floor_refused"


class FloorRefused(RuntimeError):
    """The floor is not met, or cannot be established. Carries the sentence for the stop."""


def class_of(model_id):
    """(class, floor met): opus is met; sonnet and haiku are not; anything else is unknown/None."""
    if not isinstance(model_id, str) or not model_id.strip() or model_id == UNKNOWN:
        return UNKNOWN, None
    if model_id in OPUS_IDS or any(fnmatch.fnmatchcase(model_id, p) for p in OPUS_PATTERNS):
        return FLOOR, True
    for pattern, name in BELOW:
        if fnmatch.fnmatchcase(model_id, pattern):
            return name, False
    return UNKNOWN, None


def replay_model(environ=None):
    """The synthetic replay model id, or None outside the explicit test interface."""
    environ = os.environ if environ is None else environ
    if environ.get(REPLAY_FLAG) != "1":
        return None
    value = (environ.get(REPLAY_VAR) or "").strip()
    return value or None


def session_facts(resolved, environ=None):
    """{model, class, met, source} for the reviewing session, or raise FloorRefused."""
    model = (resolved.get("invocation") or {}).get("model")
    source = "the adapter's observed model (invocation.model.id)"
    if not isinstance(model, dict) or not model.get("id"):
        replay = replay_model(environ)
        if replay is None:
            raise FloorRefused(
                "the reviewing session's model is not established: the input carries no "
                "`invocation.model`, so the Opus-class floor (v1 Step 0) cannot be checked. The "
                "adapter's invocation helper observes it; a floor this run cannot establish is a "
                "stop, never an assumption. No reviewer is summoned and nothing is recorded.")
        model = {"id": replay, "floor_class": class_of(replay)[0], "floor_met": class_of(replay)[1]}
        source = "synthetic replay (%s under %s=1), never a live observation" % (REPLAY_VAR,
                                                                                REPLAY_FLAG)
    computed, met = class_of(model["id"])
    typed_class, typed_met = model.get("floor_class"), model.get("floor_met")
    if typed_class != computed or typed_met != met:
        raise FloorRefused(
            "the input's model facts disagree with its model id: %r is class %r (floor met: %s) "
            "by the floor map, and the input says class %r, floor met %r. A typed floor is never "
            "taken in place of the observed id; nothing is summoned and nothing is recorded."
            % (model["id"], computed, _word(met), typed_class, typed_met))
    if met is not True:
        raise FloorRefused(
            "the reviewing session runs %r, class %r: %s. Reviewers run at Opus-class or better "
            "(v1 Step 0); no reviewer is summoned from below the floor, no model is upgraded, and "
            "nothing is recorded."
            % (model["id"], computed, "below the floor" if met is False else
               "a floor this run cannot establish"))
    return {"model": model["id"], "class": computed, "met": True, "source": source}


def reviewer_facts(answer, session, environ=None):
    """{model, class, met, source} for the reviewer the answer names, or raise FloorRefused."""
    model = answer.get("model") if isinstance(answer, dict) else None
    source = "the readers result (the answer's model, readers' effective model)"
    if not isinstance(model, str) or not model.strip():
        replay = replay_model(environ)
        if replay is None:
            raise FloorRefused(
                "the reviewer's model is not established: the answer names no `model`, so the "
                "readers result that says which model reviewed is missing. The adapter's sidecar "
                "map supplies it (`answer_identity.model`); nothing is accepted without it.")
        model = replay
        source = "synthetic replay (%s under %s=1), never a live observation" % (REPLAY_VAR,
                                                                                REPLAY_FLAG)
    computed, met = class_of(model)
    if met is not True:
        raise FloorRefused(
            "the reviewer ran %r, class %r: %s. A verdict from below the Opus-class floor is never "
            "recorded (v1 Step 0)." % (model, computed, "below the floor" if met is False else
                                        "a floor this run cannot establish"))
    if session and model != session.get("model"):
        raise FloorRefused(
            "the reviewer's model %r disagrees with the model the session recorded, %r. A "
            "`claude-session` reader inherits the session's model, so the two facts must agree; "
            "the disagreement is refused rather than resolved." % (model, session.get("model")))
    return {"model": model, "class": computed, "met": True, "source": source}


def reported(session, reviewer=None, refused=None, resolved=None, answer=None):
    """The result's `floor` block. On a refusal the ids the run was given are still named."""
    session_model = (session or {}).get("model")
    if session_model is None and resolved is not None:
        session_model = ((resolved.get("invocation") or {}).get("model") or {}).get("id")
    reviewer_model = (reviewer or {}).get("model")
    if reviewer_model is None and isinstance(answer, dict):
        reviewer_model = answer.get("model")
    met = bool(session and session.get("met") and (reviewer is None or reviewer.get("met"))
               and not refused)
    return {
        "floor": FLOOR,
        "session_model": session_model,
        "reviewer_model": reviewer_model,
        "met": met,
        "source": "; ".join(s for s in ((session or {}).get("source"),
                                        (reviewer or {}).get("source")) if s) or None,
        "refused": refused,
    }


def _word(value):
    return {True: "yes", False: "no"}.get(value, "unknown")
