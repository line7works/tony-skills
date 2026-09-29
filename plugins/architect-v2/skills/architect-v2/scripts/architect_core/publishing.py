"""The publish record (ruling E14-6, the second action): the `Artifact:` line, from the URL the
executor's publish returned. The script never publishes.

`decide(doc_text, publish, url)` -> {"outcome", "text", "changed", "reason", "refusal"}:

    publish false                  outcome `skipped`; the doc untouched
    publish true, no URL returned  outcome `rendered-not-published`; the doc untouched
    publish true, a URL            the doc records none: the `Artifact:` line is written below
                                   `Blind review:` (the header's order); it records the same URL:
                                   nothing changes; it records another: refused
                                   (`artifact-url-changed`), the doc untouched
"""
from . import docs

OUTCOMES = ("published", "skipped", "rendered-not-published")


def with_artifact(text, url):
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith("Blind review:"):
            return "\n".join(lines[:index + 1] + ["Artifact: %s" % url] + lines[index + 1:])
    raise ValueError("the doc has no 'Blind review:' line to place the Artifact line below")


def decide(doc_text, publish, url):
    recorded = docs.artifact_url(doc_text)
    if not publish:
        return {"outcome": "skipped", "text": doc_text, "changed": False, "refusal": None, "url": recorded,
                "reason": "the answer says publish: false; the publish step is skipped, nothing was published, "
                          "and the doc's Artifact: line is untouched"}
    if url is None:
        return {"outcome": "rendered-not-published", "text": doc_text, "changed": False, "refusal": None,
                "url": recorded,
                "reason": "the doc was rendered and not published: the publish returned no URL, so the doc's "
                          "Artifact: line is untouched"}
    if recorded and recorded != url:
        return {"outcome": None, "text": doc_text, "changed": False, "url": recorded,
                "refusal": {"rule": "artifact-url-changed",
                            "message": "the doc records the artifact %s; the publish returned %s. The same URL "
                                       "serves every run (the artifact tool's url parameter); nothing was written"
                                       % (recorded, url)},
                "reason": "refused"}
    if recorded == url:
        return {"outcome": "published", "text": doc_text, "changed": False, "refusal": None, "url": url,
                "reason": "published to %s, the URL the doc already records; the Artifact: line is unchanged" % url}
    return {"outcome": "published", "text": with_artifact(doc_text, url), "changed": True, "refusal": None, "url": url,
            "reason": "published to %s; the doc's Artifact: line now records it" % url}


def status_after(outcome):
    """The terminal status and reason `report` gives a run for its publish outcome: every outcome
    completes (a run that renders and does not publish ends in a named result, never a stop); only
    a review offer with no outcome stops a run, and that is `report`'s own check."""
    if outcome == "published":
        return "completed", "the architecture doc was written, its visual rendered and published"
    if outcome == "skipped":
        return "completed", "the architecture doc was written and its visual rendered; publish: false, so nothing was published"
    return "completed", ("the architecture doc was written and its visual rendered and not published: the publish "
                         "returned no URL")
