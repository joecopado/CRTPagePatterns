"""index -> QWeb's numeric anchor: the ONE place a described position becomes a real argument.

D14, 2026-09-09 (docs/DECISIONS.md; user: "the hints are more detrimental than your independent
judgements at run time"). The parser DESCRIBES: for a control whose label repeats it reports
`disambiguation.index` -- this member's 1-based position among the same-label matches in DOM
order -- and lists the anchor texts the page offers as `anchor_candidates`. It bakes no anchor,
because a text anchor chosen from a static capture was measured resolving the WRONG live element:
docs/errors/entries/7627c1f2a9.json (slockard Zoo_Forms_Advanced, two 'Deal Name' members with
different "confirmed-unique" anchors, both resolved by QWeb's proximity scorer to one field, and
the second type_text_clearing appended instead of clearing).

The EXECUTOR prescribes. Read from the installed QWeb source, not assumed: `click_text`
(QWeb/keywords/text.py:357), `click_item` (:929) and every text-resolving keyword take
`anchor: str = "1"` and NO `index` parameter -- the docstring calls anchor "Text near the element
to be clicked **or index**", so a NUMERIC anchor IS index mode and counts from 1. An `index=`
kwarg reaching a real keyword would be swallowed into **kwargs and silently ignored, which is the
green-signal failure this codebase is named for.

So every path that turns a rung into a call routes its kwargs through `to_call_kwargs` here:
`tools/recorder/player.py` (`_coerce_rf_kwargs`, the local/QWeb execution path) and
`tools/recorder/writer.py` (`_kwargs_suffix`, the Robot export path). One implementation, so the
two can never drift onto different spellings of the same position.
"""
from __future__ import annotations

# The kwarg the parser and the POM ladder describe a position with.
INDEX_KWARG = 'index'
# The kwarg QWeb actually accepts. A numeric value is its index mode.
ANCHOR_KWARG = 'anchor'


def to_call_kwargs(kwargs: dict) -> dict:
    """Return `kwargs` with a described `index` rewritten to QWeb's numeric `anchor`.

    * `index` absent            -> unchanged (a control that occurs once carries neither).
    * `index` present, no anchor-> `anchor="<n>"`, the string QWeb's index mode expects.
    * both present              -> the explicit `anchor` WINS and `index` is dropped: a caller
      that chose an anchor candidate has made the decision the hint deliberately did not, and
      two disambiguators is a call QWeb cannot parse.
    * a non-positive or non-integer `index` -> dropped, never emitted as a bogus anchor.
    """
    out = dict(kwargs or {})
    idx = out.pop(INDEX_KWARG, None)
    if idx is None:
        return out
    if out.get(ANCHOR_KWARG) not in (None, ''):
        return out
    try:
        n = int(str(idx).strip())
    except (TypeError, ValueError):
        return out
    if n < 1:
        return out
    out[ANCHOR_KWARG] = str(n)
    return out
