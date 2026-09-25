"""inspect-v2's own library (E14 slice 2, lane I): the plan check's deterministic half.

Not shared with the other front cores (`station_core/` is the shared library). The phase driver
`scripts/inspect_v2.py` wires these modules into `station_core.driver.main`:

    common          the run, its phases, the clock, the artifacts
    readers_link    readers' roster, found the records way (route 3a, then 3b)
    gate            `choose` and `harvest`: the documents, the code book, the records component
    packet          `packet`: one fresh numbered directory per lens; the three-file rule
    request         `request`: one readers request per lens, the mandates verbatim
    mandates        the fixed mandates, v1's byte for byte
    verify          verify and adjudicate, mechanically: citations, the no-record rule, the verdict
    answering       `record-answer`: the schema, the shared E14-11 refusals, this core's own
    writing         `write`: the records append, the block, the station's own lines, the mirror
    reporting       `report` and every terminal stop: the result, validated, and the chat block

The references are `references/inspect-v2-contract.md` (what each phase does) and
`references/station-loop.md` (what every front core shares).
"""
