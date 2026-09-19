"""
Usage: python3 tools/qforce-lite/chains.py [-h] [--explain [TYPE]] [--store STORE] [--tally]
chains -- per-TYPE self-healing fallback chains for qforce-lite.

THE IDEA (the user's words): "Create infallible chains to improve and reduce need for scans."

`docs/crt-train/POLYMORPHISM.md` is what makes that tractable. describe type -> rendered control
is one-to-one per sub-kind inside the LWC surface family, so a fallback chain can be written ONCE
PER TYPE and applies to every field of that type on every object -- instead of once per field,
forever. A POM caches instances; this caches the rule.

WHAT THIS ADDS THAT qforce_lite.py DOES NOT ALREADY HAVE
--------------------------------------------------------
`qforce_lite._field_xpath_chain()` is an ordered A->B->C chain for READING a record-page field.
That is the shape. Every SETTER in qforce_lite.py -- type_text_clearing, pick_list, combo_box,
click_checkbox, pick_date -- has exactly ONE mechanism plus a repair path for that one mechanism.
None has an ordered list of ALTERNATIVE mechanisms. This module is that list, per type, plus the
thing that makes it a chain rather than a pile: after every mechanism it VERIFIES BY READ-BACK
and only counts a mechanism as having worked if the value it asked for is the value the page
now holds.

    A mechanism that "ran" is not a mechanism that worked. That distinction is this whole file.

THREE RULES THIS FILE ENCODES STRUCTURALLY, NOT AS COMMENTS
-----------------------------------------------------------
1. ORDER IS QForce -> QWeb -> ours. Behaviour stays portable to a real CRT suite and only
   degrades deliberately. `test_chains.py::test_origin_order_is_qforce_then_qweb_then_ours`
   fails the build if a chain ever puts one of ours ahead of a portable rung.
2. VERIFY BY READ-BACK, ALWAYS. Each type declares a verifier; `set_field` runs it after every
   mechanism, and the mechanism's own "no exception raised" is never the signal.
3. TRI-STATE. true / false / COULD-NOT-CHECK. A read-back that returns None is not a pass and
   not a miss -- it advances the chain and, if every rung ends that way, `set_field` raises
   `CouldNotCheck`. It never returns success on an unverifiable set.

THE SELF-HEALING PART
---------------------
Every completed walk appends one JSON line to ~/.claude/state/chain-wins.jsonl recording which
mechanism won, which ones missed and why, and WHICH VERIFIER proved it. On the next call for
that type, the last winner is tried FIRST (the rest keep their canonical order). A promoted
winner that then fails simply falls through and the new winner is recorded, so the record
self-corrects rather than pinning a stale choice.

Deliberate limits on that promotion, because a cache of "what worked" is one bad line away from
being a cache of "what looked like it worked":
  * A win is only recorded when a verifier RETURNED TRUE. Could-not-check never writes a win.
  * The verifier's name is stored with the win. A win proved by a weak verifier is not
    interchangeable with one proved by a strong one, and the log says which you have.
  * Promotion reorders; it never removes a rung and never skips verification.
  * A `degrades=True` rung (one that lands the value by a path a real user could not take) is
    recorded with that flag. A type that keeps winning there is a signal to go fix rungs 1-2,
    not a success.

WHAT IS PROVEN OFFLINE AND WHAT IS NOT
--------------------------------------
This module was built and tested WITHOUT a browser (another agent owns the live session this
round). `test_chains.py` proves, against a REAL captured DOM
(docs/dom-captures/04-account-new-record-modal.html, an Account create modal):
  * the type->control polymorphism holds on that capture for picklist / reference / textarea /
    string, so the per-type chain is being dispatched on the right thing;
  * the read-back TARGET each verifier needs actually exists in the DOM before the interaction
    (this is what makes verification possible at all -- see PICKLIST_READBACK below);
  * the chain walk itself: fall-through on a miss, no-win on a silent no-op, exhaustion,
    could-not-check, win recording, and promotion on the next call.
It does NOT prove that any individual mechanism drives a real page. The live rungs in
`LiveBackend` are transcribed from mechanisms qforce_lite.py already measured live, but their
behaviour AS CHAIN RUNGS is UNTESTED-LIVE. `docs/crt-train/CHAINS.md` carries the exact live
test to run and keeps the two columns separate.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# text_match is a pure module (no selenium, no QWeb) -- see its own header. Importing it here
# keeps ONE comparator for "did the value land", the one that already knows a numeric field
# reformats on blur ("25000" -> "25,000.00") without rescuing "202,525%".
try:
    from text_match import needs_retype_repair
except ImportError:  # pragma: no cover -- imported by path from outside this directory
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "qfl_text_match", os.path.join(os.path.dirname(os.path.abspath(__file__)), "text_match.py"))
    _tm = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_tm)
    needs_retype_repair = _tm.needs_retype_repair


# =========================================================================== outcomes

WIN = "WIN"
MISS = "MISS"
COULD_NOT_CHECK = "COULD-NOT-CHECK"
SKIPPED = "SKIPPED"

ORIGIN_RANK = {"QForce": 0, "QWeb": 1, "ours": 2}


class ChainError(ValueError):
    """Base for every way a chain walk can end without a proven set."""


class ChainExhausted(ChainError):
    """Every runnable mechanism was tried and none of them landed the value.

    Carries the per-rung reasons, because "PickList failed" sends you into the library and
    "rung 1 opened the dropdown but the option was not in it, rung 2 same, rung 3 found no
    [role=option] nodes at all" sends you at the org's picklist values -- which is where the
    answer was, measured 2026-08-30.
    """


class CouldNotCheck(ChainError):
    """The value may or may not have landed; no rung could be verified either way.

    This is the third state, kept separate on purpose. Letting it collapse into success is the
    shared root of every bug in confirm.py's header.
    """


class NoChainForType(ChainError):
    """This type/sub-kind has no chain, and guessing one would be a fabrication.

    Raised for the cases POLYMORPHISM.md measured as genuinely different: the three non-plain
    `reference` sub-kinds (Owner / audit / RecordTypeId render as different tags entirely, see
    REFERENCE_SUBKINDS below -- still could-not-check, no keyword exists for any of them) and any
    non-LWC framework surface.

    NOT raised for multipicklist any more (BACKLOG row 68, KEYWORDS-BY-FIELD.md SS2.9's "Code/spec
    disagreement, named not patched"): that refusal was written when multipicklist genuinely had
    no keyword and no reachable field to test. Both are now stale --
    keywords_multipicklist.multi_pick_list exists, is live-proven (2/2 in, 1/1 back out, SOQL
    read-back on a saved record, dev1 a4SWC00000BfzHJ2AZ), and predict.type_to_keyword already
    routes to it. MULTIPICKLIST below is that chain, so chain_for() now agrees with predict.py
    instead of contradicting it.
    """


# =========================================================================== mechanisms

@dataclass(frozen=True)
class Mechanism:
    """One way to set a field, plus the measurement that put it at this position.

    `id`         stable key; also the LiveBackend/FixtureBackend method name suffix, and the
                 key the win log is written under. Never rename without migrating the log.
    `origin`     'QForce' | 'QWeb' | 'ours'. Enforces the portability order (rule 1 above).
    `why`        the MEASUREMENT that justifies this rung's existence and position. Not a
                 rationale -- a citation. test_chains.py fails a rung whose `why` carries no
                 date or doc reference, because this file's whole value is that its ordering is
                 evidence and not taste.
    `degrades`   True if the rung lands the value by a path a real user could not take. Still a
                 legitimate rung; recorded with the flag so it can never be mistaken for a
                 clean pass.
    `last_resort` True if the rung must never run automatically -- it needs an argument the
                 caller has to supply (a reference image), or it has never been run at all.
                 Pinned to the tail and excluded from the origin-order check, because the
                 ordering rule is about which PORTABLE mechanism to reach for first, and a
                 gated rung is not in that race.
    `requires`   argument names the caller must supply before this rung can run.
    `locate_only` True if the rung can only FIND the control, not set it -- it hands off to the
                 preceding rung. An honest label: a template-image match cannot type.
    """
    id: str
    origin: str
    why: str
    degrades: bool = False
    last_resort: bool = False
    requires: Tuple[str, ...] = ()
    locate_only: bool = False

    def __post_init__(self):
        if self.origin not in ORIGIN_RANK:
            raise ValueError("unknown origin %r for mechanism %r" % (self.origin, self.id))


# --------------------------------------------------------------------------- the last rung
#
# CORRECTION, measured 2026-08-29 on this machine. The brief for this work, and
# docs/crt-train/QFORCE-KEYWORD-INVENTORY.md, both describe QWeb's `recognition_mode=vision` as
# a verified-present, DOM-independent last resort. Against the QWeb source tree available here
# (~/.claude/jobs/57acaac4/tmp/qweb/QWeb), `grep -rn "recognition_mode\|vision"` over every .py
# returns ZERO hits -- there is no such config key and no such mode.
#
# What DOES exist, and is genuinely DOM-independent, is QWeb/keywords/icon.py:
#     ClickIcon(image, template_res_w=None, browser_res_w=None, tolerance=0.95, grayscale=True)
#     IsIcon / VerifyIcon / CaptureIcon
# -- screen template matching against a reference bitmap. So the last rung of every chain below
# is ClickIcon, not a vision mode.
#
# That changes its character, and the change is the point: ClickIcon needs a PRE-CAPTURED
# REFERENCE IMAGE, so it can never be a blind automatic fallback. It is `last_resort=True,
# requires=("image",)` everywhere and is skipped unless the caller passes one.
#
# Honest scope: no QForce package is installed on this machine (nothing named QForce under
# /Users/jgarza), so the inventory's own claim -- which was mined from QConnect's compiled
# QForce, not from QWeb -- is COULD-NOT-CHECK here rather than refuted. What is refuted is
# "verified present in the [QWeb] package".
_ICON = Mechanism(
    id="qweb_clickicon_template",
    origin="QWeb",
    why=("DOM-independent screen template match. Measured 2026-08-29 in the QWeb source on this "
         "machine: no recognition_mode / 'vision' exists anywhere (grep over all .py = 0 hits); "
         "keywords/icon.py ClickIcon(image, tolerance=0.95, grayscale=True) is the real "
         "DOM-independent surface. Needs a pre-captured reference image, so it is gated behind "
         "an explicit image= argument and never runs automatically."),
    last_resort=True,
    requires=("image",),
)


PICKLIST: Tuple[Mechanism, ...] = (
    Mechanism(
        id="qforce_picklist",
        origin="QForce",
        why=("The portable rung: QForce's own PickList, which qforce_lite.pick_list reimplements "
             "keyword-for-keyword. Its trigger click is js=True because a plain Selenium click "
             "inside a record modal hit-tests onto the records-modal-lwc-detail-panel-wrapper "
             "shadow host instead of the button and the option list never renders -- measured "
             "live 2026-08-26, document.activeElement was the wrapper and 0 [role=option] nodes "
             "existed (qforce_lite.py::pick_list)."),
    ),
    Mechanism(
        id="qweb_clickitem_shadow",
        origin="QWeb",
        why=("Real QWeb ClickItem under SetConfig ShadowDOM True, on an ALREADY-OPEN trigger. "
             "Measured live 2026-08-26: the option's title-bearing span sits at composed depth 11 "
             "inside lightning-base-combobox-item's own shadow root, so driver.find_elements(By."
             "XPATH) -- what click_element does for a bare xpath -- crosses no boundary and finds "
             "0; ClickItem's get_recursive_walk does and finds it. Kept as its own rung because "
             "rung 1 can fail for a reason of its own making: its retry loop re-clicks the "
             "trigger, and a re-click TOGGLES AN OPEN DROPDOWN CLOSED (qforce_lite.py::"
             "_picklist_trigger_expanded)."),
    ),
    Mechanism(
        id="qweb_dropdown_native",
        origin="QWeb",
        why=("QWeb DropDown against a real <select>. On LEX this fails instantly and costs "
             "nothing: measured 2026-08-29 over docs/dom-captures/04-account-new-record-modal."
             "html, 0 <select> elements exist. It is here because Visualforce renders a REAL "
             "<select> and DropDown is the right first choice there (sf-metadata-locators SS5), "
             "and a chain written per TYPE has to survive meeting that type on another surface."),
    ),
    Mechanism(
        id="ours_js_option_click",
        origin="ours",
        why=("Composed-tree walk following every open shadowRoot for [role=option] or "
             "lightning-base-combobox-item whose title equals the value, then a JS "
             "element.click() -- no coordinate hit-test, no QWeb resolution. Ours, so it is the "
             "last automatic rung: it is the one that survives a changed tag vocabulary (Task's "
             "Aura Activity Composer renders picklists as bare div/ul/a[role=combobox] with no "
             "lightning-* tag at all, POLYMORPHISM.md SS2/SS3) but it is not portable to a CRT "
             "suite written in plain keywords."),
    ),
    _ICON,
)


REFERENCE: Tuple[Mechanism, ...] = (
    Mechanism(
        id="qforce_combobox",
        origin="QForce",
        why=("QForce ComboBox as qforce_lite.combo_box implements it, including two measured "
             "corrections it already carries: (a) JS focus BEFORE typing, because Selenium's "
             "click resolves onto a wrapper and the SERVER-SIDE search then never fires -- "
             "measured live 2026-08-30, 6 listboxes present, 0 formatted-text items, and no "
             "'no results' text either; (b) a same-locator retry, because CDP network capture "
             "(round 8, 2026-08-30/31) shows every SUCCEEDING call gets a delayed 'encore' "
             "request repeating the full string ~1.1s after the 22-request keystroke burst and "
             "every FAILING call gets only the burst (n=3); the retry makes the encore fire, "
             "7/7."),
    ),
    Mechanism(
        id="qweb_show_all_results",
        origin="QWeb",
        why=("ClickText('Show All Results for \"X\"') then pick the row by "
             "th[@data-cell-value=\"X\"]/../td//input -- a DIFFERENT render surface for the same "
             "server-side search, already implemented as qforce_lite.py::combo_box("
             "all_results=True). Rung 2 rather than rung 1 because it still depends on that "
             "search having fired at all, which is exactly what rung 1's JS-focus fix (measured "
             "live 2026-08-30) exists to guarantee."),
    ),
    Mechanism(
        id="ours_focus_retype_encore",
        origin="ours",
        why=("The encore-forcing retry, unbundled from rung 1 and issued against the "
             "ALREADY-RESOLVED element. Measured round 8 (2026-08-30/31, qforce_lite.py::combo_box): "
             "a naive retry that re-searches the "
             "label string hits a different failure 1/3 runs -- a failed first attempt leaves an "
             "inline validation message containing the same label substring ('Account NameSelect "
             "an option from the picklist...'), so QWeb's label search then has two candidates "
             "instead of one and reports 'Unable to find element for locator *Account Name in "
             "20.0 sec'."),
    ),
    Mechanism(
        id="ours_js_option_click",
        origin="ours",
        why=("Same shadow-piercing composed walk as the picklist chain's rung 4, over the "
             "lookup's rendered result list. Measured 2026-08-29 on the real create-modal "
             "capture: the lookup's own control is an input[role=combobox] at composed shadow "
             "depth 10 and NOT inside a native shadow root, so a composed walk reaches it and a "
             "light-DOM querySelectorAll does not."),
    ),
    _ICON,
)


MULTIPICKLIST: Tuple[Mechanism, ...] = (
    Mechanism(
        id="qforce_multi_pick_list",
        origin="QForce",
        why=("QForce ships MultiPickList (6 occurrences via `strings` over the compiled package, "
             "QFORCE-KEYWORD-INVENTORY.md); keywords_multipicklist.multi_pick_list reimplements it "
             "keyword-for-keyword against the real lightning-dual-listbox DOM and needs NONE of "
             "pick_list's ShadowDOM-config/js=True dance -- a plain, non-JS `.click()` on a "
             "[role=option] div and a plain `driver.find_elements(By.XPATH, ...)` on the Move "
             "button both reach it directly (keywords_multipicklist.py header, measured live). "
             "Move mechanics measured, not guessed: one click selects exactly one option (single- "
             "select semantics for the click itself), so multi-select is achieved by moving items "
             "one at a time -- confirmed 2/2 in (Sales, then Trainer), 1/1 back out, and an "
             "end-to-end SOQL read-back on a saved record (SDO_Experience_Role__c='Sales', dev1 "
             "a4SWC00000BfzHJ2AZ, kept per the records-stay rule). This is rung 1 because it IS "
             "the portable QForce-equivalent rung, not a degraded stand-in for one."),
    ),
    _ICON,
)


# textarea and the string family share their setter mechanisms exactly -- what differs is the
# rendered tag (lightning-textarea vs lightning-input, POLYMORPHISM.md SS2) and, for the string
# family, that a numeric sub-type REFORMATS ON BLUR, which the verifier already handles.
def _text_family(kind: str) -> Tuple[Mechanism, ...]:
    return (
        Mechanism(
            id="qweb_type_text_clear_key",
            origin="QWeb",
            why=("Real QWeb type_text with clear_key='{CONTROL + a}' -- QWeb's own documented fix "
                 "for a pre-populated Lightning input, and the only portable rung. It is rung 1 "
                 "because it is still correct for most fields, and it is not the ONLY rung "
                 "because it measurably is not enough: 2026-07-29, a percent-formatted numeric "
                 "field grew 25%% -> 2,025%% -> 202,525%% across repeated attempts WITH clear_key "
                 "applied (qforce_lite.py::type_text_clearing)."),
        ),
        Mechanism(
            id="ours_js_focus_send_keys",
            origin="ours",
            why=("JS .focus() then .clear() + .send_keys() + .blur(). Measured live 2026-08-30 on "
                 "a real New Account form, three mechanisms against the SAME resolved, visible, "
                 "enabled input: .click()+send_keys left the field '' (silent failure); JS "
                 ".focus()+send_keys landed the value. Selenium's .click() does not give a "
                 "Lightning input focus -- the click resolves onto a wrapper -- so every "
                 "keystroke went nowhere while the keyword reported success."),
        ),
        Mechanism(
            id="ours_native_value_setter",
            origin="ours",
            degrades=True,
            why=("The native HTMLInputElement/HTMLTextAreaElement value setter plus synthetic "
                 "input+change events. Measured 2026-08-30 in the same three-way comparison: the "
                 "value lands, AND it bypasses the keyboard path, so Lightning's own keydown "
                 "formatting never runs -- a phone or currency field can end up holding a string "
                 "a real user could not have produced. Marked degrades=True: a %s field that "
                 "keeps winning here is a signal to go look at rungs 1-2, not a pass." % kind),
        ),
        Mechanism(
            id="qweb_clickicon_template",
            origin="QWeb",
            why=_ICON.why + (" For a text field this rung can only LOCATE the control, never type "
                             "into it -- it hands the located element back to rung 2. Labelled "
                             "locate_only so it can never be recorded as having set anything."),
            last_resort=True,
            requires=("image",),
            locate_only=True,
        ),
    )


TEXTAREA: Tuple[Mechanism, ...] = _text_family("textarea")
STRING: Tuple[Mechanism, ...] = _text_family("string-family")


BOOLEAN: Tuple[Mechanism, ...] = (
    Mechanism(
        id="qforce_click_checkbox",
        origin="QForce",
        why=("QForce ClickCheckbox as qforce_lite.click_checkbox implements it: no-op if already "
             "in the target state, and resolve the REAL input through the label's for= attribute "
             "first. Measured live 2026-07-29 -- this keyword only ever worked on table-row "
             "checkboxes; passing a standalone Lightning checkbox FIELD's label straight to "
             "get_webelement matched the <label> node itself and raised "
             "QWebElementNotFoundError."),
    ),
    Mechanism(
        id="qweb_click_faux_span",
        origin="QWeb",
        why=("Click the SLDS decorative sibling span (slds-checkbox_faux) rather than the input. "
             "This project's own capture-mining, 2026-07-27: the real clickable target of an SLDS "
             "checkbox is that decorative sibling, because the input itself is visually hidden."),
    ),
    Mechanism(
        id="ours_click_label_ancestor",
        origin="ours",
        why=("Click the input's ancestor <label>, which the browser forwards to the control. "
             "Already present as click_checkbox's second fallback (qforce_lite.py::"
             "click_checkbox); promoted to a named rung so a miss here is recorded rather than "
             "silently swallowed by a bare except."),
    ),
    Mechanism(
        id="ours_js_set_checked_dispatch",
        origin="ours",
        degrades=True,
        why=("Set .checked and dispatch a synthetic change event. Lands the state and bypasses "
             "the click path entirely -- same trade as the text family's native value setter, "
             "and already qforce_lite.py::click_checkbox's last fallback (measured 2026-07-29). "
             "degrades=True for the same reason."),
    ),
    _ICON,
)


DATE: Tuple[Mechanism, ...] = (
    Mechanism(
        id="qweb_type_text_date",
        origin="QWeb",
        why=("TypeText with a locale-formatted date string. Portable, and measured working "
             "(tools/qforce-lite/predict.py maps date/datetime to type_text_clearing, 'verified "
             "working today'). It is rung 1 by the portability rule and it is NOT obviously the "
             "right rung 1: it never exercises the calendar widget, and it is locale-dependent "
             "in an org already measured to render non-English option labels (Salutation came "
             "back as Sr./Srta./Sra./Dr./Prof., 2026-08-26). The win log is what settles that "
             "argument with data instead of opinion -- see docs/crt-train/CHAINS.md."),
    ),
    Mechanism(
        id="ours_calendar_widget",
        origin="ours",
        why=("qforce_lite.pick_date: focus the input to open the popup, read the popup's OWN "
             "displayed month/year rather than assuming today's, then click "
             "td[@data-value='YYYY-MM-DD']. Confirmed live 2026-08-31 that Lightning's day cells "
             "carry the exact ISO date as an attribute, so nothing is computed or guessed, and "
             "the keyword returns the ISO date it actually clicked so the caller asserts against "
             "the click rather than against a re-derived date."),
    ),
    Mechanism(
        id="ours_native_value_setter",
        origin="ours",
        degrades=True,
        why=("Native value setter + synthetic events, exactly as in the text family (measured "
             "2026-08-30, qforce_lite.py::type_text_clearing). For a date "
             "field this is the most degrading rung in the file: it writes a string into a "
             "control whose whole job is to normalise one, so Lightning's own parse never runs."),
    ),
    _ICON,
)


CHAINS: Dict[str, Tuple[Mechanism, ...]] = {
    "picklist": PICKLIST,
    "reference": REFERENCE,
    "textarea": TEXTAREA,
    "string": STRING,
    "boolean": BOOLEAN,
    "date": DATE,
    "multipicklist": MULTIPICKLIST,
}


# =========================================================================== type dispatch
#
# POLYMORPHISM.md SS2, verbatim: nine describe types collapse onto ONE rendered tag
# (lightning-input), and "describe type (not the DOM) is what tells you which keyword". So the
# dispatch below is deliberately keyed on the describe type, never on what was found on the page.
TYPE_ALIASES: Dict[str, str] = {
    "picklist": "picklist",
    "reference": "reference",
    "textarea": "textarea",
    "boolean": "boolean",
    "date": "date",
    "datetime": "date",
    # the string family: all nine of these render as lightning-input and take the same setter
    "string": "string",
    "phone": "string",
    "email": "string",
    "url": "string",
    "double": "string",
    "currency": "string",
    "percent": "string",
    "int": "string",
    "address": "string",   # compound: N lightning-input sub-fields, addressed by SUB-label
    "multipicklist": "multipicklist",
}

# Sub-kinds of `reference` that are NOT the plain lookup. POLYMORPHISM.md SS2's single most
# valuable Round 9 result: `reference` is not one-to-one, it renders FOUR ways, and which one is
# decided by the field's API NAME, not its type.
#
# BACKLOG row 70 / KEYWORDS-BY-FIELD.md SS2.11's "Code/spec disagreement, named not patched":
# predict.type_to_keyword used to map every `reference` straight to combo_box regardless of
# api_name, while chain_for() below refused these three -- two routers, two answers, both about
# the same fact. This table is now the ONE place that fact lives; predict.py imports it
# (`from chains import REFERENCE_SUBKINDS`) instead of keeping a second copy that can drift.
#
# Every sub-kind here is COULD-NOT-CHECK, not "unsupported" -- and the reason differs per kind:
#   OwnerId                     renders a DIFFERENT tag (force-owner-lookup); no keyword exists to
#                                drive it yet, so combo_box would resolve nothing and the failure
#                                would read as a locator bug rather than an unbuilt keyword.
#   CreatedById/LastModifiedById renders read-only, always -- there is nothing to set, so
#                                could-not-check here means "this is an output-only field",
#                                not "we failed to test it".
#   RecordTypeId                 is not a lookup at all -- it is a record-type-selection MODAL
#                                (or plain text when the object has one record type), its own
#                                interaction, never combo_box.
# Encoded as a refusal rather than a comment in chain_for(), because the failure it prevents
# ("combo_box found nothing on OwnerId") looks like a locator bug and is not one.
REFERENCE_SUBKINDS: Dict[str, str] = {
    "OwnerId": ("renders as force-owner-lookup, not lightning-grouped-combobox, on EVERY object "
                "(POLYMORPHISM.md SS2). There is no keyword for it yet -- combo_box will find "
                "nothing and the failure will read as a locator bug."),
    "CreatedById": ("renders as force-lookup and is ALWAYS read-only -- output only, there is "
                    "nothing to set (POLYMORPHISM.md SS2)."),
    "LastModifiedById": ("renders as force-lookup and is ALWAYS read-only -- output only "
                         "(POLYMORPHISM.md SS2)."),
    "RecordTypeId": ("renders as records-record-type, or as plain output text when the object has "
                     "one record type (POLYMORPHISM.md SS2). Not a lookup; setting it is a "
                     "record-type-selection modal, which is its own interaction."),
}
# Backward-compatible alias -- kept in case anything outside this file still imports the old
# private name during the transition.
_REFERENCE_SUBKINDS = REFERENCE_SUBKINDS


def chain_for(field_type: str, api_name: Optional[str] = None,
              framework: str = "lwc") -> Tuple[Mechanism, ...]:
    """The canonical (un-promoted) chain for a describe type. Raises NoChainForType rather than
    guessing, for every case POLYMORPHISM.md measured as genuinely different."""
    ft = (field_type or "").strip()

    if framework and framework.lower() != "lwc":
        raise NoChainForType(
            "framework=%r: these chains are measured on LWC's lightning-record-edit-form only. "
            "POLYMORPHISM.md SS3 -- Task's /edit URL opens the classic Aura Activity Composer, a "
            "completely different tag vocabulary for the same describe types (picklists render as "
            "bare div/ul/a[role=combobox], Description as a bare <textarea>). Event shares that "
            "family and has not been checked. COULD-NOT-CHECK, not 'probably fine'." % framework)

    key = TYPE_ALIASES.get(ft)
    if key is None:
        raise NoChainForType(
            "no chain for describe type %r. It is not in POLYMORPHISM.md's measured table, and a "
            "chain invented for it would be exactly the plausible-looking wrong answer this "
            "codebase exists to prevent." % field_type)

    if key == "reference" and api_name in REFERENCE_SUBKINDS:
        raise NoChainForType(
            "%s is a `reference` field but not a plain lookup: it %s" %
            (api_name, REFERENCE_SUBKINDS[api_name]))

    return CHAINS[key]


# =========================================================================== verification
#
# Each type declares HOW a set is proven. The verifier is given what the caller asked for and
# what the backend read back, and returns True (proven) or False (contradicted). The backend
# returning None is COULD-NOT-CHECK and never reaches a verifier.
#
# READ-BACK TARGETS, MEASURED OFFLINE 2026-08-29 against the real Account create-modal capture
# docs/dom-captures/04-account-new-record-modal.html (parsed with tools/dom-miner/pom_miner.py,
# not grepped -- grep double-counts open+close tags and reported 4 lightning-combobox where the
# parser finds 2):
#
#   PICKLIST_READBACK  Every one of the 5 [role=combobox] nodes on that page carries
#                      aria-label == its visible label, at composed shadow depth 9-10, and NONE
#                      is inside a native shadow root. So ONE read-back locator serves both the
#                      picklist and the lookup: //*[@role="combobox"][@aria-label="<Label>"].
#                      The picklist trigger additionally carries the CURRENT VALUE in
#                      data-value ("--None--" before any selection) and repeats it in an inner
#                      span[part=input-button-value].
#                      THIS IS THE LOAD-BEARING FACT FOR THE WHOLE PICKLIST CHAIN: the same
#                      capture contains ZERO rendered options (0 lightning-base-combobox-item,
#                      0 [role=option]) because the option list does not exist in the DOM until
#                      the trigger is clicked. Verifying a picklist by inspecting the option
#                      list is therefore impossible; verifying it by reading the trigger's own
#                      displayed value is both possible and available before the interaction.
#
#   A COUNT THAT IS NOT ONE-TO-ONE, and it matters: that page has 5 [role=combobox] nodes for
#   2 picklists and 1 reference field. The other two are "Address Search" -- the compound
#   address block's autocomplete, which belongs to NO describe field. Keying the read-back on
#   role alone would target the wrong control; keying it on the LABEL is what disambiguates.
#
#   TEXT_READBACK      19 labels carry for=; 17 of them wire to an input/textarea in the same
#                      shadow root. The 2 that do NOT are exactly the two picklists (Type ->
#                      combobox-button-99, Industry -> combobox-button-111 -- <button>, not
#                      <input>). That is the measured reason the picklist chain cannot share the
#                      string family's resolver: qforce_lite.resolve_input's walk only ever
#                      returns input/textarea, so it STRUCTURALLY cannot resolve a picklist.
#                      Also measured on the same capture: ZERO <label> nodes at shadow depth 0,
#                      so QWeb's own get_by_label pass (document.querySelectorAll('label')) sees
#                      nothing at all here and contributes zero resolutions.

def _verify_text(asked: str, got: str) -> bool:
    """Reuses type_text_clearing's own comparator -- the one that already knows Amount holds
    '25,000.00' after typing '25000' and that '(415) 901-7000R20probe' is not a number."""
    return not needs_retype_repair(asked, got)


def _verify_selection(asked: str, got: str) -> bool:
    """A picklist/lookup must DISPLAY what was chosen.

    Containment, not equality, and deliberately so: a lookup renders the selected record's name
    (often with extra chrome) and a picklist can render a locale-translated label for the API
    value it holds. '--None--' is called out explicitly because it is the measured pre-selection
    value on this org's create modal, i.e. the exact string a no-op leaves behind.
    """
    a, g = " ".join((asked or "").split()), " ".join((got or "").split())
    if not g or g in ("--None--", "--Ninguno--"):
        return False
    return a.casefold() == g.casefold() or a.casefold() in g.casefold()


def _verify_multiselection(asked: str, got: str) -> bool:
    """A multipicklist chain call passes/receives values as a comma-joined string (`set_field`'s
    signature is `value: str`, and this file has no per-type value-shape override -- see the
    LiveBackend mechanism below for the same convention on the write side).

    Containment, not exact-set equality, and deliberately so, matching
    keywords_multipicklist.multi_pick_list's own ADDITIVE semantics (`:129`): the widget has no
    "replace selection" affordance, so a prior value already in Chosen legitimately survives a
    new call and must not fail this comparison. `verify_multi_pick_list` (the keyword's own
    getter-side assertion) is the exact-set check for a caller that wants that stronger guarantee;
    this verifier only proves "the chain's own mechanism call is the reason these values are
    there now", which is what set_field's read-back contract asks for.
    """
    asked_vals = {v.strip() for v in (asked or "").split(",") if v.strip()}
    got_vals = {v.strip() for v in (got or "").split(",") if v.strip()}
    if not asked_vals or not got_vals:
        return False
    return asked_vals.issubset(got_vals)


def _verify_checked(asked: str, got: str) -> bool:
    want = str(asked).strip().lower() in ("on", "true", "1", "yes", "checked")
    have = str(got).strip().lower() in ("on", "true", "1", "yes", "checked")
    return want == have


_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_US = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def _as_date(text: str) -> Optional[_dt.date]:
    m = _ISO.search(text or "")
    if m:
        try:
            return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = _US.search(text or "")
    if m:
        try:
            return _dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            return None
    return None


def _verify_date(asked: str, got: str) -> bool:
    """Compare as DATES, not strings -- '2026-09-15' and '09/15/2026' are the same day, and a
    date chain whose rung 1 types a locale string and whose rung 2 clicks an ISO-attributed cell
    will produce both. A side that cannot be parsed makes this return False, which advances the
    chain; it never guesses that two unparseable strings agree."""
    a, g = _as_date(asked), _as_date(got)
    if a is None or g is None:
        return False
    return a == g


@dataclass(frozen=True)
class Verifier:
    """How a type proves a set landed. `read_kind` is what the backend is asked to read."""
    name: str
    read_kind: str
    compare: Callable[[str, str], bool]
    strength: str   # 'strong' = reads the control's own value; 'weak' = reads a proxy
    note: str = ""


VERIFIERS: Dict[str, Verifier] = {
    "picklist": Verifier(
        "combobox_trigger_value", "selection", _verify_selection, "strong",
        "reads the trigger's own data-value / input-button-value, which exists in the DOM before "
        "and after the interaction (measured on the create-modal capture). NOT the option list -- "
        "that does not exist until the dropdown is opened."),
    "reference": Verifier(
        "lookup_input_value", "selection", _verify_selection, "strong",
        "reads the lookup's input[role=combobox]. SETTLED LIVE 2026-08-29 (second-browser round, "
        "T1, dev2, Account/create, Parent Account -> 'H2J VR Premium with phone'): the SAME input "
        "node's own .value AND data-value BOTH flip from '' to the selected record's exact name "
        "on selection ({\"tag\":\"INPUT\",\"data_value\":\"H2J VR Premium with phone\","
        "\"value\":\"H2J VR Premium with phone\",\"text\":\"\"}). Lightning also renders a sibling "
        "'Clear <label> Selection' pill/button at that point, but the combobox input itself is not "
        "a static node the verifier reads vacuously -- it genuinely changes. Promoted from weak."),
    "textarea": Verifier(
        "input_value", "text", _verify_text, "strong",
        "reads the textarea's own .value via needs_retype_repair."),
    "string": Verifier(
        "input_value", "text", _verify_text, "strong",
        "reads the input's own .value via needs_retype_repair, which already tolerates the "
        "measured blur-reformat ('25000' -> '25,000.00') without tolerating '202,525%'."),
    "boolean": Verifier(
        "checkbox_selected", "checked", _verify_checked, "strong",
        "reads is_selected() on the real input. NOTE: QForce's own VerifyCheckbox / "
        "VerifyCheckboxStatus / VerifyCheckboxValue are NOT implemented in qforce-lite "
        "(QFORCE-KEYWORD-INVENTORY.md flags exactly this: a setter without a getter is the "
        "vacuous-pass shape), so this verifier is a real read-back but not the portable one."),
    "date": Verifier(
        "input_value_as_date", "text", _verify_date, "strong",
        "parses both sides to a date, so a locale-typed string and an ISO-clicked cell compare "
        "equal when they name the same day and only then."),
    "multipicklist": Verifier(
        "chosen_column_values", "multiselection", _verify_multiselection, "strong",
        "reads the dual-listbox's own Chosen (`data-selected-list`) column, ground truth for what "
        "the widget itself believes is selected -- the same read keywords_multipicklist."
        "_chosen_values() already performs after every move (`:87-96`), not a guess from click "
        "history."),
}


# =========================================================================== the win log

DEFAULT_STORE = os.path.expanduser("~/.claude/state/chain-wins.jsonl")


@dataclass
class WinStore:
    """Append-only JSONL of what actually worked, keyed by (type, mechanism).

    One line per completed set_field walk. Append-only on purpose: a rewritten "current best"
    file loses the history that makes the record trustworthy, and this project has already been
    bitten by a generated index that drifted from its source with nothing failing loudly.

    Reading is tolerant (a malformed line is skipped, not fatal) because this is an advisory
    cache: the worst case of an unreadable store must be "the canonical order is used", never
    "the keyword raises".
    """
    path: str = DEFAULT_STORE

    def record(self, result: "ChainResult") -> None:
        line = {
            "ts": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "type": result.chain_key,
            "describe_type": result.field_type,
            "sobject": result.sobject,
            "api_name": result.api_name,
            "surface": result.surface,
            "label": result.label,
            "mechanism": result.winner,
            "origin": result.winner_origin,
            "degraded": result.degraded,
            "verified_by": result.verified_by,
            "verifier_strength": result.verifier_strength,
            "attempts": [{"mechanism": a.mechanism, "outcome": a.outcome, "detail": a.detail[:200]}
                         for a in result.attempts],
            "ok": result.winner is not None,
        }
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(line) + "\n")
        except OSError:
            # Never let bookkeeping break a working set. The chain is the product; the log is
            # the memory of it.
            pass

    def _lines(self) -> List[dict]:
        try:
            with open(self.path, encoding="utf-8") as fh:
                out = []
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        out.append(json.loads(raw))
                    except ValueError:
                        continue
                return out
        except OSError:
            return []

    def last_winner(self, chain_key: str) -> Optional[str]:
        """The mechanism that most recently WON for this type, or None.

        Most-recent rather than most-frequent, deliberately: an org, a layout or a Salesforce
        release changes what works, and a frequency count keeps voting for the old world long
        after it stopped being true. Recency adapts in one call; the append-only history is
        still there for anyone who wants the tally.
        """
        for line in reversed(self._lines()):
            if line.get("type") == chain_key and line.get("ok") and line.get("mechanism"):
                return line["mechanism"]
        return None

    def tally(self) -> Dict[str, Dict[str, int]]:
        """{type: {mechanism: wins}} -- the measurement this log exists to make possible."""
        out: Dict[str, Dict[str, int]] = {}
        for line in self._lines():
            if not line.get("ok") or not line.get("mechanism"):
                continue
            out.setdefault(line.get("type", "?"), {})
            key = line["mechanism"]
            out[line["type"]][key] = out[line["type"]].get(key, 0) + 1
        return out


def order_for(chain_key: str, chain: Sequence[Mechanism],
              store: Optional[WinStore] = None) -> List[Mechanism]:
    """The chain with the last winner moved to the front; everything else keeps canonical order.

    Never removes a rung, never reorders anything else, and never affects the LAST_RESORT tail
    (a gated rung cannot be promoted -- it did not run, so it cannot have won). This is the
    entire self-healing mechanism, and its smallness is the point: promotion changes what is
    tried FIRST and nothing else, so a wrong promotion costs one extra verified attempt.
    """
    st = store or WinStore()
    winner = st.last_winner(chain_key)
    if not winner:
        return list(chain)
    head = [m for m in chain if m.id == winner and not m.last_resort]
    if not head:
        return list(chain)
    return head + [m for m in chain if m.id != winner]


# =========================================================================== the walk

@dataclass
class Attempt:
    mechanism: str
    origin: str
    outcome: str
    detail: str = ""


@dataclass
class ChainResult:
    label: str
    value: str
    field_type: str
    chain_key: str
    attempts: List[Attempt] = field(default_factory=list)
    winner: Optional[str] = None
    winner_origin: Optional[str] = None
    degraded: bool = False
    verified_by: Optional[str] = None
    verifier_strength: Optional[str] = None
    promoted: bool = False
    sobject: Optional[str] = None
    api_name: Optional[str] = None
    surface: str = "edit"

    def summary(self) -> str:
        rows = ["%-28s %-8s %-16s %s" % (a.mechanism, a.origin, a.outcome, a.detail[:70])
                for a in self.attempts]
        return "\n".join(rows)


def set_field(label: str, value: str, field_type: str, backend: Any, *,
              sobject: Optional[str] = None, api_name: Optional[str] = None,
              surface: str = "edit", framework: str = "lwc",
              allow_degraded: bool = True, image: Optional[str] = None,
              store: Optional[WinStore] = None, record: bool = True,
              timeout: float = 10) -> ChainResult:
    """Set one field by walking its TYPE's chain, verifying every rung by read-back.

    The contract, in the order it matters:
      1. Dispatch on the DESCRIBE TYPE, never on what is on the page (POLYMORPHISM.md SS2:
         nine types collapse onto one tag, so the DOM cannot tell you which keyword to use).
      2. Try mechanisms in order -- last winner first if the log has one, else canonical.
      3. After each one, READ THE VALUE BACK and compare it to what was asked for. A mechanism
         that raised nothing and changed nothing is a MISS, not a pass.
      4. A read-back that cannot be taken at all is COULD-NOT-CHECK: advance, and if that is how
         every rung ends, raise CouldNotCheck. Never return success.
      5. Record the outcome so the next call starts from evidence.

    Raises NoChainForType / ChainExhausted / CouldNotCheck. Returns ChainResult on success.
    """
    chain = chain_for(field_type, api_name=api_name, framework=framework)
    chain_key = TYPE_ALIASES[field_type.strip()]
    verifier = VERIFIERS[chain_key]
    st = store if store is not None else WinStore()

    ordered = order_for(chain_key, chain, st)
    result = ChainResult(label=label, value=value, field_type=field_type, chain_key=chain_key,
                         sobject=sobject, api_name=api_name, surface=surface)
    result.promoted = bool(ordered) and ordered[0].id != chain[0].id

    saw_could_not_check = False

    for mech in ordered:
        if mech.degrades and not allow_degraded:
            result.attempts.append(Attempt(mech.id, mech.origin, SKIPPED,
                                           "degrading rung, allow_degraded=False"))
            continue
        if "image" in mech.requires and not image:
            result.attempts.append(Attempt(
                mech.id, mech.origin, SKIPPED,
                "needs a pre-captured reference image; never run blind"))
            continue
        if mech.locate_only:
            result.attempts.append(Attempt(
                mech.id, mech.origin, SKIPPED,
                "locate_only: this rung cannot set a value, only find the control"))
            continue

        try:
            backend.run(mech.id, label=label, value=value, field_type=field_type,
                        chain_key=chain_key, sobject=sobject, api_name=api_name,
                        image=image, timeout=timeout)
        except Exception as exc:                       # a rung failing is normal, not fatal
            result.attempts.append(Attempt(mech.id, mech.origin, MISS,
                                           "%s: %s" % (type(exc).__name__, exc)))
            continue

        try:
            got = backend.read(verifier.read_kind, label=label, field_type=field_type,
                               chain_key=chain_key, sobject=sobject, api_name=api_name,
                               timeout=timeout)
        except Exception as exc:
            got = None
            read_err = "%s: %s" % (type(exc).__name__, exc)
        else:
            read_err = ""

        if got is None:
            saw_could_not_check = True
            result.attempts.append(Attempt(
                mech.id, mech.origin, COULD_NOT_CHECK,
                read_err or ("ran without error but %s could not be read back -- the value may "
                             "or may not have landed" % verifier.read_kind)))
            continue

        if verifier.compare(value, str(got)):
            result.attempts.append(Attempt(mech.id, mech.origin, WIN,
                                           "read back %r via %s" % (got, verifier.name)))
            result.winner = mech.id
            result.winner_origin = mech.origin
            result.degraded = mech.degrades
            result.verified_by = verifier.name
            result.verifier_strength = verifier.strength
            if record:
                st.record(result)
            return result

        result.attempts.append(Attempt(
            mech.id, mech.origin, MISS,
            "ran, but %s read back %r -- asked for %r" % (verifier.name, got, value)))

    if record:
        st.record(result)

    detail = result.summary()
    if saw_could_not_check and not any(a.outcome == MISS for a in result.attempts):
        raise CouldNotCheck(
            "set_field(%r, %r, %r): no rung could be verified either way. The value may or may "
            "not have landed -- this is COULD-NOT-CHECK, not success.\n%s"
            % (label, value, field_type, detail))
    raise ChainExhausted(
        "set_field(%r, %r, %r): every rung of the %s chain was tried and none of them landed the "
        "value.\n%s" % (label, value, field_type, chain_key, detail))


# =========================================================================== live backend

class LiveBackend:
    """Drives a real page through qforce_lite / QWeb.

    UNTESTED-LIVE AS A CHAIN, and said plainly: every mechanism below is transcribed from code
    qforce_lite.py already measured live and cites in its own docstrings, but their behaviour as
    interchangeable RUNGS -- in particular whether rung 2 can recover from rung 1's side effects
    on the same control -- has not been run against a browser. The exact live test to run first
    is in docs/crt-train/CHAINS.md. Do not report a green offline self-test as live coverage.

    Imports are lazy so this module stays importable under plain python3 with no selenium and no
    QWeb, which is what lets test_chains.py run in CI.
    """

    def __init__(self, timeout: float = 10):
        self.timeout = timeout

    # -- lazy handles -------------------------------------------------------
    @staticmethod
    def _qfl():
        import qforce_lite
        return qforce_lite

    @staticmethod
    def _qweb():
        from QWeb.keywords import text as qtext
        from QWeb.keywords import input_ as qinput
        from QWeb.keywords import element as qelement
        from QWeb.keywords import config as qconfig
        return qtext, qinput, qelement, qconfig

    # -- read-back ----------------------------------------------------------
    _COMBO_VALUE_JS = r"""
    const want = arguments[0]; let hit = null;
    function walk(root, d){ if (d > 32 || hit) return;
      let els; try { els = root.querySelectorAll('*'); } catch(e) { return; }
      for (const e of els){
        if (e.getAttribute && e.getAttribute('role') === 'combobox'){
          const al = (e.getAttribute('aria-label') || '').trim();
          if (al === want){ hit = e; return; }
        }
        if (e.shadowRoot) walk(e.shadowRoot, d + 1);
      }
    }
    walk(document, 0);
    if (!hit) return null;
    // Measured on docs/dom-captures/04-account-new-record-modal.html: a picklist trigger is a
    // <button role=combobox> carrying the current value in data-value and repeating it in an
    // inner span[part=input-button-value]; a lookup is an <input role=combobox> whose value is
    // the typed/selected text. Read all three and let the caller's verifier decide.
    const dv = (hit.getAttribute('data-value') || '').trim();
    const v  = (hit.value || '').trim();
    const t  = (hit.textContent || '').trim().split('\n')[0];
    return JSON.stringify({data_value: dv, value: v, text: t});
    """

    def read(self, kind: str, *, label: str, **_) -> Optional[str]:
        qfl = self._qfl()
        drv = qfl._driver()
        if kind == "selection":
            raw = drv.execute_script(self._COMBO_VALUE_JS, label)
            if not raw:
                return None
            info = json.loads(raw)
            # value first (a lookup holds the selected text there), then data-value (a picklist
            # holds the selected API/display value there), then the rendered text.
            for k in ("value", "data_value", "text"):
                if info.get(k):
                    return info[k]
            return ""      # resolved the control and it is genuinely empty -- that is a MISS,
                           # not a could-not-check, and returning "" says so.
        if kind in ("text",):
            el = qfl.resolve_input(label)
            if el is None:
                return None
            return el.get_attribute("value")
        if kind == "checked":
            el = qfl.resolve_input(label)
            if el is None:
                return None
            return "on" if el.is_selected() else "off"
        if kind == "multiselection":
            # Mirrors keywords_multipicklist.get_multi_pick_list_value's own resolution, but
            # returns None on "could not resolve" rather than raising -- read()'s contract is
            # that None means COULD-NOT-CHECK, never an exception the chain walk has to catch.
            try:
                mpl = self._mpl()
                group = mpl._group_xpath(label)
                if not mpl._driver().find_elements(mpl.By.XPATH, group):
                    return None
                values = mpl._chosen_values(group, self.timeout)
            except Exception:
                return None
            return ",".join(values)
        return None

    # -- mechanisms ---------------------------------------------------------
    def run(self, mech_id: str, *, label: str, value: str, chain_key: str,
            image: Optional[str] = None, timeout: float = 10, **_) -> None:
        fn = getattr(self, "_m_" + mech_id, None)
        if fn is None:
            raise NotImplementedError(
                "LiveBackend has no implementation for rung %r. Not guessed -- a fabricated rung "
                "that silently no-ops is precisely the vacuous pass this file exists to stop."
                % mech_id)
        fn(label=label, value=value, chain_key=chain_key, image=image, timeout=timeout)

    # picklist ---------------------------------------------------------------
    def _m_qforce_picklist(self, *, label, value, timeout, **_):
        self._qfl().pick_list(label, value, timeout=timeout)

    def _m_qweb_clickitem_shadow(self, *, label, value, timeout, **_):
        qtext, _qi, qelement, qconfig = self._qweb()
        trigger = ('(//*[@role="combobox"][@aria-label="%s"])[1]' % label)
        if not self._is_expanded(trigger):
            qelement.click_element(trigger, timeout=timeout, js=True)
        prev = qconfig.get_config("ShadowDOM")
        qconfig.set_config("ShadowDOM", True)
        try:
            qtext.click_item(value, timeout=timeout)
        finally:
            qconfig.set_config("ShadowDOM", prev)

    def _is_expanded(self, xpath: str) -> bool:
        try:
            return bool(self._qfl()._driver().execute_script(
                'var n=document.evaluate(arguments[0],document,null,9,null).singleNodeValue;'
                'return n ? n.getAttribute("aria-expanded")==="true" : false;', xpath))
        except Exception:
            return False

    def _m_qweb_dropdown_native(self, *, label, value, timeout, **_):
        from QWeb.keywords import dropdown as qdropdown
        qdropdown.drop_down(label, value, timeout=timeout)

    _OPTION_CLICK_JS = r"""
    const want = arguments[0]; let hit = null;
    function walk(root, d){ if (d > 32 || hit) return;
      let els; try { els = root.querySelectorAll('*'); } catch(e) { return; }
      for (const e of els){
        const t = e.tagName.toLowerCase();
        const title = (e.getAttribute && e.getAttribute('title')) || '';
        const role  = (e.getAttribute && e.getAttribute('role')) || '';
        const txt   = (e.textContent || '').trim();
        if ((role === 'option' || t === 'lightning-base-combobox-item' ||
             t === 'lightning-base-combobox-formatted-text') &&
            (title.trim() === want || txt === want)){ hit = e; return; }
        if (e.shadowRoot) walk(e.shadowRoot, d + 1);
      }
    }
    walk(document, 0);
    if (!hit) return false;
    hit.click();
    return true;
    """

    def _m_ours_js_option_click(self, *, label, value, timeout, **_):
        qfl = self._qfl()
        drv = qfl._driver()
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            if drv.execute_script(self._OPTION_CLICK_JS, value):
                return
            time.sleep(0.25)
        raise ValueError("no [role=option] / lightning-base-combobox-item titled %r found in the "
                         "composed tree within %ss" % (value, timeout))

    # reference --------------------------------------------------------------
    def _m_qforce_combobox(self, *, label, value, timeout, **_):
        self._qfl().combo_box(label, value, timeout=timeout)

    def _m_qweb_show_all_results(self, *, label, value, timeout, **_):
        self._qfl().combo_box(label, value, timeout=timeout, all_results=True)

    def _m_ours_focus_retype_encore(self, *, label, value, timeout, **_):
        qfl = self._qfl()
        el = qfl.resolve_input(label)
        if el is None:
            raise ValueError("could not resolve the lookup input for %r" % label)
        drv = qfl._driver()
        drv.execute_script("arguments[0].focus();", el)
        el.clear()
        el.send_keys(value)
        # The encore is a DELAYED request ~1.1s after the keystroke burst (round 8 CDP capture),
        # so this bounded poll is waiting for a specific measured event, not sleeping and hoping.
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            if drv.execute_script(qfl._COMBO_RESULTS_JS):
                return
            time.sleep(0.25)
        raise ValueError("lookup dropdown never populated for %r within %ss" % (value, timeout))

    # text family ------------------------------------------------------------
    def _m_qweb_type_text_clear_key(self, *, label, value, timeout, **_):
        _qt, qinput, _qe, _qc = self._qweb()
        qinput.type_text(label, value, timeout=timeout, clear_key="{CONTROL + a}")

    def _m_ours_js_focus_send_keys(self, *, label, value, timeout, **_):
        qfl = self._qfl()
        el = qfl.resolve_input(label)
        if el is None:
            raise ValueError("could not resolve an input for %r" % label)
        drv = qfl._driver()
        drv.execute_script("arguments[0].focus();", el)
        el.clear()
        el.send_keys(value)
        drv.execute_script("arguments[0].blur();", el)

    _NATIVE_SET_JS = r"""
    const el = arguments[0], v = arguments[1];
    const proto = el.tagName.toLowerCase() === 'textarea'
        ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(el, v);
    el.dispatchEvent(new Event('input',  {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
    """

    def _m_ours_native_value_setter(self, *, label, value, timeout, **_):
        qfl = self._qfl()
        el = qfl.resolve_input(label)
        if el is None:
            raise ValueError("could not resolve an input for %r" % label)
        qfl._driver().execute_script(self._NATIVE_SET_JS, el, value)

    # boolean ----------------------------------------------------------------
    def _m_qforce_click_checkbox(self, *, label, value, timeout, **_):
        self._qfl().click_checkbox(label, value=value or "on", timeout=timeout)

    def _m_qweb_click_faux_span(self, *, label, value, timeout, **_):
        _qt, _qi, qelement, _qc = self._qweb()
        qelement.click_element(
            '(//label[normalize-space(.)="%s"]/..//span[contains(@class,"slds-checkbox_faux")])[1]'
            % label, timeout=timeout, js=True)

    def _m_ours_click_label_ancestor(self, *, label, value, timeout, **_):
        _qt, _qi, qelement, _qc = self._qweb()
        qelement.click_element('(//label[normalize-space(.)="%s"])[1]' % label,
                               timeout=timeout, js=True)

    def _m_ours_js_set_checked_dispatch(self, *, label, value, timeout, **_):
        qfl = self._qfl()
        el = qfl.resolve_input(label)
        if el is None:
            raise ValueError("could not resolve a checkbox for %r" % label)
        want = str(value).strip().lower() in ("on", "true", "1", "yes", "checked")
        qfl._driver().execute_script(
            "arguments[0].checked = arguments[1];"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", el, want)

    # date -------------------------------------------------------------------
    def _m_qweb_type_text_date(self, *, label, value, timeout, **_):
        _qt, qinput, _qe, _qc = self._qweb()
        d = _as_date(value)
        if d is None:
            raise ValueError("value %r is not a parseable date" % value)
        qinput.type_text(label, d.strftime("%m/%d/%Y"), timeout=timeout,
                         clear_key="{CONTROL + a}")

    def _m_ours_calendar_widget(self, *, label, value, timeout, **_):
        d = _as_date(value)
        if d is None:
            raise ValueError("value %r is not a parseable date" % value)
        got = self._qfl().pick_date(label, day=d.day, timeout=timeout)
        # pick_date does not navigate months. If the popup was showing a different month, the
        # click was on the right DAY of the WRONG month -- say so here rather than letting the
        # verifier report a confusing mismatch.
        if got != d.isoformat():
            raise ValueError("calendar was showing %s; pick_date does not navigate months, so "
                             "%s was not reachable in one click" % (got, d.isoformat()))

    # multipicklist ------------------------------------------------------------
    @staticmethod
    def _mpl():
        import keywords_multipicklist
        return keywords_multipicklist

    def _m_qforce_multi_pick_list(self, *, label, value, timeout, **_):
        # set_field's contract is value: str; a multipicklist call passes it comma-joined
        # ("Sales,Trainer") -- the same convention _verify_multiselection reads on the way back.
        values = [v.strip() for v in str(value).split(",") if v.strip()]
        if not values:
            raise ValueError("multipicklist value %r had no non-empty comma-separated values" % value)
        self._mpl().multi_pick_list(label, values, timeout=timeout)


# =========================================================================== CLI

def _explain(chain_key: Optional[str] = None, store: Optional[WinStore] = None) -> str:
    st = store or WinStore()
    tally = st.tally()
    keys = [chain_key] if chain_key else list(CHAINS)
    out = []
    for k in keys:
        if k not in CHAINS:
            out.append("no chain named %r. known: %s" % (k, ", ".join(sorted(CHAINS))))
            continue
        v = VERIFIERS[k]
        promoted = st.last_winner(k)
        out.append("== %s   verify: %s (%s)" % (k, v.name, v.strength))
        out.append("   %s" % v.note)
        if promoted:
            out.append("   PROMOTED FIRST (last winner in the log): %s" % promoted)
        for i, m in enumerate(order_for(k, CHAINS[k], st), 1):
            flags = []
            if m.degrades:
                flags.append("DEGRADES")
            if m.last_resort:
                flags.append("GATED(%s)" % ",".join(m.requires))
            if m.locate_only:
                flags.append("LOCATE-ONLY")
            wins = tally.get(k, {}).get(m.id, 0)
            out.append("   %d. %-28s %-8s %-22s wins=%d" %
                       (i, m.id, m.origin, " ".join(flags), wins))
        out.append("")
    return "\n".join(out)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="per-TYPE self-healing fallback chains")
    ap.add_argument("--json", action="store_true", help="emit JSON output")
    ap.add_argument("--explain", nargs="?", const="", metavar="TYPE",
                    help="print the chain for one type, or all types")
    ap.add_argument("--store", default=None, help="path to the win log (default %s)" % DEFAULT_STORE)
    ap.add_argument("--tally", action="store_true", help="print {type: {mechanism: wins}}")
    args = ap.parse_args()
    st = WinStore(args.store) if args.store else WinStore()
    if args.tally:
        print(json.dumps(st.tally(), indent=2))
        return 0
    print(_explain(args.explain or None, st))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
