"""Same-app iframe descent for the DOM parser (2026-09-07,
docs/recorder/COPADO-GAPS-2026-09-07.md "Iframe / canvas / Visualforce
boundaries" + docs/recorder/REVIEW-BRIEF-NEXT.md row C4c: "`--op capture`
serialises the iframe but the classifier never walks into it -- 17 shell
elements for a page whose form is in the frame").

tools/dom-miner/cdp_capture.py's in-page SERIALIZER (the JS `walk()` that
runs inside the driven page) handles an `<iframe>` one of two ways,
`stats.iframes` (same-origin, walked inline via a `<!--frame-content-->`
marker) vs. `stats.crossOriginFrames` (cross-origin/OOPIF, left as an
unresolved `<!--cross-origin-frame idx=N src="...">` placeholder for a
SEPARATE, OUT-OF-PAGE Python step). C4c's captures are the SECOND shape:
tools/recorder/cdp_transport.py's `FrameAttacher`/`FrameContextTracker` +
`splice_cross_origin_frames` (driven from `cdp_capture.py`'s
`_splice_cross_origin_frames`, after the in-page walk returns) resolve that
frame's own JS execution context and splice its serialized markup back in,
REPLACING the placeholder, as:

    <!-- frame: <src> --><template garzai-frame="<src>" origin="cross" mode="<session|context>">
    ...</template>

**Measured live on both `backpromote-02-new-promotion.html` and
`backpromote-03-confirmation-ready.html` (2026-09-07, this stream, via
direct grep of the raw capture text):** 0 unresolved
`<!--cross-origin-frame idx=` placeholders remain, 1 resolved
`<template garzai-frame="" origin="cross" mode="context">` each -- the
Promotion iframe WAS captured, mode="context" (same renderer,
`FrameContextTracker` path), never left as COULD-NOT-CHECK/still-a-
placeholder. **No `tools/dom-miner/cdp_capture.py` or `cdp_transport.py`
change was needed or made** -- the gap C4c found was entirely in CLASSIFY
not descending into markup that was already there, not a capture gap.

The SAME-ORIGIN inline shape (`<!--frame-content-->`, e.g. Salesforce
Setup's classic-in-a-same-origin-iframe pages, per `cdp_capture.py`'s own
comment) is deliberately OUT OF SCOPE for this module: measured live
2026-09-07, extending descent to that marker inflated `test_loss_audit.py`'s
v2 noise-ceiling on both Setup captures (`06-setup-permission-sets.html`
68->153, `slockard-recorder/setup-permsets.html` 229->833) -- that content
was never tuned/audited for noise the way this task's target (C4c's cross-
origin Promotion iframe) was, and widening scope to it broke a protected
existing test for no requirement this task actually has. Left as
COULD-NOT-CHECK for a future, deliberately-scoped pass (with its own noise
tuning), not silently absorbed here.

Real HTML parsers -- both Python's `html.parser` and `lxml` -- treat
`<iframe>` as a RAWTEXT element: its children are NEVER parsed into tags,
even though the cross-origin-splice content is fully present as literal
markup on disk. `component_classifier`/`element_compiler` both need a real
bs4 Tag to inspect, so that content was never reachable before this fix.
Measured 2026-09-07 (pre-fix): 0 elements inside the iframe subtree on both
backpromote captures, out of 17 total shell elements on each -- matching
C4c's "17 shell elements for a page whose form is in the frame" exactly.

This module finds each spliced cross-origin frame block by regex (bs4
cannot see it, so there is no tag to `find_all` against), HTML-unescapes
it, sub-parses it as its own bs4 document, and classifies its content with
the SAME config/classifier/compiler pipeline the caller already runs on its
top-level document -- passed in as `classify_soup_fn` so this module has
exactly one definition of "how to walk a frame block" and both
`capture_orchestration.py` and `DomParserLibraryNew.py` stay identical in
which passes actually run over a sub-document (the two entry points are
parity-tested, `tools/recorder/tests/templates/test_parser_families_2026_09_07.py`
and this fix's own `test_iframe_descent_2026_09_07.py`).

Every resulting element from inside a frame gets a `frame` key -- this is
purely a DISAMBIGUATION signal, not a navigation instruction: real QWeb
auto-penetrates iframes on its own when clicking or typing (user, confirmed
2026-09-07: "QWeb auto penetrates iframes... the only reason to even
consider iframes is for deduplication"), so no keyword ever needs to be
told to switch into a frame first. The only reason CLASSIFY needs to know a
control lives inside a frame at all is for the rare case where the SAME
label exists both inside the frame and on the host page (or in a sibling
frame) -- `frame` lets a consumer tell those two elements apart when it
matters; it is meaningless metadata the rest of the time and never becomes
part of a locator/keyword hint by itself (see
`element_compiler._get_qforce_hints`, unchanged by this module). Measured
on both fixture captures: 0 label collisions between host and frame (see
the fixture test's census) -- disambiguation was not even needed here, but
the signal is now present for the case where it is.

The frame's own `<iframe>` tag ALSO classifies as its own element (family
`iframe`, dom_config.py's TARGET_TAGS + component_classifier.py) via the
normal top-level pass, independent of this module -- this module only
supplies what is INSIDE the frame.
"""
import html as _html
import re

