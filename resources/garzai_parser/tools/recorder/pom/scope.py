"""STATE SCOPE -- does this control belong to the state's OWN container, or to the page around it?

The user's rule (2026-09-19):

    "When an interaction goes to a sub-portion, like a new modal on that details page, that step
     should only be applicable to what is in that new modal. When it's on the hierarchy of that
     general page, that's just going to have that general page's things."

and for tabs: a step taken in a tab state scopes to that tab's BODY plus the page shell.

THE DEFECT THIS CLOSES (measured one page per shape,
`docs/recorder/evidence/state-scope-one-page-2026-09-19.md`): the POM state model had no notion of
"inside". `pom_asset.build_record` appended EVERY control a capture parsed to `stamped_eids` and
`store.apply_capture_stamp` filed all of it under the state, so copado-trial's
`GarzAI slockard cred Preview` modal held 73 members of which **69 were the page shell** -- the App
Launcher, Setup, Home, Delete, every tab link -- and `page_pack.py build` then handed an AI a
"modal" part of 64 controls, 3 of which were in the modal.

THE ONE FIELD. A state member stays a bare element id; the scope goes on the element's own
per-state entry, which already exists:

    elements[<eid>]["states"][<state>] = {"label": ..., "scope": "own" | "shell"}

* `own`   -- inside the state's own DOM subtree (the modal/dialog/docked composer/menu, or the
              selected tab's panel). For the base state, the page's own controls.
* `shell` -- the page around it. Still a member (a step driven in a modal can still name Save on
              the page behind it), but never the modal's contents.
* ABSENT  -- COULD-NOT-CHECK. No capture stands behind this member, or the subtree could not be
              resolved. **Never defaulted to `own`.**

Why two values and not `modal|tab-body|shell`: the state already carries `kind`, so a three-valued
scope would duplicate it and let the two disagree. The only fact the member was missing is *does
this control belong to this state's own container*.

THE LADDER is the one measured on the two probe pages, most-specific-first, and it refuses to
guess: two outermost matches is AMBIGUOUS and the capture reads COULD-NOT-CHECK rather than
scoring against the wrong node.

Offline and pure: the caller hands it capture HTML. No browser, no org, no store.
"""
from __future__ import annotations

import os
import re as _re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
for _p in ("tools/interop/resources/pythonDom", "tools/benchmark"):
    _abs = os.path.join(_ROOT, _p)
    if _abs not in sys.path:
        sys.path.insert(0, _abs)

OWN = "own"
SHELL = "shell"

# ---------------------------------------------------------------- THE BASE STATE HAS ONE NAME
# B1 (held-out audit, 2026-09-19): the base state was written under TWO names. `crawl.py` drove the
# page with `HOST_STATE = "page"` (merge_session wrote that into every record) while it STAMPED its
# base captures `default` (`store.DEFAULT_STATE`, the sentinel merge_session uses for "this step
# named no state"). `migrate_scope.capture_index` then keyed base captures `(key, "default")` and
# `plan_record` looked up `(key, "page")`, so the two never met: measured store-wide, **0 records
# carried a state named `default` and 18 carried `page`, while 106 of 198 index entries were
# `default`** -- every base state in the store permanently COULD-NOT-CHECK, with 14/12/3 stamped
# base captures sitting unread on disk for the three held-out records.
#
# `page` is the ONE name, for three reasons that are facts rather than taste:
#   1. it is what all 18 stored records already carry, so the migration rewrites no record and is
#      a safety net rather than a rewrite of the store;
#   2. `default` is ALREADY taken -- `store.DEFAULT_STATE` is merge_session's sentinel for "the
#      step named no state", and a name that means both "no state" and "the base state" is the
#      ambiguity that produced B1. Distinct words for distinct facts;
#   3. the base state's `kind` is already `page` (`apply_capture_stamp`), and crawl.py's own
#      comment beside HOST_STATE already said `default` was the wrong name for it.
BASE_STATE = "page"

