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

    When several elements tie on the label (a repeated control, or a seeded twin), the tie-break is
    D27's own order of what a store may lead with: the most PROVEN rungs (a recorded validation
    passed and none failed since), then the most live BRAIN-CARRIED rungs (D27a), then the most
    legacy live verdicts (`n_verified`), then the most recently seen. Until 2026-10-10 it ranked
    `n_verified` then `last_seen` alone, so a seeded brain twin -- newer, unproven -- outranked the
    element a v2 validation had proven, and 3 of 20 `[proven]` marks demoted on the seed dry run
    (docs/audit/pom-rebuild-2026-10-10.md, section 6). A record with no proven and no carried rung
    (every brain record) ranks exactly as it did."""
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
        ladder = el.get("ladder") or []
        pv = sum(1 for r in ladder if proven_passed(r))
        cv = sum(1 for r in ladder if carried_live(r))
        nv = sum(int(r.get("n_verified") or 0) for r in ladder)
        return (pv, cv, nv, el.get("last_seen") or "", eid)

    eid, el = sorted(pool, key=rank, reverse=True)[0]
    out = dict(el)
    out["_id"] = eid
    return out


def best_verified_rung(element: dict | None) -> dict | None:
    """The first ladder rung that has passed live at least once and did not fail last; None when
    the store holds the control but nothing verified -- the caller then drives live and reports
    `locator: live`, never a store rung it cannot vouch for (tri-state rule).

    A rung whose LAST VALIDATION FAILED (`proven_failed`, D27) is skipped here too: a recorded
    validation that said no is a newer and stronger fact than a live verdict that said yes. So is a
    brain-carried rung v2 DEMOTED (D27a: two clean failures) -- the same reasoning, one door over."""
    if not element:
        return None
    for r in element.get("ladder") or []:
        if proven_failed(r) or carried_demoted(r):
            continue
        if int(r.get("n_verified") or 0) > 0 and r.get("last_verdict") in ("VERIFIED-PASS", "PASS-GUARDED"):
            return r
    return None


# ------------------------------------------------------------- PROVEN BY A VALIDATION (D27, 2026-10-07)
# The user, 2026-10-07: "the full screenshot can validate steps success, the query if that was the
# value entered, or any other measure you can think of." A rung's `proven` block is written by
# `store.stamp_proven` and nothing else: every stamp names the validation that proved (or failed) the
# call, the run context and the time. `n_verified` above is a live VERDICT -- 819 of them on slockard,
# 26 with a read-back -- so "acted without an error" is what it mostly counts; `proven` is the fact.
def proven_passed(rung: dict | None) -> bool:
    """True when the rung's most recent validation PASSED."""
    p = (rung or {}).get("proven") or {}
    return p.get("result") == "pass" and int(p.get("n_pass") or 0) > 0


def proven_failed(rung: dict | None) -> bool:
    """True when the rung's most recent validation FAILED -- it is demoted until a newer one passes."""
    return ((rung or {}).get("proven") or {}).get("result") == "fail"


def best_proven_rung(element: dict | None) -> dict | None:
    """The rung a recorded validation proved and none has failed since: the most passes, then the most
    recent. None when no rung of this control was ever proven (or every proven one failed last)."""
    if not element:
        return None
    hits = [r for r in element.get("ladder") or [] if proven_passed(r)]
    if not hits:
        return None
    return max(hits, key=lambda r: (int(r["proven"].get("n_pass") or 0),
                                    str((r["proven"].get("last") or {}).get("at") or "")))


# ------------------------------------------------------------- BRAIN-CARRIED VERDICTS (D27a, 2026-10-10)
# The user, 2026-10-10: "The brain verdict should carry over to V2 ... If it's behind, if it doesn't have
# the same things that the brain allows it to operate with effectively, it's wrong by design." A rung the
# brain's consult rule calls verified (passed live, did not fail last) is SEEDED into v2's store with a
# `carried` block (store.carry_verdicts writes it and nothing else does): the brain's verdict frozen as it
# was carried -- {"from": "brain", "verdict", "n_verified", "n_failed", "date" (the rung's last live pass),
# "rung" (its rung key), "source" (partition, page key, element), "carried_at"}. It LEADS in v2 the way the
# brain's verified rung leads in the brain, until one of two newer facts ends it:
#   * `restamped` -- v2's first validation that PASSED on this call (store.stamp_proven writes it): D27's
#     rule from then on, the proof leads (basis `proven`), and a later failure demotes it as any proof;
#   * `demoted` -- TWO clean failures in v2 (store.record_lead_miss / store.stamp_proven count them): a
#     could-not-act miss counts only when the page key and state were confirmed, the readiness wait passed
#     and the control's own context was showing; a validation that ran and FAILED (a wrong value read back,
#     a SOQL mismatch, a judged screenshot) counts as it is (the call acted on that page and was judged).
# The carried verdict is read from the block alone, never from the rung's own counters, so a capture
# sighting v2 later merges onto the rung (a COULD-NOT-CHECK `last_verdict`) cannot silently drop it.
CARRIED_FROM = "brain"
#: two clean failures demote a carried verdict (D27a); one is recorded and the verdict keeps leading
CARRIED_DEMOTE_AFTER = 2
_LIVE_VERDICTS = ("VERIFIED-PASS", "PASS-GUARDED")


