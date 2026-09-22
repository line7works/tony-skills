# A rendered review block

What `records.py render --run-id signoff-2026-04-01-widget-a` returns under `review` for
a run that raised two findings against one slice (E13 amendment A4). It is the text a
station appends at the ledger home's tail, and
`import-report/valid/import-nothing-new-native.json` is the report the next
`import-legacy --dry-run` prints over the document holding it: nothing new, and three
lines recognised as the rendering of native events (these two and the `Status:` line the
run's `card_set` moved).

```text
### 2026-04-01 — review: Slice A
- BLOCKER · src/widget.py:88 · (the retry loop never ends) · it spins forever · A
- BLOCKER · src/widget.py:3 · (the gauge never resets) · a second call reads the value the first left · A
```

Read back by this component's own reader, each line is a `finding` whose section 7
identity is the finding id its native event carries; `render`'s `review_slices` names
one block per slice, because Appendix A's review heading names one slice.
