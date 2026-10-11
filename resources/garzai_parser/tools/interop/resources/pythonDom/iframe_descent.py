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

2026-10-09 (frames-capture; docs/DESIGN-FRAMES-CAPTURE-2026-10-09.md, F28/F36): the flat regex is
replaced by a walk over the capture's <iframe> elements (balanced on nested frames), because the
regex's non-greedy `</template>` stopped at the FIRST shadow root inside a spliced frame -- the
customer QLE capture (docs/dom-captures/customer-cpq/qle-q15573-editlines-ctx-fixed.html: 52,019
bytes, 39 form controls, 188 shadow roots) gave the classifier 812 bytes and 0 controls. A raw
splice is no longer `html.unescape`d (that turned `&quot;` inside an attribute into a quote that
ended it). Every frame is listed by `frame_census`, walked or not, with why. And the descent is
FRAME-AGNOSTIC (the user, 2026-10-09): a SAME-ORIGIN frame the serializer walked inline is now
classified like any other -- the 2026-09-07 out-of-scope note above is superseded -- so a classic
Setup page's fields come from its vfFrame itself, never from the old splicer's copy of it (F28).
"""
import html as _html
import re

# The splice wrapper tools/recorder/cdp_transport.py's `splice_cross_origin_frames` writes (`_sub`,
# mode="context"|"session"). The marker leads with `<!-- frame: <src> -->` OUTSIDE the <template> on
# purpose (per that function's own comment); a capture with src="" (both backpromote captures, every
# Aura-hosted VF frame) still matches, its src is just empty.
_SPLICE_OPEN_RE = re.compile(
    r'\s*(?:<!--\s*frame:\s*(?P<src>.*?)\s*-->)?\s*'
    r'<template\s+garzai-frame="(?P<gsrc>[^"]*)"\s+origin="cross"\s+mode="(?P<mode>[^"]*)"\s*>',
    re.DOTALL,
)
# What cdp_capture.py's SERIALIZER writes as the first thing inside an <iframe> it walked INLINE (a
# same-origin frame: Salesforce Setup's classic page in its vfFrame, a VF page's own inner frames).
_INLINE_MARK = '<!--frame-content-->'
_IFRAME_OPEN_RE = re.compile(r'<iframe\b([^>]*)>', re.IGNORECASE)
_ATTR_RE = re.compile(r'([^\s=/"\'<>]+)\s*=\s*"([^"]*)"')
_AURA_PLACEHOLDER_TITLE = 'accessibility title'
#: frames inside frames are walked this deep (Setup: the vfFrame, then its sessionserver helper = 2)
MAX_FRAME_DEPTH = 6


def _iframe_spans(markup: str) -> list:
    """Each OUTERMOST `<iframe ...>...</iframe>` of `markup`, in document order, as
    (start, end, attrs, body). Balanced on nested iframe tags: a frame's content is serialized markup
    that may hold frames of its own (Setup's vfFrame holds a sessionserver iframe). The serializer
    escapes `<` in every text node and attribute value, so a literal `<iframe` is always a tag."""
    out, pos, n = [], 0, len(markup)
    low = markup.lower()
    while True:
        m = _IFRAME_OPEN_RE.search(markup, pos)
        if not m:
            break
        depth, i, closed = 1, m.end(), False
        while depth:
            o = low.find('<iframe', i)
            c = low.find('</iframe>', i)
            if c < 0:
                i = n                       # unterminated: the rest is its body
                break
            if 0 <= o < c:
                if _IFRAME_OPEN_RE.match(markup, o):
                    depth += 1
                i = o + 7
            else:
                depth -= 1
                i = c + 9
                closed = depth == 0
        body = markup[m.end():i - 9] if closed else markup[m.end():i]
        out.append((m.start(), i, dict(_ATTR_RE.findall(m.group(1))), body))
        pos = i
    return out


def _own_markup(body: str) -> str:
    """`body` with every frame inside it cut out: a frame's OWN document, without its children's."""
    spans = _iframe_spans(body)
    if not spans:
        return body
    parts, pos = [], 0
    for start, end, _attrs, _b in spans:
        parts.append(body[pos:start])
        pos = end
    parts.append(body[pos:])
    return ''.join(parts)


def _frame_content(body: str):
    """(origin, inner markup, mode, src) for one iframe's body:
      same        walked inline by the serializer (`<!--frame-content-->`)
      cross       spliced from the frame's own execution context or target (`<template garzai-frame ...>`)
      unresolved  a `<!--cross-origin-frame -->` placeholder nobody filled (COULD-NOT-CHECK in the capture header)
      hidden      a `<!--hidden-frame -->` marker: a helper frame no person sees, never spliced
      empty       nothing inside (an unloaded frame, a frame captured by an older serializer)"""
    s = body.lstrip()
    if s.startswith(_INLINE_MARK):
        return 'same', s[len(_INLINE_MARK):], None, ''
    m = _SPLICE_OPEN_RE.match(body)
    if m:
        # the wrapper's own close is the LAST </template> of the body: a frame with shadow roots holds
        # `<template shadowrootmode>` pairs of its own, and the first </template> closes one of THEM (the
        # customer QLE capture: 188 shadow roots, the first close at byte 812 of 52,019)
        close = body.rfind('</template>')
        inner = body[m.end():close] if close >= m.end() else body[m.end():]
        if '<' not in inner and '&lt;' in inner:
            inner = _html.unescape(inner)   # an ESCAPED splice; a raw one is never unescaped (it would break
            #                                 every attribute holding &quot; and turn &lt; text into a tag)
        return 'cross', inner, (m.group('mode') or 'session'), (m.group('src') or m.group('gsrc') or '').strip()
    head = s[:600]
    if head.startswith('<!--hidden-frame'):
        return 'hidden', '', None, ''
    if head.startswith('<!--cross-origin-frame'):
        return 'unresolved', '', None, ''
    return 'empty', '', None, ''


def frame_census(raw_html: str) -> list:
    """EVERY frame of the capture, the ones the parser walks and the ones it does not, depth first in
    document order: {"index", "depth", "parent", "name", "title", "src", "origin", "mode", "walked",
    "why", "html"} -- `index` counts every frame listed; `walked` says whether `collect_frame_elements`
    classifies it and `why` says why not. Never raises."""
    rows = []

    def visit(markup, depth, parent, parent_own):
        if depth > MAX_FRAME_DEPTH:
            return
        for _start, _end, attrs, body in _iframe_spans(markup):
            origin, inner, mode, src = _frame_content(body)
            row = {"index": len(rows) + 1, "depth": depth, "parent": parent,
                   "name": (attrs.get('name') or '').strip(), "title": (attrs.get('title') or '').strip(),
                   "src": (src or attrs.get('src') or '').strip(), "origin": origin, "mode": mode,
                   "walked": origin in ('same', 'cross'), "why": None, "html": inner}
            if (origin == 'cross' and parent_own is not None and len(inner) > 0
                    and _own_markup(inner) == parent_own):
                # F28 (2026-10-08 overnight): the capture's old single-placeholder fallback filled a frame's hidden
                # helper child (Setup's sessionserver) with the PARENT frame's own document. A document is never its
                # own child: the parent is classified itself, so walking the copy would list every control twice.
                # Stored captures carry it (25 of 25 product Setup captures); a capture taken since 2026-10-09 does not.
                row["walked"] = False
                row["why"] = ("a copy of its own parent frame's document (the old splicer's fallback, F28): "
                              "not a frame of its own")
            elif origin == 'unresolved':
                row["why"] = "a cross-origin frame the capture could not reach (COULD-NOT-CHECK in its header)"
            elif origin == 'hidden':
                row["why"] = "a hidden helper frame (aria-hidden, off-screen or zero-size): no person sees it"
            elif origin == 'empty':
                row["why"] = "nothing captured inside it"
            rows.append(row)
            if row["walked"]:
                visit(inner, depth + 1, row["index"], _own_markup(inner) if origin == 'same' else None)

    try:
        visit(raw_html, 0, None, None)
    except Exception:                                                     # noqa: BLE001 -- never raises
        return rows
    return rows


def extract_frame_blocks(raw_html: str) -> list:
    """Returns one dict per frame the parser walks -- FRAME-AGNOSTIC: a same-origin frame the serializer
    walked inline (`origin` "same") and a cross-origin frame spliced into the capture (`origin` "cross"),
    whatever app owns it -- depth first in document order, a frame inside a frame included (`depth`,
    `parent`):
        {"index": 1-based int over `frame_census`, "src": str, "mode": "context"|"session"|None,
         "origin": "same"|"cross", "depth", "parent", "name", "title", "html": the frame's own markup}
    `html` still holds the frame's own child frames as RAWTEXT, so a caller that sub-parses each block
    sees each control once. Never raises -- a capture with no frame (the common case) returns []."""
    return [b for b in frame_census(raw_html) if b["walked"]]


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
      3. The block's 1-based index among the frames of this capture.
    `iframe_tag` is the enclosing tag (anything with `.get`); without one the block's own `title` /
    `name` (read off the same tag's markup by `frame_census`) are used."""
    src = iframe_tag if iframe_tag is not None else block
    title = (src.get("title") or "").strip()
    if title and title.lower() != _AURA_PLACEHOLDER_TITLE:
        return title
    name = (src.get("name") or "").strip()
    if name:
        return name
    return block["index"]


def collect_frame_elements(raw_html: str, main_soup, classify_soup_fn) -> list:
    """Walks every frame `extract_frame_blocks` returns (same-origin frames walked inline and cross-origin
    frames spliced in, at any depth), classifying
    each with `classify_soup_fn(sub_soup) -> list[dict]` (the caller's own full pass --
    datatable/table/target-tags/interactive-roles/c-*/lightning-* -- so behaviour matches the
    top-level document exactly) and tagging every returned element with `frame` (see `frame_label`).

    Each block is sub-parsed on its OWN markup: its child frames stay RAWTEXT inside it and are walked
    as blocks of their own, so no control is classified twice; a block that is a copy of its own
    parent (F28) is never walked. A frame block whose sub-parse raises is skipped (not silently
    merged with the main document, not fabricated) -- this only ever ADDS elements, never removes
    any from the caller's own top-level pass. `main_soup` is kept for the callers' signature; the
    enclosing tag's attributes are read off the capture's own markup."""
    blocks = extract_frame_blocks(raw_html)
    if not blocks:
        return []
    from bs4 import BeautifulSoup
    out = []
    for block in blocks:
        label = frame_label(block)
        try:
            frame_soup = BeautifulSoup(block["html"], "html.parser")
        except Exception:
            continue
        for el in classify_soup_fn(frame_soup):
            el["frame"] = label
            out.append(el)
    return out