def carried_demoted(rung: dict | None) -> bool:
    """True when v2 demoted this brain-carried rung (two clean failures)."""
    return bool(((rung or {}).get("carried") or {}).get("demoted"))


def carried_live(rung: dict | None) -> bool:
    """True when this rung holds a brain-carried verdict that still LEADS: the brain called it verified when it was
    carried (passed live, did not fail last), v2 has neither re-stamped it with a validation nor demoted it."""
    c = (rung or {}).get("carried")
    if not isinstance(c, dict) or c.get("from") != CARRIED_FROM:
        return False
    if c.get("demoted") or c.get("restamped"):
        return False
    return c.get("verdict") in _LIVE_VERDICTS and int(c.get("n_verified") or 0) > 0


def best_carried_rung(element: dict | None) -> dict | None:
    """The first rung in ladder order whose brain-carried verdict still leads (`carried_live`) -- the brain's own
    `best_verified_rung` order, so v2 leads with the rung the brain would lead with. None when there is none."""
    if not element:
        return None
    for r in element.get("ladder") or []:
        if carried_live(r):
            return r
    return None


# --------------------------------------------------------------- which call cells are DATA (one list)
#: keywords whose SECOND positional cell is DATA a person supplied, not part of the locator.
#: Read from the installed QWeb source, not assumed: `type_text(locator, input_text, anchor…)`
#: (QWeb/keywords/input_.py:157), `click_checkbox(locator, value, anchor…)` (checkbox.py:33),
#: `drop_down(locator, option, anchor…)` (dropdown.py:32). The GarzAI one-step keywords take the
#: same shape (`PickList <label> <option>`, `Omni Select <label> <option>`, `Omni Date <key> <iso>`).
#: Moved here from consult.py (which re-exports it) so the store's proven-call identity reads the
#: SAME list: store.py imports this module and not consult.
VALUE_KEYWORDS = frozenset({
    "TypeText", "TypeSecret", "DropDown", "ClickCheckbox", "PickList", "ComboBox", "SetDate",
    "Omni Select", "Omni Type", "Omni Date", "Omni Radio", "Omni Checkbox", "Omni Lookup",
    "Aura PickList", "Aura Lookup", "Aura Date",
})
#: keywords whose cells after the locator are an EXPECTED value a verify compares against -- data too
#: (`VerifyField <label> <value>`, `VerifyInputValue <locator> <value>`), plus the setters a holder
#: names in its own words (`Type Text Clearing`, `Set Datetime`, `Multi Pick List`).
EXPECT_KEYWORDS = frozenset({
    "VerifyField", "VerifyInputValue", "VerifyCheckbox", "VerifyCheckboxValue", "VerifyPickList",
    "VerifyDropDown", "VerifyComboBox", "Type Text Clearing", "Set Datetime", "Multi Pick List",
    "Pick List Any",
})
#: compound setters: every keyword argument is a sub-field VALUE (`Set Address street= city=`).
COMPOUND_SETTERS = frozenset({"Set Address", "Set Name", "Multi Pick List"})


def flat_kw(kw: str | None) -> str:
    """A keyword name in one comparable form: `TypeText`, `type_text`, `Type Text` -> `typetext`."""
    return re.sub(r"[^a-z]", "", (kw or "").lower())


_DATA_FLAT = frozenset(flat_kw(k) for k in VALUE_KEYWORDS | EXPECT_KEYWORDS)
_COMPOUND_FLAT = frozenset(flat_kw(k) for k in COMPOUND_SETTERS)


def takes_data(kw: str | None) -> bool:
    """True when the cells after this keyword's locator are a value (typed, picked or expected)."""
    return flat_kw(kw) in _DATA_FLAT


def is_compound_setter(kw: str | None) -> bool:
    return flat_kw(kw) in _COMPOUND_FLAT