# Matches exactly what tools/recorder/cdp_transport.py's
# `splice_cross_origin_frames` writes (`_sub`, mode="context"|"session").
# The marker leads with `<!-- frame: <src> -->` OUTSIDE the <template> on
# purpose (per that function's own comment) -- kept here as one group so a
# capture with src="" (measured live: both backpromote captures) still
# matches, it's just an empty string.
_CROSS_ORIGIN_RE = re.compile(
    r'<!--\s*frame:\s*(?P<src>.*?)\s*-->'
    r'<template\s+garzai-frame="[^"]*"\s+origin="cross"\s+mode="(?P<mode>[^"]*)"\s*>'
    r'(?P<body>.*?)'
    r'</template>',
    re.DOTALL,
)


def extract_frame_blocks(raw_html: str) -> list:
    """Returns one dict per same-app CROSS-ORIGIN frame spliced into this
    capture (see module docstring for why the same-origin `<!--frame-
    content-->` shape is deliberately not handled here), in document order:
        {"index": 1-based int, "src": str, "mode": "context"|"session",
         "html": unescaped inner markup}
    Never raises -- a capture with no spliced frame (the common case) just
    returns []."""
    blocks = []
    for i, m in enumerate(_CROSS_ORIGIN_RE.finditer(raw_html), start=1):
        blocks.append({
            "index": i,
            "src": (m.group("src") or "").strip(),
            "mode": m.group("mode") or "session",
            "html": _html.unescape(m.group("body")),
        })
    return blocks


def frame_label(block: dict, iframe_tag=None):
    """The `frame` disambiguation identifier stamped onto every element
    found inside this frame -- used ONLY to tell two same-labeled elements
    apart (one inside this frame, one on the host page or a sibling frame);
    never a navigation instruction (QWeb auto-penetrates iframes on its
    own). Preference order, each confirmed live on the C4c/C4b captures:
      1. The enclosing <iframe>'s `title`, UNLESS it is Aura's generic
         placeholder ("accessibility title" -- measured on every VF-in-Aura
         frame this pass, carries no per-frame identity).
      2. The enclosing <iframe>'s `name` (Aura's own per-frame id, e.g.
         "vfFrameId_1788705794491" -- always present, always unique).
      3. The block's 1-based index among frames spliced into this capture.
    """
    if iframe_tag is not None:
        title = (iframe_tag.get("title") or "").strip()
        if title and title.lower() != "accessibility title":
            return title
        name = (iframe_tag.get("name") or "").strip()
        if name:
            return name
    return block["index"]


def collect_frame_elements(raw_html: str, main_soup, classify_soup_fn) -> list:
    """Walks every same-app cross-origin frame spliced into `raw_html`,
    classifying each with `classify_soup_fn(sub_soup) -> list[dict]` (the
    caller's own full pass -- datatable/table/target-tags/interactive-roles/
    c-*/lightning-* -- so behaviour matches the top-level document exactly)
    and tagging every returned element with `frame` (see `frame_label`).

    Matches each block back to its enclosing real `<iframe>` tag in
    `main_soup`, in document order, by index -- the block itself carries no
    positional link to the tag since bs4 never parsed the tag's contents.
    A frame block whose sub-parse raises is skipped (not silently merged
    with the main document, not fabricated) -- this only ever ADDS elements,
    never removes any from the caller's own top-level pass.
    """
    blocks = extract_frame_blocks(raw_html)
    if not blocks:
        return []
    from bs4 import BeautifulSoup
    iframe_tags = main_soup.find_all("iframe") if main_soup is not None else []
    out = []
    for block in blocks:
        iframe_tag = iframe_tags[block["index"] - 1] if block["index"] - 1 < len(iframe_tags) else None
        label = frame_label(block, iframe_tag)
        try:
            frame_soup = BeautifulSoup(block["html"], "html.parser")
        except Exception:
            continue
        for el in classify_soup_fn(frame_soup):
            el["frame"] = label
            out.append(el)
    return out
