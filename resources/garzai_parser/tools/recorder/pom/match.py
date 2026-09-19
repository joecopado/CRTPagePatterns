"""match -- the ONE rule for "does the store already know this control?", shared by the interop
consult (up.py --op kw, parity plan phase 0) and the recorder's lookup-before-derive (phase 1).
Capability lookup 2026-09-15: pom_asset.consult answers per CAPTURE and ladders.lookup answers
per URL (page level, with a unique-label-only tolerant match); neither answers "this label, this
family, which verified rung" for a record already in hand, which is what a consult needs.

Usage (library):
    from pom.match import find_control, best_verified_rung, norm_label
    el = find_control(record, "Dependency Analysis", family="button")   # element dict or None
    rung = best_verified_rung(el)                                       # rung dict or None

The rule, in words: a control matches when its stored label equals the requested label after
normalisation (whitespace collapsed, case folded, a trailing live count such as "(2)" or "(9)"
dropped -- `Dependency Analysis (2)` and `Get Previously Commited (9)` are the same buttons as
their uncounted forms, measured 2026-09-15 on na.devops.copado.com) and, when a family is given,
its family is compatible (button/link/menuitem are one click family; input/textarea/combobox are
one type family). A stable attribute (aria-label, title, name, data-testid) equal to the label is
the second rung of the match; a prefix match is NEVER a match (`Save` must not find `Save & New`).

Nothing here touches disk or a browser; the caller passes the record it already read.
"""
from __future__ import annotations

import re

CLICK_FAMILIES = {"button", "link", "menuitem", "tab", "click", "a"}
TYPE_FAMILIES = {"input", "input_field", "textarea", "combobox", "text", "type", "search"}
_COUNT_SUFFIX = re.compile(r"\s*\(\d+\)\s*$")
_LABEL_ATTRS = ("aria-label", "title", "name", "data-testid", "data-test-id", "placeholder", "field-label")


def norm_label(s: str | None) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip().strip("*").strip()
    s = _COUNT_SUFFIX.sub("", s)
    return s.casefold()


def families_compatible(want: str | None, have: str | None) -> bool:
    if not want or not have:
        return True
    w, h = want.casefold(), have.casefold()
    if w == h:
        return True
    if w in CLICK_FAMILIES and h in CLICK_FAMILIES:
        return True
    if w in TYPE_FAMILIES and h in TYPE_FAMILIES:
        return True
    return False


def find_control(record: dict | None, label: str, family: str | None = None) -> dict | None:
    """The stored element whose label (rung 1) or stable label-like attribute (rung 2) equals
    `label` after normalisation, family-compatible with `family`. Exact only; None on a miss.
    When several elements tie on the label (a repeated control), the one with the most verified
    rungs wins, then the most recently seen."""
    if not record or not label:
        return None
    want = norm_label(label)
    if not want:
        return None
    elements = record.get("elements") or {}
    tier1, tier2 = [], []
    for eid, el in elements.items():
        if not families_compatible(family, el.get("family")):
            continue
        if norm_label(el.get("label")) == want:
            tier1.append((eid, el))
            continue
        attrs = el.get("attrs") or {}
        if any(norm_label(attrs.get(k)) == want for k in _LABEL_ATTRS if attrs.get(k)):
            tier2.append((eid, el))
    pool = tier1 or tier2
    if not pool:
        return None

    def rank(item):
        eid, el = item
        nv = sum(int(r.get("n_verified") or 0) for r in el.get("ladder") or [])
        return (nv, el.get("last_seen") or "", eid)

    eid, el = sorted(pool, key=rank, reverse=True)[0]
    out = dict(el)
    out["_id"] = eid
    return out


def best_verified_rung(element: dict | None) -> dict | None:
    """The first ladder rung that has passed live at least once and did not fail last; None when
    the store holds the control but nothing verified -- the caller then drives live and reports
    `locator: live`, never a store rung it cannot vouch for (tri-state rule)."""
    if not element:
        return None
    for r in element.get("ladder") or []:
        if int(r.get("n_verified") or 0) > 0 and r.get("last_verdict") in ("VERIFIED-PASS", "PASS-GUARDED"):
            return r
    return None