# What a capture may be STAMPED with and still mean the base state. `default` is the legacy stamp:
# every capture on disk before 2026-09-19 carries it, and they are read, never rewritten.
BASE_STATE_ALIASES = (BASE_STATE, "default")

# Back-compat alias. `DEFAULT_STATE` used to be this module's name for the base state; it is kept
# so an older caller still imports, and it now points at the ONE name.
DEFAULT_STATE = BASE_STATE


def is_base_state(name) -> bool:
    """True when this state name means "the page itself" -- empty, `page`, or the legacy `default`
    stamp. The ONE place that question is answered, so a reader and a writer cannot disagree."""
    return (not name) or name in BASE_STATE_ALIASES


def normalize_state(name):
    """The canonical name for a state: every base-state spelling collapses onto `page`."""
    return BASE_STATE if is_base_state(name) else name

# `[role=dialog]` is worn by Lightning's "New user experience" coachmark on a great many pages;
# without excluding it every fsc7f capture reads AMBIGUOUS (measured 2026-09-19).
_COACHMARK = "nux-coachmark"

_DIALOG_LADDER = (
    ("[aria-modal=true]", None),
    # `slds-modal` also matches modal-container/header/body/footer and the close button -- 6 hits
    # for 1 modal -- so only the OUTERMOST match counts, here and on every rung.
    ("div.slds-modal, section.slds-modal", None),
    # a docked composer (New Task) is a role=dialog with neither slds-modal nor aria-modal
    ("[role=dialog].slds-docked-composer", None),
    ("[role=dialog]", _COACHMARK),
    ("[role=menu]", None),
)

_INTERACTIVE = ["button", "a", "input", "select", "textarea", "th", "td"]


def _outermost(hits):
    return [n for n in hits if not any(a in hits for a in n.parents)]


def find_dialog_subtree(soup):
    """(node, selector, note). node is None when no dialog/menu is open, and None with an
    AMBIGUOUS note when a rung has two outermost matches -- COULD-NOT-CHECK, never a guess."""
    for sel, excl in _DIALOG_LADDER:
        hits = soup.select(sel)
        if excl:
            hits = [n for n in hits if n.get("data-testid") != excl]
        outer = _outermost(hits)
        if len(outer) > 1:
            return None, sel, "AMBIGUOUS: %d outermost matches" % len(outer)
        if len(outer) == 1:
            n = outer[0]
            # SLOTTED-PANEL TRAP: a Lightning dropdown's [role=menu] holds only a <slot>; its items
            # serialize under the slot HOST, so scoring against the menu node calls every item
            # "outside". Ascend to the nearest custom element and say so.
            if n.find("slot") is not None and not n.find(_INTERACTIVE):
                host = next((p for p in n.parents if p.name and "-" in p.name), None)
                if host is not None:
                    return host, "%s -> slot host <%s>" % (sel, host.name), "slotted panel"
            return n, sel, "ok"
    return None, "dialog ladder", "no dialog or menu subtree in this capture"


def _norm(s) -> str:
    return " ".join(str(s or "").split()).casefold()


def text_of(node) -> str:
    """The node's text, TEMPLATE-SAFE.

    **`get_text()` is empty over most of a Lightning capture** and gives no sign of it. The capture
    serializer wraps every shadow root in `<template>`, and bs4 4.15 marks strings inside one
    `TemplateString`, which is NOT in `interesting_string_types` -- so `get_text()` skips them
    silently. Measured 2026-09-19 on dev1's Account view: the selected tab's `contents` is
    `['Details']` and `get_text(' ', strip=True)` is `''`. `TemplateString` is a `str` subclass, so
    walking `descendants` and keeping the `str` ones reads what a person sees."""
    return " ".join(str(x) for x in node.descendants if isinstance(x, str))


def _tab_label(node) -> str:
    """What a person reads on a tab. `data-label` is Lightning's own copy of the visible tab text
    and survives the template wrapper; the text, aria-label and title follow it."""
    return _norm(node.get("data-label") or text_of(node) or node.get("aria-label")
                 or node.get("title") or "")


