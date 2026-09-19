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
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
for _p in ("tools/interop/resources/pythonDom", "tools/benchmark"):
    _abs = os.path.join(_ROOT, _p)
    if _abs not in sys.path:
        sys.path.insert(0, _abs)

OWN = "own"
SHELL = "shell"

# The state name a capture carries when it is the page itself (crawl.py CAPTURE_DEFAULT_STATE and
# store.DEFAULT_STATE). A literal here so this module imports nothing from store -- store imports
# this one, and a cycle would break every reader.
DEFAULT_STATE = "default"

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


def find_tab_subtree(soup):
    """The selected tab's panel: [role=tab][aria-selected=true] -> aria-controls -> its tabpanel.
    A page with two tabsets has two selected tabs and reads COULD-NOT-CHECK, which is the honest
    answer (fsc7f's Account page is exactly that)."""
    tabs = soup.select("[role=tab][aria-selected=true]")
    if len(tabs) != 1:
        return None, "[role=tab][aria-selected=true]", "%d selected tabs" % len(tabs)
    ctl = tabs[0].get("aria-controls")
    if not ctl:
        return None, "[role=tab][aria-selected=true]", "selected tab has no aria-controls"
    panels = [n for n in soup.select("[role=tabpanel]") if n.get("id") == ctl]
    if len(panels) != 1:
        return None, "[role=tabpanel]#%s" % ctl, "%d panels" % len(panels)
    return (panels[0],
            "[role=tab][aria-selected=true] -> aria-controls -> [role=tabpanel]#%s" % ctl, "ok")


def find_state_subtree(soup, kind=None):
    """(node, selector, note) for a NAMED state. `kind` is the state's stored kind when the record
    has one (`modal`/`panel`, written by merge_session), else None and the shape is read off the
    capture itself: a capture taken in a modal state HAS the dialog open; one taken in a tab state
    does not."""
    if kind in ("modal", "panel"):
        return find_dialog_subtree(soup)
    if kind == "tab":
        return find_tab_subtree(soup)
    node, sel, note = find_dialog_subtree(soup)
    if node is not None:
        return node, sel, note
    if note.startswith("AMBIGUOUS"):
        return None, sel, note
    return find_tab_subtree(soup)


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
def _control_ids(html, element_id, stable_attrs):
    """Raw element ids for every LABEL-BEARING control in this html -- the same denominator
    `pom_asset.controls()` uses, so both halves are comparable to the store by construction."""
    from capture_orchestration import parse_elements_from_html
    import metadata_dom_parity as PARITY
    out = set()
    for e in parse_elements_from_html(html):
        label = ((e.get("identification") or {}).get("label_text")) or ""
        if not PARITY.norm(label):
            continue
        det = e.get("element_details") or {}
        out.add(element_id(e.get("element_type"), label,
                           (e.get("context") or {}).get("section") or "",
                           stable_attrs(det.get("attributes") or {})))
    return out


def scopes_for_capture(html: str, *, state: str | None, kind: str | None = None,
                       element_id=None, stable_attrs=None) -> dict | None:
    """{raw element id -> "own"|"shell"} for one capture, or **None** for COULD-NOT-CHECK.

    `element_id`/`stable_attrs` are `pom.store`'s, passed in so the ids are minted by exactly the
    code the writer uses and this module needs no import from store.

    * named state -- `own` = parsed from the state's own subtree; `shell` = the page with that
      subtree removed, so the page underneath keeps its context and its ids do not shift.
    * base state (`default`, or no state) -- the page's own controls are `own`; anything inside a
      dialog that happened to be open is **not** the base state's, and is `shell`.
    * unresolvable subtree -- None, and the caller writes no `scope` key at all.
    """
    from bs4 import BeautifulSoup
    if element_id is None or stable_attrs is None:          # pragma: no cover - programmer error
        raise TypeError("scopes_for_capture needs store.element_id and store.stable_attrs")
    soup = BeautifulSoup(html, "html.parser")
    if bool(state) and state != DEFAULT_STATE:
        node, _sel, _note = find_state_subtree(soup, kind)
        if node is None:
            return None
        inside = _control_ids("<html><body>%s</body></html>" % str(node), element_id, stable_attrs)
        node.decompose()
        outside = _control_ids(str(soup), element_id, stable_attrs)
    else:
        node, _sel, note = find_dialog_subtree(soup)
        if node is None and note.startswith("AMBIGUOUS"):
            return None
        if node is not None:
            outside = _control_ids("<html><body>%s</body></html>" % str(node),
                                   element_id, stable_attrs)
            node.decompose()
            inside = _control_ids(str(soup), element_id, stable_attrs)
        else:
            inside, outside = _control_ids(html, element_id, stable_attrs), set()
    return dict([(k, OWN) for k in inside] + [(k, SHELL) for k in outside if k not in inside])
