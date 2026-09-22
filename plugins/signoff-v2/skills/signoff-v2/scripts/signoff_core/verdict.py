"""Severity to verdict, and the card the verdict sets.

v1 signoff's table, carried over word for word under pick P5 (review policy unchanged):

| BLOCKER | spec requirement unmet, or a defect that loses data, corrupts state, or breaks a
            shipped feature | cannot sign |
| MAJOR   | real defect with a concrete failure path, contained and fixable in place | conditional |
| MINOR   | rough edge, missing guard, thin test | punch list only |

- SIGNED OFF              no BLOCKER and no MAJOR
- SIGNED OFF WITH CONDITIONS  no BLOCKER; named MAJORs must be fixed before the next slice
- REJECTED                one or more BLOCKERs

The mapping runs over the findings the run RAISED. A note is not a finding and never moves the
verdict. The mapping is arithmetic over severities, not a judgement about code, so the core
computes it; what the reviewer stated is recorded beside it and a disagreement is reported.

The card carries the same three values into the build doc's `Status:` line, which is v1's
one-word state flag for the next build's preflight. A slice at `built` is moved by this station,
because a review is exactly the event that takes it off `built`.
"""
from .constants import (VERDICT_REJECTED, VERDICT_SIGNED_OFF, VERDICT_WITH_CONDITIONS)


def verdict_for(severities):
    """The verdict the severities of the raised findings produce."""
    severities = list(severities)
    if "BLOCKER" in severities:
        return VERDICT_REJECTED
    if "MAJOR" in severities:
        return VERDICT_WITH_CONDITIONS
    return VERDICT_SIGNED_OFF


def card_for(verdict):
    """The `Status:` value the verdict sets. The three verdict words are the three card words."""
    return verdict


def counts(severities):
    out = {"BLOCKER": 0, "MAJOR": 0, "MINOR": 0}
    for severity in severities:
        if severity in out:
            out[severity] += 1
    return out