def find_tab_subtree(soup, driven_tab=None):
    """The DRIVEN tab's panel: the selected tab whose label the state was entered via ->
    aria-controls -> its tabpanel.

    TWO TABSETS IS THE STANDARD RECORD PAGE, not an fsc7f quirk (held-out audit 2026-09-19:
    **36 of 60** held-out captures carry two selected tabs -- a details tabset and a related-list
    tabset -- so "1 selected tab" made every standard Salesforce record page COULD-NOT-CHECK and
    no tab state on one could ever be scoped). `driven_tab` is the label the state was entered via
    (or the state's own name); when exactly one selected tab carries it, that is the tabset the
    interaction happened in and the other tabset is page shell. With no label to go on, or a label
    that names none of them (or more than one), this still refuses to guess."""
    tabs = soup.select("[role=tab][aria-selected=true]")
    sel = "[role=tab][aria-selected=true]"
    if not tabs:
        return None, sel, "0 selected tabs"
    if len(tabs) > 1:
        want = _norm(driven_tab)
        if not want:
            return None, sel, ("%d selected tabs and no driven tab label to choose between them"
                               % len(tabs))
        hit = [t for t in tabs if _tab_label(t) == want]
        if len(hit) != 1:
            return None, sel, ("%d selected tabs and the driven label %r names %d of them"
                               % (len(tabs), driven_tab, len(hit)))
        tabs, sel = hit, "%s naming %r" % (sel, driven_tab)
    ctl = tabs[0].get("aria-controls")
    if not ctl:
        return None, sel, "selected tab has no aria-controls"
    panels = [n for n in soup.select("[role=tabpanel]") if n.get("id") == ctl]
    if len(panels) != 1:
        return None, "[role=tabpanel]#%s" % ctl, "%d panels" % len(panels)
    return panels[0], "%s -> aria-controls -> [role=tabpanel]#%s" % (sel, ctl), "ok"


# ------------------------------------------------------------------ LIGHTNING INLINE-EDIT FORM
# B2 (held-out audit, 2026-09-19). 13 held-out states named `Edit <Field> menu` and kinded `panel`
# resolved to NO subtree at all: the page is not a menu and holds no dialog. Clicking a field's
# pencil puts the WHOLE record detail form into edit mode. Measured on dev1's Account view:
# the base capture is 125,795 B with **0 `<input>`** and 0 record-layout-items holding an editable
# child; `Edit-Phone-menu.html` is 170,708 B with **18 `<input>`**, 34 `lightning-input`, a Save
# and **14** record-layout-items that gained an editable child -- and no `[role=dialog]`,
# `[role=menu]`, `.slds-modal` or `.slds-popover` anywhere. The ladder simply had no rung for it.
#
# The signature is a GROWTH, not an absolute: slockard's Zoo Case base capture already holds 1
# editable item (a related-list search box), so "has an editable item" would call its base state
# form mode. The rung therefore diffs against the page's own base capture and takes only the items
# that BECAME editable, plus the edit footer that carries Save/Cancel.
_FORM_ITEM = "records-record-layout-item, force-record-layout-item"
_EDITABLE = ("input, textarea, select, lightning-input, lightning-textarea, lightning-combobox, "
             "lightning-picklist, lightning-lookup, lightning-grouped-combobox, "
             "lightning-input-field, lightning-datepicker, lightning-timepicker")
# The inline-edit footer. `div.center-align-buttons` nests inside `div.footer-full-width`, so
# _outermost leaves one node. Measured present on all 13 inline-edit captures and on NO base,
# menu or view capture of the same four pages.
_FORM_FOOTER = "div.footer-full-width, div.center-align-buttons"


def _editable_items(soup):
    """{a key that survives a re-render: the item node} for every record-layout-item holding an
    editable control. The key is the field label the item declares, never a generated id."""
    out = {}
    for i, n in enumerate(soup.select(_FORM_ITEM)):
        if not n.select(_EDITABLE):
            continue
        lab = n.get("field-label")
        if not lab:
            lt = n.select_one(".slds-form-element__label, span.test-id__field-label")
            lab = text_of(lt) if lt else ""       # template-safe: see `text_of`
        out[_norm(lab) or "item#%d" % i] = n
    return out


