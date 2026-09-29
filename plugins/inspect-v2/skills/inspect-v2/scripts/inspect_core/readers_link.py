"""readers' roster, found by the shared resolver (contract section 6; slice 3a's design, section 5).

`packet` and `request` need to know whether the row the owner named is a Claude row (provider
`anthropic`) or an outside row, and `readers_request.build` needs the roster to decide
`authorized`. The roster is `<readers root>/skills/readers/assets/roster.json`, found by the one
resolver the four cores share, `station_core/readers_roster.py` (`find`, `load`):

    --readers-root   an explicit folder, taken only when its manifest names `readers` and the roster is there
    route 3a         `<plugin root>/../readers`, the checkout sibling, on the same test
    route 3b         `<plugin root>/../../readers/<version>`, the installed shape: the highest dotted
                     version whose folder name equals its manifest's `version`

Nothing found, or a roster that cannot be read, is this core's exit 3 (a missing dependency, like
the records component): the shared `RosterMissing` is caught and raised again as
`ComponentUnavailable`, one line on stderr naming every place looked. The script reads the roster
and never runs readers: the executor summons it (ruling E14-4).
"""
from station_core import readers_roster
from station_core.records_client import ComponentUnavailable


def resolve(plugin_root, argument=None):
    """{"root", "route", "roster", "looked"}; ComponentUnavailable (exit 3) naming every place looked."""
    try:
        return readers_roster.find(plugin_root, argument)
    except readers_roster.RosterMissing as exc:
        raise ComponentUnavailable(str(exc))


def load(plugin_root, argument=None):
    """(found, roster); ComponentUnavailable (exit 3) when nothing is found or the roster is unreadable."""
    try:
        return readers_roster.load(plugin_root, argument)
    except readers_roster.RosterMissing as exc:
        raise ComponentUnavailable(str(exc))


def provider(roster, row):
    for entry in (roster or {}).get("rows") or []:
        if isinstance(entry, dict) and entry.get("id") == row:
            return entry.get("provider")
    return None