def find_form_subtrees(soup, base_soup=None):
    """([node, ...], selector, note) for Lightning inline-edit form mode, or (None, sel, why).

    The state's own controls are the record-layout-items that BECAME editable plus the edit
    footer; everything else on the page -- the highlights panel, the tab bar, the related lists,
    the nav -- is shell. With no base capture to diff against, every editable item counts and the
    note says so, because over-including there is visible in the note rather than silent."""
    footer = _outermost(soup.select(_FORM_FOOTER))
    items = _editable_items(soup)
    if not footer or not items:
        return None, _FORM_FOOTER, "no inline-edit form in this capture"
    if base_soup is None:
        return (list(items.values()) + footer, "%s + %s" % (_FORM_ITEM, _FORM_FOOTER),
                "form mode, no base capture to diff against -- every editable item counted")
    was = set(_editable_items(base_soup))
    grew = [n for k, n in items.items() if k not in was]
    if not grew:
        return None, _FORM_ITEM, ("an edit footer is present but no record region became editable "
                                  "versus the base capture")
    return (grew + footer, "%s that became editable + %s" % (_FORM_ITEM, _FORM_FOOTER),
            "form mode, %d of %d record region(s) became editable" % (len(grew), len(items)))


def find_state_subtree(soup, kind=None, driven_tab=None, base_soup=None):
    """(nodes, selector, note) for a NAMED state -- `nodes` is a LIST (inline-edit form mode is
    several record regions plus a footer) or None for COULD-NOT-CHECK.

    `kind` is the state's stored kind when the record has one (`modal`/`panel`, written by
    merge_session), else None and the shape is read off the capture itself. `driven_tab` is the
    label the state was entered via, which is what picks the right tabset on a two-tabset page.
    `base_soup` is the page's own base capture, needed only by the inline-edit rung.

    The crawler kinds an inline-edit state `panel` (it was reached by clicking `Edit <Field>`), so
    the form rung has to sit behind the dialog ladder on the `panel` path too -- it is tried when
    the dialog ladder finds nothing, never when it finds something."""
    if kind in ("modal", "panel"):
        node, sel, note = find_dialog_subtree(soup)
        if node is not None:
            return [node], sel, note
        if note.startswith("AMBIGUOUS"):
            return None, sel, note
        nodes, fsel, fnote = find_form_subtrees(soup, base_soup)
        return (nodes, fsel, fnote) if nodes else (None, sel, note)
    if kind == "tab":
        node, sel, note = find_tab_subtree(soup, driven_tab)
        return ([node] if node is not None else None), sel, note
    node, sel, note = find_dialog_subtree(soup)
    if node is not None:
        return [node], sel, note
    if note.startswith("AMBIGUOUS"):
        return None, sel, note
    nodes, fsel, fnote = find_form_subtrees(soup, base_soup)
    if nodes:
        return nodes, fsel, fnote
    node, tsel, tnote = find_tab_subtree(soup, driven_tab)
    return ([node] if node is not None else None), tsel, tnote


# A TOAST IS NOT PART OF THE PAGE. Lightning's toast manager renders a transient notification
# wherever it likes; its `Dismiss` was a member of NINE states on the probe page and outside every
# one of their subtrees. These containers hold nothing a test drives on purpose.
_TRANSIENT = "[role=alert], .slds-notify, .toastContainer, .forceToastMessage, .forceToastManager"


def transient_ids(html: str, *, element_id=None, stable_attrs=None) -> set:
    """Raw element ids for every control inside a toast / alert container. They are chrome: the
    element is still recorded, it is simply never a member of a state."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    out: set = set()
    for n in _outermost(soup.select(_TRANSIENT)):
        out |= _control_ids("<html><body>%s</body></html>" % str(n), element_id, stable_attrs)
    return out


# --------------------------------------------------------------------------- the scope map
def _control_rows(html, element_id, stable_attrs):
    """[(element id, identity-minus-container key)] for every LABEL-BEARING control in this html --
    the same denominator `pom_asset.controls()` uses, so both halves are comparable to the store by
    construction.

    The KEY drops the `container` segment, and that is what makes the subtree split work. A
    control's container is read off its surroundings, so the SAME control mints one id when the
    whole page is parsed and another when its subtree is parsed alone
    (`input_field|Billing City||name=city` vs `...|Billing Address|name=city`). Family, label,
    stable attributes and the HTML tag do not move.

    THE TAG RIDES ALONG (D20/F122, 2026-09-19). `pom_asset.build_record`'s `id_map` translates this
    function's RAW id to the record's FINAL one (`identify_control`'s id, which now carries the
    tag), so the two must agree on what "raw" means. Leaving tag out here would collide two
    genuinely different controls that share a label and container but differ in tag -- measured on
    slockard's Zoo Case CKEditor toolbar: a page-shell `Strikethrough` (`button`) and one inside the
    `Edit Zoo Phone` panel (`a`) shared one raw key, so `id_map` (a plain dict) kept only the LAST
    one written and the other's scope silently rode along with it (`test_a_held_out_state_holds_
    exactly_its_own_controls[slockard-zoo-case-view/Edit Zoo Phone menu]`)."""
    from capture_orchestration import parse_elements_from_html
    import metadata_dom_parity as PARITY
    out = []
    for e in parse_elements_from_html(html):
        label = ((e.get("identification") or {}).get("label_text")) or ""
        if not PARITY.norm(label):
            continue
        det = e.get("element_details") or {}
        fam = e.get("element_type")
        at = stable_attrs(det.get("attributes") or {})
        tag = det.get("tag")
        # the key is the SAME id with an empty container -- canonical, hashable, and identical
        # for a control whether the whole page or only its subtree was parsed
        out.append((element_id(fam, label, (e.get("context") or {}).get("section") or "", at,
                               tag=tag),
                    element_id(fam, label, "", at, tag=tag)))
    return out


def _control_ids(html, element_id, stable_attrs):
    """Just the ids. Kept because readers outside this module use it."""
    return {i for i, _k in _control_rows(html, element_id, stable_attrs)}


def _split(html, nodes, element_id, stable_attrs):
    """(inside ids, outside ids) over the ids the capture ITSELF mints.

    **The document is parsed ONCE, from the bytes on disk.** Re-serializing a capture through bs4
    and parsing that instead loses controls silently: measured 2026-09-19 on slockard's Zoo Case
    inline-edit capture, `str(soup)` parsed **138** controls where the file parses **174** -- the
    36 missing ones are a CKEditor toolbar (`Align Left`, `Bold (Cmd+B)`, ...) whose `<a
    href="javascript:void('Align Left')">` does not survive the round trip. Those 36 were members
    of the state with no scope at all and nothing said why.

    So the subtrees are parsed alone -- which is safe, because only the CONTAINER segment of an id
    moves -- and matched back onto the page's own ids by the identity-minus-container key. A
    control whose family, label and stable attributes match one inside the subtree is inside: two
    such controls in different containers are the same control as far as every locator rung is
    concerned, and `own` is this codebase's standing tie-break for a control that is in both."""
    rows = _control_rows(html, element_id, stable_attrs)
    by_key: dict = {}
    for i, k in rows:
        by_key.setdefault(k, set()).add(i)
    inside: set = set()
    for n in nodes:
        for _i, k in _control_rows("<html><body>%s</body></html>" % str(n),
                                   element_id, stable_attrs):
            inside |= by_key.get(k, set())
    whole = {i for i, _k in rows}
    return inside, whole - inside


def capture_header(path):
    """{path, host, state, entered_via} off a capture's header, or None. Header bytes only."""
    try:
        head = open(path, errors="replace").read(4000)
    except OSError:
        return None

    def one(k):
        m = _re.search(r"<!--\s*%s:\s*(.*?)\s*-->" % k, head)
        return (m.group(1).strip() if m else "")
    m = _re.search(r"<!--\s*state:\s*(?P<s>.*?)\s*\|\s*entered_via:\s*(?P<v>.*?)\s*[|-]", head)
    return {"path": one("path"), "host": one("host"),
            "state": (m.group("s") if m else ""), "entered_via": (m.group("v") if m else "")}


def find_base_capture(capture_path):
    """The base-state capture of the SAME page, beside this one on disk, or None.

    Matched on the captures' own headers (`path:` + `host:` + the state stamp), never by splitting
    a filename on dots -- a state name may contain one. The one entered by `nav` wins: that is the
    page as it was LANDED, before any state left residue in it (a `default-after-Edit-Zoo-Phone`
    capture is stamped base and is still in form mode, measured 2026-09-19). Used only by the
    inline-edit rung, the one rung that needs to know what the page looked like before."""
    if not capture_path:
        return None
    d = os.path.dirname(os.path.abspath(capture_path))
    hdr = capture_header(capture_path)
    if not hdr:
        return None
    cands = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".html"):
            continue
        p = os.path.join(d, name)
        if os.path.abspath(p) == os.path.abspath(capture_path):
            continue
        h = capture_header(p)
        if not h or h["path"] != hdr["path"] or h["host"] != hdr["host"]:
            continue
        if not is_base_state(h["state"]):
            continue
        cands.append((0 if _norm(h["entered_via"]) == "nav" else 1, os.path.getmtime(p), p))
    return min(cands)[2] if cands else None


def scopes_for_capture(html: str, *, state: str | None, kind: str | None = None,
                       element_id=None, stable_attrs=None, driven_tab=None,
                       base_html: str | None = None) -> dict | None:
    """{raw element id -> "own"|"shell"} for one capture, or **None** for COULD-NOT-CHECK.

    `element_id`/`stable_attrs` are `pom.store`'s, passed in so the ids are minted by exactly the
    code the writer uses and this module needs no import from store.

    * named state -- `own` = parsed from the state's own subtree(s); `shell` = the page with those
      subtrees removed, so the page underneath keeps its context and its ids do not shift.
    * base state (`page`, the legacy `default` stamp, or no state) -- the page's own controls are
      `own`; anything inside a dialog, or in an inline-edit form, that happened to be open is
      **not** the base state's, and is `shell`.
    * unresolvable subtree -- None, and the caller writes no `scope` key at all.
    """
    from bs4 import BeautifulSoup
    if element_id is None or stable_attrs is None:          # pragma: no cover - programmer error
        raise TypeError("scopes_for_capture needs store.element_id and store.stable_attrs")
    soup = BeautifulSoup(html, "html.parser")
    base_soup = BeautifulSoup(base_html, "html.parser") if base_html else None
    if not is_base_state(state):
        nodes, _sel, _note = find_state_subtree(soup, kind, driven_tab, base_soup)
        if not nodes:
            return None
        inside, outside = _split(html, nodes, element_id, stable_attrs)
    else:
        node, _sel, note = find_dialog_subtree(soup)
        nodes = [node] if node is not None else None
        if node is None:
            if note.startswith("AMBIGUOUS"):
                return None
            # a base capture taken while the page was still in inline-edit form mode is the same
            # case as a dialog left open: the form is not the page's own (measured 2026-09-19 --
            # every `default-after-Edit-Zoo-<Field>` capture is still in form mode)
            nodes, _fsel, _fnote = find_form_subtrees(soup, None)
        if nodes:
            # the dialog or form left open is NOT the base state's own -- the halves swap
            outside, inside = _split(html, nodes, element_id, stable_attrs)
        else:
            inside, outside = _control_ids(html, element_id, stable_attrs), set()
    return dict([(k, OWN) for k in inside] + [(k, SHELL) for k in outside if k not in inside])
