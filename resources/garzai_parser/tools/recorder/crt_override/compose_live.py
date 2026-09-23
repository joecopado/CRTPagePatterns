"""compose_live -- the CRT recorder override's answer on a page nobody reviewed.

Usage:
  python3 tools/recorder/crt_override/compose_live.py --capture <html> --org <alias> --url <page url> --target '<identity xpath>' --rendered '<the recorder line>' [--form keyword|xpath|both]

compose-from-capture: what the CRT recorder override answers on a page NOBODY reviewed.

`build_override.py` embeds a review's rows and answers each recorded event with that review's
VERIFIED line (proven 2026-09-18, 29 of 29 pane lines on the Zoo page). A page with no review gets
nothing: every recorder line passes through, absolute paths and all. This module is that page's
path -- our OWN capture of the live DOM, the EXISTING parser and pattern library over it, the
recorded element found among the parsed rows by DOM identity, and the parser's proposed keyword
form (and xpath form) as the answer, marked `# unverified: parser proposal`.

Nothing here parses HTML, classifies a control or invents a locator: `review_table.build_rows`
(the JSON parser + the xpath ladder + the identity xpath) and `pattern_library` (buckets + the
verified recipes) are consumed as they are. The parser's `index` is consumed as a DESCRIPTION
only (`disambiguation.index` in the answer): a numeric anchor is never composed from a capture
count (F189, 2026-09-20 -- `Company anchor=8` hung 3 of 3 in the container while the anchor-less
lines landed 4 of 4). With the element in hand the driver layer takes a live census
(`live_disambiguation`) and decides bare label / text anchor / xpath-live from it. The review is
still what turns `unverified` into `verified`; this only stops a blank page from being worse
than a reviewed one.

Two layers, deliberately split so `build_override` can inline the second one later:

  compose_from_capture(html, url, org, target_identity_xpath, rendered, form) -> dict
      pure: html in, line out, no driver, unit-tested offline against a committed capture.
  compose_live_element(drv, target_element, rendered, org, cache, url, form) -> dict
      the driver layer: ONE capture per page through the same serializer `up.py --op capture`
      ships (tools/dom-miner/cdp_capture.build_serializer -- it pierces synthetic and native
      shadow roots; the recorder's own snapshot was measured too thin, 22-45 KB, main frame only),
      then ONE execute_script that `===`-compares the target against every parsed row's identity
      xpath. Recapture only when the target is not among the cached rows.

The verdict words on any surface: VERIFIED-PASS / CAUGHT-BUG / COULD-NOT-CHECK / PASS-GUARDED.
A line from here is none of them -- it is a PROPOSAL, which is why every emitted line carries the
unverified marker and why `confidence` is never raised here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..'))
for _p in ('tools/recorder', 'tools/dom-miner'):
    _abs = os.path.join(_ROOT, _p)
    if _abs not in sys.path:
        sys.path.insert(0, _abs)

import review_table as RT          # noqa: E402  (parser + xpath ladder + identity xpath)
import descriptor as DESC         # noqa: E402  (the page's own description of the element, and the row rule)
import disambiguation_args as DA   # noqa: E402  (the ONE place a described `index` becomes QWeb's numeric `anchor`)
import pattern_library as PL       # noqa: E402  (buckets + the verified recipes)
from pom import keys as PK         # noqa: E402  (the page key, for provenance)

UNVERIFIED = '# unverified: parser proposal'

# families whose control is FILLED (the recorder's focus click and tab-out render as
# ClickText/VerifyText of the field's own value -- 8 of 17 lines on the Zoo page, run 3)
FILL_FAMILIES = ('input_field', 'textarea', 'date', 'datetime', 'lookup', 'combobox',
                 'picklist', 'email', 'number', 'search')
CLICK_ACTIONS = ('ClickText', 'ClickElement', 'ClickItem', 'Click', 'ClickCheckbox')
NOISE_ACTIONS = ('ClickText', 'VerifyText')
_MAX_CACHED_PARSES = 4
_PARSE_CACHE: dict = {}


# ----------------------------------------------------------------------------- small helpers
def _cells(line: str) -> list[str]:
    return [c for c in re.split(r' {2,}|\t', (line or '').strip()) if c != '']


def split_step_body(body: str) -> tuple:
    """A composed Robot step -> (keyword, positional cells, kwarg cells), UN-ESCAPING NOTHING.

    `RT.parse_robot_line` un-escapes `\\=` for EXECUTION; this one exists to RE-RENDER, so
    `xpath\\=//a[@b\\="c"]` must come back out of `RT._rf` byte-identical. `# ...` comment cells
    are dropped: they are the note on the line, never an argument.
    """
    cells = [c for c in _cells(body or '') if not c.startswith('#')]
    if not cells:
        return None, [], {}
    kw, args, kwargs = cells[0], [], {}
    for c in cells[1:]:
        if _KWARG_CELL.match(c):
            k, v = c.split('=', 1)
            kwargs[k] = v
        else:
            args.append(c)
    return kw, args, kwargs


def _indent(rendered: str) -> str:
    """Every emitted line starts with the recorder's own leading whitespace, or four spaces.
    Measured 2026-09-18 (run 1): six composed lines arrived at the CRT editor as keyword messages
    and NONE reached the pane -- the only difference was the missing indent."""
    r = rendered or ''
    lead = r[: len(r) - len(r.lstrip())]
    return lead or '    '


def _xp_of(row: dict) -> str | None:
    return row.get('xpath_corrected') or (row.get('xpath') or {}).get('value')


def _label_of(row: dict) -> str:
    return RT._clean_label(row.get('label_corrected') or row.get('label') or '')


def _described_index(row: dict) -> int | None:
    """The member's position among the same-label matches the parser counted in the CAPTURE --
    a DESCRIPTION, carried in the answer as `disambiguation.index` and never as a call argument.

    Until build n9 this became `anchor=<n>` through `disambiguation_args.to_call_kwargs`: QWeb's
    INDEX MODE, which counts by QWeb's own live scorer over the live page. The two counts are not
    the same number (F188 CAUGHT-BUG 3, 2026-09-20: Lead New modal, `Company anchor=8` /
    `Title anchor=9` / `Email anchor=7` resolved nothing and hung 3 of 3; the anchor-less lines on
    the same modal landed 4 of 4; the committed new-Account capture reports `Shipping City` as
    index 2 of 2 while the label occurs once). The live decision is `live_disambiguation`."""
    idx = row.get('index_corrected') if 'index_corrected' in row else row.get('index')
    if not idx or (row.get('group_size') or 1) <= 1:
        return None
    try:
        n = int(str(idx).strip())
    except (TypeError, ValueError):
        return None
    return n if n >= 1 else None


_NUMERIC_ANCHOR_CELL = re.compile(r'^anchor=(\d+)$')


def strip_numeric_anchor(body: str) -> tuple[str, int | None]:
    """(body without its `anchor=<digits>` cell, the number that was there or None). A TEXT anchor
    (`anchor=September`) is a real disambiguator and is kept; a body with no numeric anchor comes
    back byte-identical."""
    cells = _cells(body or '')
    hit = next((c for c in cells if _NUMERIC_ANCHOR_CELL.match(c)), None)
    if hit is None:
        return body, None
    return '    '.join(c for c in cells if not _NUMERIC_ANCHOR_CELL.match(c)), int(hit[len('anchor='):])


def _unescape_xpath_step(step: str) -> str | None:
    """The xpath inside a `ClickElement    xpath\\=...` step (the form the recipes are written in)."""
    m = re.match(r'\s*\w[\w ]*?\s{2,}xpath\\=(.+?)\s*$', step or '')
    return m.group(1).replace('\\=', '=') if m else None


def capture_header(url: str | None, org: str | None, path_hint: str | None = None,
                   stats: dict | None = None) -> str:
    """The header a real capture carries. `pom_asset.page_key_for` reads `host:`/`path:` off it, and
    a capture with no host used to be filed under a fabricated `unknown-host.lightning.force.com`
    -- a SALESFORCE suffix -- which put 583 third-party controls inside an org's POM (2026-09-12).
    The url here comes from the caller (the driver's own `location`), never from a guess."""
    host, path = '', path_hint or ''
    if url:
        m = re.match(r'^[a-z]+://([^/]+)(/.*)?$', url)
        if m:
            host, path = m.group(1), (m.group(2) or path or '/')
    out = ['<!-- capture: compose_live (in-memory) -->']
    if path:
        out.append('<!-- path: %s -->' % path)
    if host:
        out.append('<!-- host: %s -->' % host)
    if org:
        out.append('<!-- org: %s -->' % org)
    if stats:
        out.append('<!-- stats: %s -->' % json.dumps(stats))
    return '\n'.join(out) + '\n'


# ----------------------------------------------------------------------------- the parse (cached)
class Parsed:
    """One capture, parsed once: the rows the parser proposes plus the lxml tree they were found in."""

    def __init__(self, cap, rows: list, page_key: str | None, parse_ms: float, url: str | None):
        self.cap, self.rows, self.page_key, self.parse_ms, self.url = cap, rows, page_key, parse_ms, url
        self._tree = cap.doc.getroottree()

    def path_of(self, el) -> str:
        """Canonical identity of one element WITHIN this tree -- lxml proxies are created on
        demand, so `is` between two xpath calls is not guaranteed; the tree path is.

        NEVER memoise this on `id(el)`: an lxml proxy is freed as soon as the last reference to it
        goes, and the next proxy can be allocated at the same address. Measured 2026-09-18 on the
        first oracle run -- six of the 22 events matched a chrome button (rows 0-3) because a
        stale id hit answered for a different element."""
        return self._tree.getpath(el)

    def resolve(self, xpath: str) -> list:
        try:
            return self.cap.doc.xpath(xpath)
        except Exception:
            return []


def parse_capture(html: str, url: str | None, org: str | None) -> Parsed:
    """Parse ONE capture through the existing parser; cached on (html, url, org) so a page is
    parsed once per event storm, never per event."""
    key = hashlib.sha1(('%s|%s|' % (org or '', url or '')).encode() + html.encode('utf-8', 'replace')).hexdigest()
    hit = _PARSE_CACHE.get(key)
    if hit is not None:
        return hit
    body = html if '<!-- host:' in html[:2000] or '<!-- path:' in html[:2000] else \
        capture_header(url, org) + html
    t0 = time.time()
    fd, path = tempfile.mkstemp(suffix='.html', prefix='compose-live-')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(body)
        cap = RT.Capture(path)
        rows, _tmpl = RT.build_rows(cap, org)      # the parser, the ladder, the identity xpath
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    pk = None
    try:
        pk = (PK.page_key(url, org=org) or {}).get('key') if url else None
    except Exception:
        pk = None
    parsed = Parsed(cap, rows, pk, round((time.time() - t0) * 1000, 1), url)
    if len(_PARSE_CACHE) >= _MAX_CACHED_PARSES:
        _PARSE_CACHE.pop(next(iter(_PARSE_CACHE)))
    _PARSE_CACHE[key] = parsed
    return parsed


# ----------------------------------------------------------------------------- composition
def _recipe_first_action(entry: dict, row: dict, value: str | None) -> str | None:
    """The ACTION line of a verified library recipe (its read-back lines are the review's job, not
    a recorded event's). A documenting entry -- a policy or a measured failure -- starts with `#`
    and is never emitted as a step."""
    try:
        kw_lines, _xp_lines = PL.recipe(entry, row, value if value is not None else RT.probe_value(row))
    except Exception:
        return None
    for line in kw_lines:
        if line.strip().startswith('#'):
            return None
        # the library renders `{anchor_kw}` from the same capture count (F189): stripped here so
        # the recipe rung and the generic rung answer one shape
        return strip_numeric_anchor(line.strip())[0]
    return None


def _recipe_note(entry: dict | None) -> str:
    """The provenance note for a line the pattern library rendered (CH-B B1.d,
    docs/audit/challenge-wave-one-2026-09-23/CH-B-d22-followthrough.md): a recipe-led line is a
    MEASURED pattern, never `UNVERIFIED` ('# unverified: parser proposal') -- that stamp is a false
    claim on a recipe, the same error class F246 was raised for. Carries the entry's own `status`
    verbatim when it is not the default 'verified' (so 'verified-on-one-page' travels, per
    `review_table._pattern_entry`'s own admission list), and the pages it was measured on when the
    library entry carries that count (most do not yet -- omitted, never fabricated)."""
    if not entry:
        return UNVERIFIED
    name = entry.get('id') or entry.get('name')   # the id names the recipe; the name is a sentence
    status = entry.get('status') or 'verified'
    note = '# recipe: %s' % name
    if status != 'verified':
        note += ' (%s)' % status
    pages = entry.get('measured_pages')
    if isinstance(pages, int) and pages > 0:
        note += ', measured on %d page%s' % (pages, '' if pages == 1 else 's')
    return note


def _stamp(line: str, note: str) -> str:
    """Join a provenance note onto a composed line as ONE comment cell (F196/F203, the fifth call
    site, 2026-09-23): `annotate` folds it into an existing `#` note with `; `, so a disclosure the
    line already carries (`# COULD-NOT-CHECK: ...`) stays FIRST and the recipe stamp follows it;
    a line with no note gets `    # <note>`, byte-identical to the old plain join."""
    body = note[2:] if note.startswith('# ') else note.lstrip('#').strip()
    return annotate(line.rstrip(), body)


def _insert_before_note(cells: list, mark: str) -> list:
    """A kwarg cell goes BEFORE the first `#` cell, never after it: Robot reads nothing past a
    comment marker, so `gz_family=combobox` appended last (7 lines of the n12 goldens) never
    reached the shipped TypeText override."""
    out = list(cells)
    for i, c in enumerate(out):
        if c.strip().startswith('#'):
            out.insert(i, mark); return out
    out.append(mark); return out


def _recipe_step_value(rendered: str) -> str | None:
    """The event's OWN recorded value, when the rendered line carries one (>=3 cells, the same
    read `_body` rule 5 uses) -- never the synthetic probe D19/F246 exists to keep out of a
    composed line."""
    cells = _cells(rendered)
    return cells[-1] if len(cells) >= 3 else None


def _recipe_live_step(step: str, probe, real_value: str | None) -> tuple[str | None, str | None]:
    """(live, dormant) for ONE recipe STEP already matched by its own xpath against a
    PROBE-rendered form (`RT.probe_value(row)`, CH-B B1.c): the match is found by rendering with a
    SYNTHETIC review literal purely to see whose xpath resolves to the target element, and that
    literal must never become a LIVE line on its own (D19/F246 -- the same rule the fill branch
    already obeys at :316-326). A step that never embedded the probe at all (most STEPS -- e.g. the
    dual-listbox move arrow's own ClickElement, which carries no {value} slot) stands live
    unchanged. One that did gets the event's own recorded value substituted verbatim; with no
    recorded value (e.g. the event was a click) it goes DORMANT instead of shipping the probe."""
    probe_s = str(probe)
    if probe_s not in step:
        return step, None
    if real_value is None:
        return None, step
    return step.replace(probe_s, real_value), None


def _recipe_dormant(indent: str, step: str, why: str) -> str:
    return '%s#   backup: %s' % (indent, annotate(step.strip(), why))


def _body(row: dict, rendered: str, entry: dict | None, _used: list | None = None) -> str | None:
    """Our proposed line for this row and this recorded action, or '' to record nothing, or None
    to let the recorder's own line stand. The shape mirrors `build_override._our_line_body`, with
    one difference that is the whole point: there are no live verdicts here, so the LABEL form is
    what the parser proposes and the xpath is the backstop -- never a silent downgrade to xpath
    because a keyword was measured bad (that knowledge only exists in a review).

    `_used` is an optional out-param (CH-B B1.d): when the returned body actually came from
    `entry`'s recipe (rules 2/5/11), `entry` is appended to it, so a caller (`_compose_body`) can
    stamp the line `# recipe: <name>` instead of the parser's `UNVERIFIED` note. Every existing
    caller omits it and is unaffected -- this is purely additive."""
    cells = _cells(rendered)
    action = cells[0] if cells else ''
    value = cells[-1] if len(cells) >= 3 else None
    fam = row.get('family_corrected') or row.get('element_type')
    label = _label_of(row)
    # No numeric anchor is composed here, ever (F189): the parser's index is a description of
    # the CAPTURE and the live decision belongs to `live_disambiguation` in the driver layer.
    anchor = None
    xp = _xp_of(row)
    c0 = (row.get('calls') or [{}])[0] or {}
    kw = row.get('keyword_corrected') or c0.get('keyword')

    # 1. the recorder's focus/blur noise on a field: its ClickText of the current value and its
    #    VerifyText of the next field's value. The TypeText that follows carries the intent.
    if fam in FILL_FAMILIES and action in NOISE_ACTIONS and not (fam == 'dual_listbox'):
        return ''

    # 1b. the SAME focus click arriving by the OTHER door. The safety net posts a SYNTHETIC click
    #    for an element the stock recorder wrote no line for at all (`rendered` is '', so
    #    `action` is ''), and on a fill-family control that click is the focus click of rule 1:
    #    the user clicked the field because they are about to TYPE in it, and the TypeText that
    #    follows carries the whole intent. Rule 3 used to answer it with an xpath ClickElement, so
    #    every filled field cost a `ClickElement    xpath\=//input[@placeholder="..."]` line
    #    immediately above its own TypeText -- 7 of the 33 lines the user recorded on fsc7f,
    #    2026-09-19 (the frozen pane, decisions 1/3/7/12/17/24/29).
    #    Rule 9 is untouched: a RENDERED click on a combobox or lookup opens a list and is a real
    #    step, and it never reaches here because its action is `ClickElement`, not ''.
    if action == '' and fam in FILL_FAMILIES:
        return ''

    # 2. a dual listbox: the option the user clicked, exact text -- the library's recipe, rendered
    #    with the clicked text as the parameter (its move-right and read-back are the next lines).
    if fam == 'dual_listbox' and action in ('ClickText', 'VerifyText') and len(cells) >= 2:
        if entry:
            line = _recipe_first_action(entry, row, cells[1])
            if line:
                if _used is not None:
                    _used.append(entry)
                return line
        return RT._rf('ClickText', cells[1], partial_match='False')

    # 3. a synthetic click on a textless control: the recorder emits nothing, our own listener
    #    posts the event with no rendered line. Only an xpath can name it.
    if action == '':
        return RT._rf('ClickElement', RT._xp_arg(xp)) if xp else None

    # 4. a control the parser could not name: the xpath is the only honest answer.
    if not label and not c0.get('locator'):
        if xp and action in CLICK_ACTIONS:
            return RT._rf('ClickElement', RT._xp_arg(xp))
        if xp and action in ('TypeText', 'TypeSecret') and value is not None:
            return RT._rf('TypeText', RT._xp_arg(xp), value)
        return None

    # 5. typing into a field the LIBRARY already has a verified recipe for: that recipe's own
    #    action line, rendered with this row's value and D4's anchor slot. The recipe is the form
    #    that was MEASURED working on a real page (`reactive-input-clear-then-verify`'s clear key,
    #    `clarity-lookup`'s timeout=40), so it outranks the generic rung -- and it is what
    #    `review_table.robot_call` renders for the same row, which has put the recipe ahead of its
    #    keyword dispatch since the library landed. Until 2026-09-18 this branch order was the
    #    other way round here, so the review exporter and the composer answered two different lines
    #    for every recipe-bearing fill control (ledger F50).
    if fam in FILL_FAMILIES and action in ('TypeText', 'TypeSecret') and value is not None and entry:
        line = _recipe_first_action(entry, row, value)
        if line:
            if _used is not None:
                _used.append(entry)
            return line

    # 6. typing into a field: the generic rung, and the fallback for a row with no recipe
    if fam in FILL_FAMILIES and action in ('TypeText', 'TypeSecret') and value is not None:
        if label:
            return RT._rf('TypeText', label, value, anchor=anchor)
        return RT._rf('TypeText', RT._xp_arg(xp), value) if xp else None

    # 7. a checkbox
    if fam in ('checkbox', 'radio') and action in CLICK_ACTIONS:
        if label:
            return RT._rf('ClickCheckbox', label, 'on', anchor=anchor)
        return RT._rf('ClickElement', RT._xp_arg(xp)) if xp else None

    # 8. a native select
    if fam == 'dropdown' and action == 'DropDown' and value is not None:
        if label:
            return RT._rf('DropDown', label, value, anchor=anchor)
        return RT._rf('DropDown', RT._xp_arg(xp), value) if xp else None

    # 9. a CLICK on a field the parser only knows how to FILL (opening a combobox, a lookup or a
    #    multi-select). The keyword rung describes filling it; the click is the xpath's job.
    if fam in FILL_FAMILIES and action in ('ClickElement', 'ClickItem', 'Click'):
        if xp:
            return RT._rf('ClickElement', RT._xp_arg(xp))
        return RT._rf('ClickText', label, anchor=anchor, partial_match='False') if label else None

    # 10. a button, link or tab
    if action in CLICK_ACTIONS:
        if kw == 'ClickItem' and c0.get('locator'):
            return RT._rf('ClickItem', c0['locator'], tag=(row.get('tag_corrected') or c0.get('tag') or row.get('tag')),
                          anchor=anchor, partial_match='False')
        if label:
            return RT._rf('ClickText', label, anchor=anchor, partial_match='False')
        if xp:
            return RT._rf('ClickElement', RT._xp_arg(xp))

    # 11. nothing of ours fits the recorded action: a verified library recipe for this control, if
    #     the library has one; otherwise the recorder's line stands.
    if entry:
        line = _recipe_first_action(entry, row, value)
        if line and _used is not None:
            _used.append(entry)
        return line
    return None


# ----------------------------------------------------------------------------- the OmniStudio pair
# An OmniScript combobox is TWO stock recorder events for ONE intent: a click on the combobox's own
# input (which the stock recorder writes as a ~1,200-character positional `ClickElement
# /html[1]/body[1]/...`) and then a `ClickText <option>` on an `li` inside the listbox it opened.
# The job library already owns that intent as one keyword -- CRTPagePatterns
# `resources/garzai_omni.robot` -> `Omni Select    <key-or-label>    <option>` -- which scopes the
# option to THIS combobox's own listbox (`aria-controls`) and drives the full pointer sequence a
# bare .click() is measured not to commit. The two stock lines are kept as dormant `#   backup:`
# lines so a reader who wants them can still have them: `Omni Select` resolves its first argument
# through `keywords_omni.__host` (data-omni-key, then data-element-label, then aria-label, then
# placeholder), and whether the RENDERED label reaches the host on a given script is a live
# question this module cannot answer -- COULD-NOT-CHECK until a run says so, which is exactly what
# the backups are for.
OMNI_PAIR_WINDOW_S = 8.0
_OMNI_COMBOBOX = 'runtime_omnistudio_common-combobox'
_OMNI_TYPEAHEAD = 'runtime_omnistudio_common-typeahead'
_OMNI_ANY = 'runtime_omnistudio'


def _paths(*parts) -> str:
    return '\n'.join(str(p or '') for p in parts)


def omni_combobox_opener(rendered: str, *xpaths, family: str | None = None) -> bool:
    """True when this event is the CLICK that opens an OmniScript combobox's listbox.

    A rendered click (never a synthetic one -- the safety net's focus click on the same input is
    rule 1b's business), on a fill-family control, whose own path runs through a
    `runtime_omnistudio_common-combobox` host."""
    cells = _cells(rendered)
    if not cells or cells[0] not in ('ClickElement', 'ClickItem', 'Click'):
        return False
    if family is not None and family not in FILL_FAMILIES:
        return False
    return _OMNI_COMBOBOX in _paths(*xpaths)


def omni_combobox_option(rendered: str, *xpaths) -> bool:
    """True when this event is the `ClickText <option>` on an `li` of an OmniScript combobox's
    own listbox. The `li` is what separates a real option from any other text in the container."""
    cells = _cells(rendered)
    if len(cells) < 2 or cells[0] != 'ClickText':
        return False
    blob = _paths(*xpaths)
    return _OMNI_COMBOBOX in blob and '/li[' in blob


def _host_prefix(host: str, *xpaths) -> str | None:
    """The element path up to and INCLUDING its `<host>[n]` segment, or None when no such host is
    on the path. Two controls of the same kind on one page differ EARLIER than that segment
    (`omniscript-select[2]` vs `omniscript-select[5]`), so the prefix names the instance."""
    for xp in xpaths:
        s = str(xp or '')
        # the host SEGMENT (`/<host>[n]`), never a longer tag that starts with the same letters:
        # `/lightning-base-combobox-item[3]` on an option path is not the `lightning-base-combobox`
        # host, and a bare `rfind('/' + host)` matched it (measured in this build's own test)
        i = s.rfind('/' + host + '[')
        if i < 0:
            continue
        j = s.find('/', i + 1)
        return s[:j] if j > 0 else s
    return None


def omni_combobox_prefix(*xpaths) -> str | None:
    """The held combobox INSTANCE's own path prefix (challenge 2026-09-19b case 9b)."""
    return _host_prefix(_OMNI_COMBOBOX, *xpaths)


def omni_date_picker_prefix(*xpaths) -> str | None:
    """The held date picker INSTANCE's own path prefix (challenge 2026-09-19b case 5a)."""
    return _host_prefix(_OMNI_DATE_PICKER, *xpaths)


def omni_same_host(prefix: str | None, *xpaths, host: str = _OMNI_COMBOBOX):
    """TRI-STATE: True (this event is inside the same widget instance the hold named), False (it
    is plainly a DIFFERENT instance), None (COULD-NOT-CHECK -- one side carries no prefix, so the
    caller keeps its previous behaviour and says so). Never collapses the third into the first."""
    mine = _host_prefix(host, *xpaths)
    if not prefix or not mine:
        return None
    return prefix == mine


def omni_dormant(text: str, indent: str = '    ') -> str:
    """One dormant `#   backup:` line, for a caller outside this module (the generated library's
    placeholder-pick branch, which keeps the OPEN click held and banks only the pick)."""
    return _dormant(indent, text)


def omni_typeahead_shape(rendered: str, *xpaths) -> bool:
    """The typeahead's opener, for the record. A Type Ahead Block opens its listbox on TYPING, not
    on a click (`Omni Typeahead`'s own [Documentation]), so its two events are NOT this pair's
    shape and nothing here composes one."""
    return _OMNI_TYPEAHEAD in _paths(*xpaths)


def omni_label(label: str | None) -> str:
    """The label a person reads, without the required-field marker the page renders in front of
    it (`*Phone Type` -> `Phone Type`)."""
    return re.sub(r'\s+', ' ', str(label or '')).strip().strip('*').strip()


# The option a listbox offers for "nothing chosen". Picking one is NOT a step: the field ends where
# it began. Measured live on fsc7f, 2026-09-19 13:13 (build n, run 5): `Omni Select    Salutation
# -- No Value --` FAILED -- `omni_select` looks for the option's own commit and the control never
# leaves its empty state. The pair composes nothing and the HELD open click is dropped with it
# (clicking a combobox open and picking nothing is not a step either); both stock lines are kept as
# dormant backups, so nothing the user did is lost.
OMNI_PLACEHOLDER_OPTIONS = ('-- no value --', '--none--', '-- none --', 'none',
                            'select an option', 'select...', 'select', '--select--',
                            '-- select --', '--select an option--')


def omni_placeholder_option(option: str | None) -> bool:
    """True when this option is the listbox's own "nothing chosen" entry."""
    o = re.sub(r'\s+', ' ', str(option or '')).strip()
    if not o:
        return True
    return o.casefold() in OMNI_PLACEHOLDER_OPTIONS


def omni_open_click_line(label: str | None, stock_open: str) -> tuple[str, str]:
    """(the combobox OPEN click, why) in the form a person can read.

    The user, 2026-09-19 (run 5): "Why are absolute paths coming up as backup options?" The stock
    recorder writes the open click as ~1,200 characters of positional
    `ClickElement /html[1]/body[1]/...`, which is a generated path by every rule in the locator
    doctrine. When the descriptor knows the control's LABEL the honest backup is the same
    label-form xpath the fill backups already carry; the positional line survives only when there
    is no label at all, because then it is the only handle there is."""
    lab = omni_label(label)
    if not lab:
        return (stock_open or '').strip(), 'no label on the combobox: the positional stock line is the only handle'
    xp = '//label[normalize-space(.)=%s]/following::input[1]' % RT._lit(lab)
    return RT._rf('ClickElement', RT._xp_arg(xp)), 'label form from the descriptor label %r' % lab


def _dormant(indent: str, text: str) -> str:
    return '%s#   backup: %s' % (indent, annotate((text or '').strip(), 'stock recorder line, unverified'))


# ---------------------------------------------------------------- the backup LADDER (F224)
# The user, 2026-09-20, on finding a ~1,200-character positional path still standing as a backup:
#
#   "Think of the attack formation that we send in, in an RTS like StarCraft. You put your
#    strongest units in the front, your ultralisks. They take the most hits. Those are keywords.
#    We take the next strongest as the next line... The second backup should be our next
#    strongest locator, which should NEVER be an absolute XPath. ... While yes, it should pick up
#    the individual actions picked up there, those individual actions should be BEST PRACTICE,
#    not strictly absolute XPath stuff picked up by the recorder."
#
# So a dormant backup is not "whatever the stock recorder said". It is the same gesture expressed
# at the strongest rung that still names the control, and a rung the locator doctrine calls a
# generated path is dropped whenever ANY better rung survives. Nothing the user did is lost --
# the ACTION is still there, in a form a person would have written by hand.
#
# This does NOT retire F151 ("every stock line the pair absorbed is its own backup"): the set of
# GESTURES is unchanged, only the FORM each one is written in. The positional line survives alone,
# annotated, when there is no label and therefore no better handle -- which is the tri-state rule,
# not an exception to this one.
LADDER_KEYWORD = 1           #: ClickText / TypeText / PickList -- a person's own words. The ultralisk.
LADDER_RELATIVE_XPATH = 2    #: //label[...]/following::... -- anchored to something a person sees.
LADDER_POSITIONAL = 3        #: /html[1]/body[1]/... -- a generated path. Never a locator (CLAUDE.md).

#: rooted at the document element -- the shape Chrome's own "copy full xpath" produces, and what
#: the CRT recorder writes today.
_POSITIONAL_ROOT_RE = re.compile(r'(?:xpath\s*=\s*)?/+html(?:\[\d+\])?/', re.I)
#: one xpath step: a node name, optionally one predicate.
_STEP_RE = re.compile(r'/([A-Za-z_][\w.:-]*)(\[[^\]]*\])?')
#: a predicate that carries no information a PERSON could have written -- absent, or a bare index.
_BARE_PREDICATE_RE = re.compile(r'^\[\d+\]$')


def _looks_generated(body: str) -> bool:
    """A long chain of steps whose predicates are all bare indices is a GENERATED path, whatever
    it is rooted at.

    Rooting at /html is not the defining property, it is just the common one. An app that mounts
    its tree elsewhere, or a recorder that trims the root, produces
    `/div[2]/section[1]/slot[1]/input[1]` -- identically brittle and identically unreadable. This
    is deliberately framework-agnostic: it asks only whether the locator names anything a person
    could point at, which is the locator doctrine's own test for a generated value."""
    steps = _STEP_RE.findall(body)
    if len(steps) < 4:
        return False
    bare = sum(1 for _name, pred in steps if not pred or _BARE_PREDICATE_RE.match(pred))
    return bare >= max(4, int(0.8 * len(steps)))


def locator_rung(line: str) -> int | None:
    """Which rung of the backup ladder one composed line sits on, or None when it is blank.

    Positional beats relative beats keyword only in VERBOSITY; the ladder is the other way up.
    A line carrying a generated path is LADDER_POSITIONAL however it is written and wherever it is
    rooted; anything else naming an xpath is relative; a line with no xpath at all addresses the
    control the way a person reads it."""
    body = (line or '').strip()
    if not body:
        return None
    if _POSITIONAL_ROOT_RE.search(body) or _looks_generated(body):
        return LADDER_POSITIONAL
    if '//' in body or re.search(r'xpath\s*=', body, re.I):
        return LADDER_RELATIVE_XPATH
    return LADDER_KEYWORD


#: what a rung IS, said honestly. A composed rung is not a stock recorder line and must not claim
#: to be one -- `_dormant`'s old fixed note put "stock recorder line" on lines this module wrote
#: itself, which is a provenance claim the reader would act on.
STOCK = 'stock recorder line, unverified'
COMPOSED_KEYWORD = 'keyword form, unverified: composed from the label'
COMPOSED_XPATH = 'xpath form, unverified: composed from the label'


def ladder_dormants(indent: str, rungs) -> list:
    """The dormant `#   backup:` lines for one absorbed gesture, in RECORDED ORDER, with every
    positional line dropped WHEN A BETTER RUNG SURVIVES.

    `rungs` is a sequence of (line, note) pairs, or a bare line meaning `STOCK`. The order is the
    order the person acted in -- that is what makes the block readable and is F151's point. The
    ladder decides MEMBERSHIP, never order."""
    pairs = []
    for item in rungs:
        line, note = item if isinstance(item, tuple) else (item, STOCK)
        if (line or '').strip():
            pairs.append((locator_rung(line), line, note))
    if any(r is not None and r < LADDER_POSITIONAL for r, _l, _n in pairs):
        pairs = [(r, l, n) for r, l, n in pairs if r != LADDER_POSITIONAL]
    return ['%s#   backup: %s' % (indent, annotate((l or '').strip(), n)) for _r, l, n in pairs]


def annotate(line: str, note: str) -> str:
    """Append a note to a composed line AS A ROBOT COMMENT CELL, never as a bare cell. F196 (the
    user, 2026-09-20): a dormant backup ending in `   (xpath form, unverified: parser proposal)`
    stopped being runnable the moment its `Comment    backup:` prefix was removed -- the bare
    parenthesised cell became TypeText's third argument. 2,267 of 2,419 dormant lines in the n9
    goldens had that tail. A line that already carries a `#` comment gets the note folded into it."""
    line = (line or '').rstrip()
    if '    #' in line or line.lstrip().startswith('#'):
        return '%s; %s' % (line, note)
    return '%s    # %s' % (line, note)


def open_click_keyword_form(label: str | None) -> str:
    """The KEYWORD-form opener for a combobox or picklist -- the rung above the relative xpath.

    F224, the user: "the two backup steps that you would typically use for this ... would be a
    type text and a click text. It should not be an absolute XPath." `ClickText <label>` is the
    line a CRT author writes by hand to open a control, so it is the strongest rung that still
    names the control, and it goes ABOVE the `//label[...]/following::` form rather than
    replacing it -- both are dormant, and a person promoting one wants the readable one first.

    The TYPE-then-pick half of that pair is NOT invented here. When the recording shows the person
    typing to filter the list, that keystroke is already absorbed as `stock_filter` and rides the
    ladder in recorded order; when they did not type, composing a TypeText would be fabricating a
    step they never took, and a picklist with no filter box has nothing to type into."""
    lab = omni_label(label)
    return RT._rf('ClickText', lab) if lab else ''


def omni_pair_lines(label: str | None, option: str, stock_open: str, stock_option: str,
                    indent: str = '    ', stock_filter: str | None = None) -> tuple[str, list]:
    """(the one composed line, the dormant backup lines) for one combobox pick.

    Returns ('', []) when there is no label to name the control with -- a keyword whose first
    argument would be blank is not a proposal, it is a guess, and the stock lines stand instead.

    Returns ('', [backups]) for a PLACEHOLDER pick: nothing is composed AND the held open
    click is dropped too, but every stock line is kept as a dormant backup. The empty line with a
    NON-empty backup list is what tells the caller apart from the no-label case.

    EVERY STOCK LINE THE PAIR ABSORBED IS ITS OWN BACKUP, IN THE ORDER THEY WERE RECORDED (user,
    build n8: "those clicked interactions and typed are the true backups" -- a combobox pick whose
    only backup was one TypeText was not enough). The RAW positional opener line and its
    LABEL-FORM translation are both kept, in that order, when they differ -- `omni_open_click_line`
    used to keep the label form ALONE (2026-09-19 run 5: "why are absolute paths coming up as
    backup options?"), which is right for the PRIMARY backup but wrong for "never drop a stock
    line the pair absorbed": both now stand, dormant, never as a live step. `stock_filter` is the
    typed filter-box keystroke a SENTINEL-armed pick absorbed (F146-3/F146-4, build n8) -- there is
    none for a plain click-only pick (Alt-click or a gesture-free literal), so it is optional and
    slots in between the opener and the option, matching recording order: opener, filter, option."""
    lab = omni_label(label)
    opt = (option or '').strip()
    if not lab or not opt:
        return '', []
    open_line, _ = omni_open_click_line(label, stock_open)
    raw_open = (stock_open or '').strip()
    # F224: recorded order -- opener (raw, then its label form), the typed filter, the option --
    # handed to the ladder, which drops the raw positional opener whenever the label form survives.
    rungs = [(raw_open if raw_open != open_line.strip() else '', STOCK),
             (open_click_keyword_form(label), COMPOSED_KEYWORD),
             (open_line, COMPOSED_XPATH), (stock_filter, STOCK), (stock_option, STOCK)]
    backups = ladder_dormants(indent, rungs)
    if omni_placeholder_option(opt):
        return '', backups
    line = '%s%s    %s' % (indent, RT._rf('Omni Select', lab, opt).strip(), UNVERIFIED)
    return line, backups


# ------------------------------------------------ open-then-choose, EVERY family (Loop 4 item 2)
# Ledger F188 (the user's CRT editor session, fsc7f, 2026-09-20): four comboboxes on one page
# recorded as a raw opening click with no pick, and the Lead modal's own picklists had no one-step
# shape at all. The OmniStudio pair above was the first family; this table is the census of ALL of
# them (`tools/recorder/open_then_choose_census.py` reads it, and so does the composer), and the
# `lightning-base-combobox` rules below are the second family, keyed EXACTLY like the first: on the
# host prefix of the event's own path -- the live describer's control identity -- never on the
# reviewed page key. A recipe bound to a reviewed page (`page_gate`) is what skipped every one-step
# pick on fsc7f; nothing here reads a page key, a row table or a recipe.
#
# `one_step` names the keyword form that EXISTS (CRT QForce / `tools/qforce-lite` / the CRT job
# resources); `could_not_check` names, in words, why a family has no one-step rule yet. A family
# has one or the other, never neither (the test pins it).
PICK_FAMILIES = {
    'omni_combobox': {
        'host': _OMNI_COMBOBOX, 'opener': 'click on the combobox input',
        'option': 'ClickText on an <li> of its own listbox',
        'selected_render': "the input's value (the option text)",
        'one_step': 'Omni Select', 'status': 'composes (build n2+)'},
    'lightning_picklist': {
        'host': 'lightning-base-combobox', 'not_under': ('lightning-grouped-combobox',
                                                          'lightning-lookup'),
        'opener': 'click on <button role=combobox aria-haspopup=listbox> (LWC) or '
                  '<input role=combobox readonly> (older base)',
        'option': 'click on <lightning-base-combobox-item role=option> inside the SAME host',
        'selected_render': "the trigger button's own text / data-value after the listbox closes",
        'one_step': 'PickList', 'status': 'composes (this build)'},
    'lightning_lookup': {
        'host': 'lightning-grouped-combobox',
        'opener': 'click on <input role=combobox>, then a typed filter',
        'option': 'click on <lightning-base-combobox-item> after the server search returns',
        'selected_render': 'a <lightning-pill> replaces the input',
        'one_step': None,
        'could_not_check': 'three stock lines (open, type, pick) and the option list is '
                           'SERVER-rendered after the keystroke; `ComboBox` is the candidate '
                           'keyword and its read-back is the pill, not the input -- next slice'},
    'button_menu': {
        'host': 'lightning-button-menu',
        'opener': 'click on <button aria-haspopup=true>',
        'option': 'click on <lightning-menu-item> / [role=menuitem]',
        'selected_render': 'none (an action fires; nothing is selected)',
        'one_step': None,
        'could_not_check': 'no selected value to read back: the pair is a navigation, and the '
                           'item is not in the DOM until the menu opens, so `ClickText <item>` '
                           'alone cannot run -- needs a `Click Menu Item` keyword first'},
    'app_launcher': {
        'host': 'one-app-launcher-header',
        'opener': 'click on button[title="App Launcher"], then a typed search',
        'option': 'click on the app tile / menu item',
        'selected_render': 'the URL changes to /lightning/app/<id>',
        'one_step': 'LaunchApp', 'status': 'measured ONE step in F188 (`LaunchApp Sales`), '
                                           'composed by the recorder itself'},
    'native_select': {
        'host': 'select', 'opener': 'none (the change event is the whole gesture)',
        'option': '<option>', 'selected_render': "the <select>'s value",
        'one_step': 'DropDown', 'status': 'composes (rule 8)'},
    'aura_picklist': {
        'host': 'forceInputPicklist',
        'opener': 'click on <a role=button aria-haspopup> (uiPicklistLabel beside it)',
        'option': 'click on <a role=option> inside uiMenuList',
        'selected_render': "the anchor's own text",
        'one_step': None,
        'could_not_check': '`pick_list` already resolves the Aura trigger (its 4th tier), but no '
                           'capture in the corpus holds an Aura listbox OPEN (customer-cpq/03 is '
                           'named "picklist-open" and carries 0 role=option) and no walk has driven '
                           'one -- next slice, same hold-and-pair shape'},
    'omni_typeahead': {
        'host': _OMNI_TYPEAHEAD,
        'opener': 'TYPING opens the listbox (no opening click)',
        'option': 'click on an <li>', 'selected_render': "the input's value",
        'one_step': None,
        'could_not_check': 'opens on typing, not on a click, so the opener rule does not apply; '
                           '`Omni Typeahead` exists in the CRT resources and the pair is (type, '
                           'pick) -- next slice'},
    'dual_listbox': {
        'host': 'lightning-dual-listbox',
        'opener': 'click on an option in the left list', 'option': 'the move-right arrow',
        'selected_render': 'the option appears under Selected',
        'one_step': None,
        'could_not_check': 'a multi-step move, not open-then-choose; the reviewed recipe (row 77) '
                           'composes it on the reviewed page only -- out of this item'},
    'date_picker': {
        'host': 'runtime_omnistudio_common-date-picker',
        'opener': 'click on the date input', 'option': 'a day cell',
        'selected_render': "the input's committed value",
        'one_step': 'Omni Date', 'status': 'composes (build n5/n6, `_omni_date_pair`); D19 says a '
                                           'date is TYPED, the picker gesture is still recorded'},
}
_LBC = 'lightning-base-combobox'
_LBC_ITEM = 'lightning-base-combobox-item'
# `--None--` is what a Lightning picklist offers for "nothing chosen"; the OmniStudio list above
# already carries it, and the Lead modal renders exactly that text on every unset picklist.
LBC_PLACEHOLDER_OPTIONS = OMNI_PLACEHOLDER_OPTIONS


def pick_family_of(*xpaths) -> str | None:
    """The open-then-choose family the event's OWN path names, or None. The lookup's grouped host
    wraps a base combobox, so the grouped host is asked first (a base-combobox inside a lookup is
    that lookup's own shadow child, `component_classifier`'s OUTER-wins rule)."""
    blob = _paths(*xpaths)
    if 'lightning-grouped-combobox' in blob or 'lightning-lookup' in blob:
        return 'lightning_lookup'
    if _LBC in blob:
        return 'lightning_picklist'
    if _OMNI_COMBOBOX in blob:
        return 'omni_combobox'
    if _OMNI_TYPEAHEAD in blob:
        return 'omni_typeahead'
    if 'lightning-button-menu' in blob:
        return 'button_menu'
    if 'one-app-launcher' in blob:
        return 'app_launcher'
    if 'lightning-dual-listbox' in blob:
        return 'dual_listbox'
    return None


def lbc_prefix(*xpaths) -> str | None:
    """The `lightning-base-combobox[n]` INSTANCE's own path prefix: the pairing key."""
    return _host_prefix(_LBC, *xpaths)


def lbc_opener(rendered: str, *xpaths, desc: dict | None = None) -> bool:
    """True when this event is the click that opens a standalone Lightning picklist's listbox: a
    click (rendered `ClickText --None--` / `ClickElement ...`, or the safety net's synthetic one)
    on the trigger -- a <button role=combobox> or an <input role=combobox> -- under
    `lightning-base-combobox` with no lookup host above it."""
    if pick_family_of(*xpaths) != 'lightning_picklist':
        return False
    blob = _paths(*xpaths)
    if _LBC_ITEM in blob:
        return False
    cells = _cells(rendered)
    if cells and cells[0] not in ('ClickElement', 'ClickItem', 'Click', 'ClickText'):
        return False
    d = desc or {}
    role = (d.get('role') or '').lower()
    tag = (d.get('tag') or '').lower()
    if role == 'combobox' or (d.get('aria_haspopup') or '').lower() == 'listbox':
        return True
    # no descriptor role: the path's own last segment decides
    last = blob.strip().rsplit('/', 1)[-1]
    return tag in ('button', 'input') or last.startswith(('button[', 'input['))


def lbc_option(rendered: str, *xpaths) -> bool:
    """True when this event is a click on a `lightning-base-combobox-item` (the option)."""
    cells = _cells(rendered)
    if not cells or cells[0] not in ('ClickText', 'ClickElement', 'ClickItem', 'Click'):
        return False
    return _LBC_ITEM in _paths(*xpaths)


def lbc_option_text(rendered: str, desc: dict | None = None) -> str:
    """The option a person chose: the rendered `ClickText` cell first, the describer's text next."""
    cells = _cells(rendered)
    if len(cells) >= 2 and cells[0] == 'ClickText':
        return cells[1].strip()
    d = desc or {}
    return (d.get('text') or d.get('title') or '').strip()


def lbc_open_click_line(label: str | None, stock_open: str) -> tuple[str, str]:
    """(the picklist OPEN click in a form a person can read, why). `*[@role="combobox"]` because
    the trigger is a <button> on LWC pages and an <input> on older base pages; the label's
    `following::` is the same rung the fill backups carry."""
    lab = omni_label(label)
    if not lab:
        return (stock_open or '').strip(), 'no label on the picklist: the stock line is the only handle'
    xp = '//label[normalize-space(.)=%s]/following::*[@role="combobox"][1]' % RT._lit(lab)
    return RT._rf('ClickElement', RT._xp_arg(xp)), 'label form from the descriptor label %r' % lab


def _dormant_note(indent: str, text: str, note: str) -> str:
    """F256 (2026-09-23): the note is a ROBOT COMMENT CELL through `annotate`, never a bare
    parenthesised tail -- the fourth call site of the F196/F203 shape; 7 of 30 dormant lines in
    the user's Session B pane carried `   (opened, no pick recorded -- not a step)` and would have
    become the keyword's next argument the moment `Comment    backup: ` was stripped."""
    return '%s#   backup: %s' % (indent, annotate((text or '').strip(), note))


def pick_open_dormant(label: str | None, stock_open: str, indent: str = '    ',
                      family: str = 'lightning_picklist') -> str:
    """The dormant line an UNPAIRED opener leaves behind (opened and closed, or the hold lapsed):
    the label form when there is a label, the stock line otherwise -- never a live click. A live
    raw opening click is F188's shape: it opened a listbox, chose nothing, and the open listbox
    intercepted the next control."""
    if family == 'omni_combobox':
        body, _ = omni_open_click_line(label, stock_open)
    else:
        body, _ = lbc_open_click_line(label, stock_open)
    return _dormant_note(indent, body or stock_open, 'opened, no pick recorded -- not a step')


def lbc_pair_lines(label: str | None, option: str, stock_open: str, stock_option: str,
                   indent: str = '    ') -> tuple[str, list]:
    """(the one composed `PickList` line, the dormant backups) for one Lightning picklist pick --
    the same contract as `omni_pair_lines`: ('', []) with no label, ('', [backups]) for a
    placeholder pick, and EVERY absorbed stock line dormant in recorded order: the raw opener
    line, its label form, the option click. Each is a complete runnable step once `#   backup: `
    is deleted (F151)."""
    lab = omni_label(label)
    opt = (option or '').strip()
    if not lab or not opt:
        return '', []
    open_line, _ = lbc_open_click_line(label, stock_open)
    raw_open = (stock_open or '').strip()
    # F224: same ladder as omni_pair_lines -- see ladder_dormants.
    rungs = [(raw_open if raw_open != open_line.strip() else '', STOCK),
             (open_click_keyword_form(label), COMPOSED_KEYWORD),
             (open_line, COMPOSED_XPATH), (stock_option, STOCK)]
    backups = ladder_dormants(indent, rungs)
    if omni_placeholder_option(opt):
        return '', backups
    line = '%s%s    %s' % (indent, RT._rf('PickList', lab, opt).strip(), UNVERIFIED)
    return line, backups


# ------------------------------------------------------- the OmniStudio fill (the component tag)
# Measured on the user's SECOND fsc7f run, 2026-09-19 12:17-12:19: the composed pane EXECUTED, every
# click landed, 7 TypeText lines ran and 5 read back correctly. The 2 that did not are both
# OmniStudio MASKED controls, and the failure is the keyword, not the locator:
#   * `TypeText    Date of Birth    09-01-2025    anchor=1` -- the element sits under
#     `runtime_omnistudio_common-date-picker`; the field ended BLANK on the page. That widget only
#     commits a value chosen through its own calendar UI (`Omni Date`'s [Documentation]: a plain
#     native-value write never commits on it).
#   * `TypeText    Phone Number    (555) 111-2244` -- under `runtime_omnistudio_common-masked-input`,
#     which REFORMATS on blur, so a raw string compare cannot confirm it.
# The job library owns both: `Omni Date    <key-or-label>    <YYYY-MM-DD>` drives the calendar, and
# `Omni Type    <key-or-label>    <value>    family=` normalises the read-back per family. So the
# OmniScript COMPONENT TAG in the element's own path routes the keyword -- the same shape as the
# combobox pair, one rung below it -- and the stock TypeText stays as a dormant backup.
_OMNI_DATE_PICKER = 'runtime_omnistudio_common-date-picker'
_OMNI_MASKED_INPUT = 'runtime_omnistudio_common-masked-input'
_OMNI_PLAIN_INPUT = 'runtime_omnistudio_common-input'
# EVERY OmniStudio fill component, widened on the THIRD run (2026-09-19 12:28): the composed
# `TypeText    First Name    ads` ran into a field already holding `ads` and the field ended
# `adsads` -- the recorder itself then captured `TypeText    First Name    adsads` off that input
# 20 s later. TypeText's clear does not clear a `runtime_omnistudio_common-input` (the append class,
# docs/errors/entries/576d7e8859), so the plain OmniScript text input joins the masked ones.
_OMNI_FILL_TAGS = (_OMNI_DATE_PICKER, _OMNI_MASKED_INPUT, _OMNI_PLAIN_INPUT)

# The value's own shape names the family `keywords_omni._normalise_for` compares with. Nothing here
# guesses: a value that looks like neither is plain text and the keyword's own default stands.
_MONEY_RX = re.compile(r'^\s*[$£€]\s*[\d,]+(\.\d+)?\s*$')
_PHONE_RX = re.compile(r'^\s*\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\s*$')
_ISO_RX = re.compile(r'^\s*(\d{4})-(\d{2})-(\d{2})\s*$')
_US_RX = re.compile(r'^\s*(\d{1,2})[-/](\d{1,2})[-/](\d{4})\s*$')

OMNI_TEXT_FAMILY = 'omni-text'


def omni_value_family(value: str) -> str:
    """`omni-currency` / `omni-telephone` / `omni-text` -- the family `Omni Type` normalises the
    read-back with. Read off the VALUE's own shape, because that is the only evidence a recorded
    event carries; anything else is plain text, which is the keyword's own default."""
    v = str(value or '')
    if _MONEY_RX.match(v):
        return 'omni-currency'
    if _PHONE_RX.match(v):
        return 'omni-telephone'
    return OMNI_TEXT_FAMILY


def omni_iso_date(value: str) -> str | None:
    """`Omni Date` takes `YYYY-MM-DD` and the widget commits `MM-DD-YYYY` (its own
    [Documentation]). The recorder writes what the page rendered, which on this script is
    month-first (`1/1/1990`, `09-02-2025`). Anything this cannot read returns None and NOTHING is
    composed -- a date the composer had to guess is not a proposal."""
    v = str(value or '')
    m = _ISO_RX.match(v)
    if m:
        return '%s-%s-%s' % m.groups()
    m = _US_RX.match(v)
    if not m:
        return None
    mo, da, yr = int(m.group(1)), int(m.group(2)), m.group(3)
    if not (1 <= mo <= 12 and 1 <= da <= 31):
        return None
    return '%s-%02d-%02d' % (yr, mo, da)


_MASK_PLACEHOLDER = '_'


def omni_mask_value(value: str) -> tuple[str, str]:
    """(the value to compose, why) for a recorded value that carries MASK PLACEHOLDERS.

    Measured live on fsc7f, run 4 (2026-09-19 12:49): the user typed six digits into the masked
    Phone Number control and the recorder captured the control's RENDERED text mid-entry --
    `TypeText    Phone Number    (666) 453-____` -- which the composer then emitted verbatim. Those
    underscores are the widget's own unfilled slots, not characters anyone typed; replaying them
    types literal `_` into a masked input.

    Each `_` is one unfilled slot, so `digits + underscores` is what the mask wants and `digits` is
    what the user actually entered -- which makes every surviving `_` proof that the value is
    SHORT. Stripping alone would leave `(666) 453-`, whose trailing separator is the mask's own
    furniture around a half-entered number, so the DIGITS are what gets composed (`666453`); the
    stripped form is named in the `why` rather than thrown away. A value that is nothing but
    placeholders returns '' -- there is no value to compose and the stock line stands.

    AN UNDERSCORE IS NOT ALWAYS A MASK. `a_b@c.com`, `Zoo_Text__c`, `First_Name` are ordinary
    values a person typed, and digits-only would destroy them. A `_` is read as a mask placeholder
    only when the value carries NO letter -- the shape every masked control on this script renders
    (`(666) 453-____`, `___-__-____`, `$ __,___.__`)."""
    v = str(value or '')
    if _MASK_PLACEHOLDER not in v:
        return v, ''
    if any(c.isalpha() for c in v):
        return v, ''            # an underscore inside real text is a character, not a slot
    stripped = v.replace(_MASK_PLACEHOLDER, '')
    want = sum(c.isdigit() for c in v) + v.count(_MASK_PLACEHOLDER)
    have = sum(c.isdigit() for c in stripped)
    if not have:
        return '', ('the recorded value is nothing but mask placeholders (%r): there is no value '
                    'to compose and the stock line stands' % v)
    digits = ''.join(c for c in stripped if c.isdigit())
    return digits, ("a half-typed masked input: the recorder captured the widget's own unfilled "
                    'slots (%r); %d of %d digits were entered, so the mask characters are dropped '
                    'and the digits composed (stripped form was %r)' % (v, have, want, stripped))


def omni_fill_line(composed: str, *xpaths, omni_key: str | None = None,
                   omni_key_capped: int | None = None,
                   indent: str = '    ') -> tuple:
    """(the Omni line, the dormant backup, why) for one composed fill on an OmniStudio control, or
    ('', '', why) when nothing should change.

    `composed` is the line the composer ALREADY decided -- the one that would otherwise run -- so
    the label and the value are the parser's own, not the placeholder the recorder wrote.
    `omni_key` is the element's `data-omni-key` (= `OmniProcessElement.Name`), which is what
    `keywords_omni.__host` resolves and therefore what both keywords take as their first argument.
    Without it there is no honest proposal here and the stock line stands -- said out loud in the
    `why`, never as a silent miss."""
    cells = _cells(composed)
    if len(cells) < 3 or cells[0] not in ('TypeText', 'TypeSecret'):
        return '', '', 'not a composed fill line'
    value = cells[2]
    blob = _paths(*xpaths)
    tag = next((t for t in _OMNI_FILL_TAGS if t in blob), None)
    if tag is None:
        return '', '', 'no OmniStudio fill component in the element path'
    key = str(omni_key or '').strip()
    if not key:
        if omni_key_capped:
            # THE THIRD STATE (challenge 2026-09-19b case 12). `omniKey` gave up at the hop cap;
            # the key may well exist above it. Saying "carries no data-omni-key" here is a false
            # statement of fact, and it is the elide-without-disclosure shape the previous cap
            # (`h < 8`) already cost a whole run to.
            return '', '', ('an OmniStudio %s: the data-omni-key was NOT REACHED within %s hops '
                            '(the walk stopped on its own cap -- this is NOT the same fact as an '
                            'element that carries no key); the stock TypeText line stands'
                            % (tag.rsplit('-', 1)[-1], omni_key_capped))
        return '', '', ('an OmniStudio %s, but the element carries no data-omni-key: the stock '
                        'TypeText line stands' % tag.rsplit('-', 1)[-1])
    value, mask_why = omni_mask_value(value)
    if not value:
        # AN ALL-PLACEHOLDER MASK IS NOT "LEAVE THE LINE ALONE" (challenge 2026-09-19b case 7).
        # The line left alone is the stock `TypeText Phone Number (___) ___-____`, which replays
        # eleven literal underscores into a masked input -- the exact hazard the mask rule exists
        # to stop, handed through on the input where the evidence is strongest. So it composes
        # NOTHING and the stock line survives as a DORMANT backup: the shape the placeholder PICK
        # already uses (an empty line with a non-empty backup is the caller's signal).
        return '', _dormant(indent, composed), mask_why
    if tag == _OMNI_DATE_PICKER:
        iso = omni_iso_date(value)
        if not iso:
            # A SENTINEL IS NOT AN UNREADABLE DATE (user, 2026-09-19: "a date is GENERATED by a
            # value typed into the date field, never by the picker -- I was just recording the
            # date picker before, which is not ideal"). Typing `asdf` or `@@date+30` into a date
            # input is the PRIMARY way a generated date is authored, and it has to survive this
            # branch: the value is a placeholder the generated-data rule replaces one step later.
            # Dropping it here left the stock `TypeText` standing on a widget where a typed value
            # is measured NOT to commit (the field ended blank, fsc7f 2026-09-19 12:17), so the
            # generated date would never have landed.
            if sentinel_spec(value)[0] is not None:
                line = RT._rf('Omni Date', key, value)
                return ('%s%s    %s' % (indent, line.strip(), UNVERIFIED), _dormant(indent, composed),
                        'OmniStudio date picker with a typed SENTINEL: routed to Omni Date (a typed '
                        'value never commits on this widget) and held for the generated-data rule, '
                        'which replaces the sentinel with a ${variable} in ISO form')
            return '', '', 'a date-picker control, but %r is not a date this can read' % value
        line = RT._rf('Omni Date', key, iso)
        why = ('OmniStudio date picker: a typed value never commits on it '
               '(Omni Date drives the calendar)')
    elif tag == _OMNI_MASKED_INPUT:
        line = RT._rf('Omni Type', key, value, omni_value_family(value))
        why = 'OmniStudio masked input: it reformats on blur (Omni Type normalises the read-back)'
    else:
        line = RT._rf('Omni Type', key, value, omni_value_family(value))
        why = "OmniStudio text input: TypeText's clear does not clear it (the value APPENDS)"
    if mask_why:
        why = '%s; %s' % (why, mask_why)
    backup = _dormant(indent, composed)
    return '%s%s    %s' % (indent, line.strip(), UNVERIFIED), backup, why


# ------------------------------------------------- the OmniStudio date picker's OPENING click
# The user, on run 8 (2026-09-19 14:17): "the birthdate thing is not capturing the initial click
# to find the dates, so it's only showing the click to select the date".
#
# MEASURED LIVE on fsc7f the same day (slot fsc7f@probe, `/lightning/n/GarzAI_Omni_Launcher`,
# `FSC_DL_v1_Date_Of_Birth`): from a CLOSED picker, a mousedown/mouseup/click on
# `input[data-id=date-picker-slds-input]` takes the widget's state from `null` to
# `{open: true, month: 'September', year: '2026'}`. **A click on a date input is an OPENING
# click, not a focus click.** Rule 1b had been suppressing it as recorder noise -- correct for
# an ordinary text field, wrong for this widget -- so the pane kept the day-cell click alone
# (`ClickText    10    anchor=September`), which on a fresh page has no calendar to click into
# and failed with `Could not find text using web recognition`.
#
# So the date picker gets the same three moves the combobox already has: the opening click is
# HELD, the day-cell pick joins it, and ONE `Omni Date` line comes out with both stock lines as
# dormant backups. Two things the calendar itself decided:
#   * the YEAR IS NOT IN THE HEADER. The widget's `h2[data-id=selected_month]` renders
#     `September` and nothing else; the year lives in a `<select>` and in each day cell's own
#     `aria-label`. So a day-cell click can only name the full date when the descriptor carried
#     that cell's aria-label; otherwise the date comes from the input's own value afterwards,
#     which is the authoritative read-back anyway.
#   * the SELECTED cell's aria-label carries a ` Selected` suffix (`Mon Sep 22 2025 Selected`),
#     measured verbatim on the live grid. Anything reading these labels matches on the DATE
#     PREFIX -- an exact compare is the bug that made `omni_date` fail on the one date the field
#     already held.
_DAY_CELL_RX = re.compile(
    r'^(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+'
    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+(\d{4})\b')
_DAY_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def omni_date_opener(rendered: str, *xpaths, family: str | None = None) -> bool:
    """True when this event is the click that OPENS an OmniStudio date picker's calendar.

    Unlike the combobox opener this accepts a SYNTHETIC click (`rendered` empty). On the user's
    recording the opening click arrived by the safety net with no stock line at all, which is
    exactly why rule 1b swallowed it."""
    cells = _cells(rendered)
    if cells and cells[0] not in ('ClickElement', 'ClickItem', 'Click', 'ClickText'):
        return False                       # a TypeText on the same input is the FILL, not the open
    if family is not None and family not in FILL_FAMILIES:
        return False
    blob = _paths(*xpaths)
    return _OMNI_DATE_PICKER in blob and '/table[' not in blob and '/td[' not in blob


def omni_day_cell(rendered: str, *xpaths) -> bool:
    """True when this event is the DAY-CELL click inside an OmniStudio calendar: a click whose own
    path runs through the date picker AND through the day grid (`table`/`tr`/`td`)."""
    cells = _cells(rendered)
    if cells and cells[0] not in ('ClickText', 'ClickElement', 'ClickItem', 'Click'):
        return False
    blob = _paths(*xpaths)
    if _OMNI_DATE_PICKER not in blob:
        return False
    return any(seg in blob for seg in ('/table[', '/tr[', '/td['))


def omni_day_cell_date(rendered: str, descriptor: dict | None = None) -> tuple:
    """(ISO date, why) read off a day cell's OWN `aria-label`, or (None, why).

    The widget generates that label with `Date().toDateString()` -- `Thu Sep 10 2026` -- and
    appends ` Selected` to whichever cell is currently selected, so the match is on the DATE
    PREFIX and never an exact compare. When no such label reached the descriptor the year is
    simply not knowable from the calendar (its header renders the month alone), and this says so
    rather than guessing one."""
    desc = descriptor or {}
    for field in ('aria_label', 'title', 'text', 'label'):
        m = _DAY_CELL_RX.match(re.sub(r'\s+', ' ', str(desc.get(field) or '')).strip())
        if m:
            mon, day, yr = m.groups()
            return ('%s-%02d-%02d' % (yr, _DAY_MONTHS.index(mon) + 1, int(day)),
                    "the day cell's own aria-label %r" % desc.get(field))
    cells = _cells(rendered)
    day = cells[1] if len(cells) >= 2 else ''
    return (None, "the calendar header renders the month alone (%r) and no day-cell aria-label "
                  "reached the descriptor, so the year is not knowable here: the date comes from "
                  "the input's own value after the pick" % (desc.get('label') or day))


def omni_date_pair_lines(label: str | None, omni_key: str | None, iso: str | None,
                         stock_open: str, stock_day: str, indent: str = '    ') -> tuple:
    """(the one composed `Omni Date` line, the dormant backup lines) for one calendar pick.

    ('', [backups]) when the date is known but the element carries no `data-omni-key`, or when
    the date could not be read: nothing is composed and both stock lines survive as backups --
    the same tri-state the combobox pair already keeps."""
    open_line, _ = omni_open_click_line(label, stock_open)
    backups = [_dormant(indent, s) for s in (open_line, stock_day) if (s or '').strip()]
    key = str(omni_key or '').strip()
    if not key or not iso:
        return '', backups
    return '%s%s    %s' % (indent, RT._rf('Omni Date', key, iso).strip(), UNVERIFIED), backups


def verify_backup(composed: str, indent: str = '    ') -> str:
    """The dormant read-back line that belongs AFTER a fill step, or '' when this is not a fill.

    THE STEP IS THE ACTION, THE VERDICT IS A SEPARATE LINE (user, 2026-09-19). The composer does
    not lean on validation buried inside a keyword: it emits the assertion a person can un-comment,
    quoting the label and the value as they read them on the page. `Verify Input Value` is the
    job library's own read-back-only keyword (`resources/garzai_typetext_override.robot`:
    `[Arguments] ${locator} ${expected} ${anchor}=1`) -- GetInputValue + Values Match, no typing and
    no repair."""
    cells = _cells(composed)
    if len(cells) < 3 or cells[0] not in ('TypeText', 'TypeSecret'):
        return ''
    return '%s#   verify: %s' % (indent, RT._rf('Verify Input Value', cells[1], cells[2]).strip())


# ------------------------------------------------------- the typeable combobox (F192 fix 2)
COMBOBOX_MARK = 'gz_family=combobox'


def descriptor_is_typeable_combobox(desc) -> tuple[bool, str]:
    """(True, why) when the descriptor says the typed-into control is a COMBOBOX with a typeable
    input -- an `<input role="combobox">` (lightning-base-combobox with allow-input, the
    OmniStudio typeahead/combobox input), or a family the review/parser already calls
    `combobox` / `picklist`.  The page-side `familyOf` folds every `role=combobox` input into
    `input_field`, so the ROLE is the evidence here, not the family."""
    d = desc or {}
    tag = str(d.get('tag') or '').casefold()
    role = str(d.get('role') or '').casefold()
    fam = str(d.get('family') or '').casefold()
    if tag in ('input', '') and role == 'combobox':
        return True, "the descriptor's role is combobox on a typeable input"
    if fam in ('combobox', 'picklist') and tag not in ('button', 'a'):
        return True, "the descriptor's family is %r" % fam
    if role == 'combobox':
        return False, 'role combobox on a <%s>: a button trigger is clicked, never typed into' % tag
    return False, 'not a combobox (tag %r, role %r, family %r)' % (tag, role, fam)


def combobox_fill_line(composed: str, desc, indent: str = '    ') -> tuple[str, str, str]:
    """(the marked fill line, its dormant verify line, why) for a `TypeText` whose descriptor is
    a typeable combobox; ('', '', why) for everything else, a non-fill, or a line already marked.

    F188 CAUGHT-BUG 4 (fsc7f, 2026-09-20): `Phone Type` is a combobox with a typeable input.
    The composer routed it as text, the TypeText override read the typed stamp back while the
    input still had focus (VERIFIED-PASS), and the control cleared the invalid value on blur --
    the vacuous green.  The mark `gz_family=combobox` tells the shipped TypeText override
    (resources/garzai_typetext_override.robot) to read back the SELECTED OPTION AFTER BLUR --
    never the input's text -- and to say COULD-NOT-CHECK naming the control when that is blank.
    The dormant verify line is `Verify Combobox Selection`, the same read-back as a step.  The
    mark is a trailing cell, so `replace_value_cell` (the generated-data rewrite) keeps it."""
    if not isinstance(composed, str) or not composed.strip():
        return '', '', 'nothing composed'
    cells = _cells(composed)
    if len(cells) < 3 or cells[0] not in ('TypeText', 'TypeSecret'):
        return '', '', 'not a fill line'
    if any(c.strip() == COMBOBOX_MARK for c in cells[3:]):
        return '', '', 'already marked'
    is_combo, why = descriptor_is_typeable_combobox(desc)
    if not is_combo:
        return '', '', why
    ind = composed[: len(composed) - len(composed.lstrip())] or indent
    line = ind + '    '.join(_insert_before_note(list(cells), COMBOBOX_MARK))
    verify = '%s#   verify: %s' % (ind, RT._rf('Verify Combobox Selection', cells[1], cells[2]).strip())
    return line, verify, 'typeable combobox: %s -- the read-back is the selected option after blur' % why


# ============================================================ generated data from a typed sentinel
# "Every value is hard-coded, so the second run fails on duplication rules." (user, 2026-09-19 --
# docs/PLAN-OFFLINE-REPLAY-2026-09-19.md, "Backlog: generated data from a typed sentinel").
#
# The typed value is the HOTKEY. A recorded fill whose value is a SENTINEL composes a VARIABLE line
# above the fill, and the fill uses the variable, so a later verify line can reuse the same value.
#
# BUILD n10 (2026-09-20, the user, twice): "don't like the friggin dates and crazy reinvention of
# randomized data. That shit is way too complicated and FakerLibrary does so well already as long
# as it's treated properly." So the variable line is FakerLibrary's own keyword, chosen by the
# field's MEANING -- `${lead_first_name}=    FakerLibrary.First Name` -- and NO run stamp sits in
# any visible value. Traceability is `Gz Generated Tally` (every generated value, at the end) and
# `Gz Cleanup Hint` (the SOQL a person runs: CreatedById + CreatedDate = TODAY). The argument
# grammar (`@@date+N`, `@@unique <base>`, `@@int a b`, `@@text n`) is RETIRED; a retired form is
# disclosed as MALFORMED, never silently generated.
#
# THE SENTINEL TABLE IS DELIBERATELY SMALL: `asdf`, `@@pick`, and one plain override with no
# arguments, `@@<provider name>` (`@@company`, `@@first name`, `@@date`). `asdfasdf`, `test`, `qwer`
# are NOT sentinels: a person types those as real data, and a false positive would silently
# replace a value they meant -- the same class of quiet wrong answer as
# `get_field_value("Stage") -> "Stage"`.
#
# Click-recorded controls (a picklist option, a calendar day) cannot carry a typed sentinel, so they
# get two markers instead: an ALT-CLICK on the option or the day ("any valid value here"), and -- on
# every pick and every date, gesture or not -- a dormant `Comment    generate:` pair a person
# promotes by deleting two cells, exactly like a backup line.
SENTINEL_BARE = 'asdf'

# Values that LOOK like a sentinel and are NOT. Named so the table is a table, not a regex nobody
# can argue with; the test file asserts every one of them stays a literal.
SENTINEL_NEAR_MISSES = ('asdfasdf', 'test', 'qwer', 'asdfg', 'asd', 'aaaa', 'x', 'ASDF1')

# The forms build n7-n9 accepted and build n10 retired. Named so the refusal can quote them.
RETIRED_GRAMMAR = ('@@date+N', '@@date-N', '@@unique <base>', '@@int <min> <max>', '@@text <len>')

# A picklist's option list is ELIDED on the composed line when it is long -- and the `why` always
# says how many were dropped and where the whole list lives (an instrument may elide; it may never
# elide SILENTLY -- CLAUDE.md, tools/guards/no_silent_truncation.py).
PICK_OPTION_CAP = 12

FAKER_LIB = 'FakerLibrary'
_FAKER = {'inst': None, 'error': None}


def provider_keyword(name) -> str:
    """`first name` / `first_name` / `First Name` -> `First Name`: Robot's own rendering of a
    FakerLibrary keyword (the dynamic library title-cases a snake_case method and turns `_` into
    a space -- faker_classify.py's header, verified against the installed library)."""
    return ' '.join(w.capitalize() for w in re.sub(r'[_\s]+', ' ', str(name or '')).strip().split())


def provider_known(keyword) -> tuple:
    """(True, '') when the installed `faker` has this provider; (False, why) when it does not;
    (None, note) when `faker` is not importable here -- said, never assumed either way."""
    if _FAKER['inst'] is None and _FAKER['error'] is None:
        try:
            import faker as _faker
            _FAKER['inst'] = _faker.Faker()
        except Exception as exc:                      # pragma: no cover - depends on the host
            _FAKER['error'] = '%s: %s' % (type(exc).__name__, exc)
    if _FAKER['inst'] is None:
        return None, (' (provider unverified here: faker is not importable -- %s; FakerLibrary '
                      'decides at run time)' % _FAKER['error'])
    snake = str(keyword).strip().lower().replace(' ', '_')
    if snake and callable(getattr(_FAKER['inst'], snake, None)):
        return True, ''
    return False, 'FakerLibrary has no provider %r' % keyword


def sentinel_spec(value) -> tuple:
    """(kind, args, why) for a typed value that is a SENTINEL, or (None, None, why).

    kinds: `auto` (the bare `asdf`: the generator comes from the field's meaning and type),
    `pick` (`@@pick`: a valid option), `provider` (`@@<provider name>`: args = [the FakerLibrary
    keyword], e.g. `@@company` -> ['Company'], `@@first name` -> ['First Name']).

    The grammar, in full -- there is nothing else:
        asdf                  (case-insensitive, surrounding whitespace ignored)
        @@pick
        @@<provider name>     (letters, spaces or underscores; NO arguments)
    A retired argument form (`@@date+30`, `@@unique Acme`, `@@int 1 100`, `@@text 40`) is a
    MALFORMED SENTINEL: said out loud in `why`, typed as the literal it is, and then caught by the
    sentinel-landed verdict if it reaches a record.
    """
    v = re.sub(r'\s+', ' ', str(value if value is not None else '')).strip()
    if not v:
        return None, None, 'no value to read'
    if v.casefold() == SENTINEL_BARE:
        return 'auto', [], ("the bare sentinel %r: the generator is chosen by the field's own "
                            "meaning and type" % v)
    if not v.startswith('@@'):
        return None, None, 'not a sentinel: %r is a literal value' % v[:60]
    body = v[2:].strip()
    if body.casefold() == 'pick':
        return 'pick', [], 'the explicit sentinel %r' % v
    retired_word = body.split()[0].casefold() in ('unique', 'int') if body else False
    if re.fullmatch(r'[A-Za-z][A-Za-z _]*', body) and not retired_word:
        kw = provider_keyword(body)
        ok, note = provider_known(kw)
        if ok is False:
            return None, None, ('MALFORMED SENTINEL %r: %s, so it is typed as the literal text it '
                                'is -- said out loud rather than silently generated (type asdf and '
                                'let the field decide, or @@<provider> with a real provider name, '
                                'e.g. @@company)' % (v, note))
        return 'provider', [kw], 'the explicit sentinel %r: %s.%s%s' % (v, FAKER_LIB, kw, note)
    return None, None, ('MALFORMED SENTINEL %r: it starts with @@ but is not a bare provider name; '
                        'the argument grammar (%s) was RETIRED 2026-09-20 (the user: FakerLibrary '
                        'does it), so it is typed as the literal text it is -- said out loud rather '
                        'than silently generated. Type asdf and let the field decide, or '
                        '@@<provider> with no arguments (@@company, @@first name, @@date)'
                        % (v, ', '.join(RETIRED_GRAMMAR)))


def sentinel_landed(value) -> bool:
    """True when a value READ BACK OFF THE PAGE is itself a sentinel -- the bare `asdf`, or ANY
    `@@...` (a person never means `@@x` as data, so a malformed one that was not generated and
    still reached the record is a landed sentinel too) -- the verdict `CAUGHT-BUG: sentinel
    landed`, never a quiet pass. Mirrored by `Gz Is Sentinel` in resources/garzai_data.robot,
    which is the copy that runs in the container."""
    v = re.sub(r'\s+', ' ', str(value if value is not None else '')).strip()
    return bool(v) and (v.casefold() == SENTINEL_BARE or bool(re.fullmatch(r'@@\S.*', v)))


# ------------------------------------------------------------------ meaning -> FakerLibrary provider
# ONE TABLE. The recorder's own Faker chips and `annotate.py`'s `${VAR}=    FakerLibrary.<kw>`
# preambles route through `tools/recorder/authoring/faker_classify.FAKER_METHODS` (keyword names
# verified against the installed robotframework-faker, not guessed); this table is pinned to it by
# `test_the_provider_table_agrees_with_the_one_faker_classify_already_ships` so the two cannot
# drift. The third column is the provider's typical WIDTH in characters: a field the org map says
# is narrower than that falls back to a bounded lorem value with the reason in `why`, because the
# browser would otherwise truncate the value silently (F146-10).
FAKER_PROVIDERS = {
    'first':   ('First Name', [], 20),
    'last':    ('Last Name', [], 20),
    'name':    ('Name', [], 40),
    'company': ('Company', [], 40),
    'email':   ('Email', [], 40),
    'phone':   ('Phone Number', [], 25),
    'street':  ('Street Address', [], 50),
    'city':    ('City', [], 30),
    'state':   ('State', [], 25),
    'country': ('Country', [], 45),
    'postal':  ('Postcode', [], 10),
    'url':     ('Url', [], 60),
    'job':     ('Job', [], 60),
    'date':    ('Date', [], 10),
}
# label shapes -> meaning, checked in this order (first hit wins). ANCHORED at the end of the
# label on purpose: `Email Bounced Reason` is a reason, not an email, and `Company D-U-N-S Number`
# is a number, not a company -- the word alone is not the meaning, the label's HEAD noun is.
LABEL_MEANING = [
    (re.compile(r'\bfirst\s*name\s*$', re.I), 'first'),
    (re.compile(r'\blast\s*name\s*$|\bsurname\s*$', re.I), 'last'),
    (re.compile(r'\be-?mail(\s*address)?\s*$', re.I), 'email'),
    (re.compile(r'\b(phone|mobile|fax|telephone)(\s*number)?\s*$', re.I), 'phone'),
    (re.compile(r'\b(zip|postal|post)\s*code\s*$|\bzip\s*$|\bpostcode\s*$', re.I), 'postal'),
    (re.compile(r'\bstreet(\s*address)?\s*$|\baddress\s*line\s*\d*\s*$', re.I), 'street'),
    (re.compile(r'\bcity\s*$', re.I), 'city'),
    (re.compile(r'\bstate(\s*/\s*province)?\s*$|\bprovince\s*$', re.I), 'state'),
    (re.compile(r'\bcountry\s*$', re.I), 'country'),
    (re.compile(r'\burl\s*$|\bwebsite\s*$', re.I), 'url'),
    (re.compile(r'\bjob\s*title\s*$|^\s*\*?\s*title\s*$', re.I), 'job'),
    (re.compile(r'\b(company|organization)(\s*name)?\s*$|\baccount\s*name\s*$', re.I), 'company'),
    (re.compile(r'\bdate\b|\bbirth', re.I), 'date'),
    (re.compile(r'\bname\s*$', re.I), 'name'),
]
# a label that names a NUMBER, KEY, ID or CODE is not the thing before it (`Company D-U-N-S
# Number` is not a company; `Data.com Key` is not data)
_NOT_A_MEANING_RX = re.compile(r'\bnumber\b|\bno\.?\s*$|\bid\b|\bkey\b|\bcode\b|d-u-n-s', re.I)

# Salesforce LocaleSidKey -> the strftime pattern a date INPUT renders and accepts in that locale.
# en_US is MEASURED (fsc7f, the User record's LocaleSidKey, 2026-09-20; `10/8/2026` read back
# equal to `10/08/2026` by `confirm.lenient_equal`). The rest are the Salesforce locale table's
# short date formats and are UNMEASURED here -- a locale not in this table is COULD-NOT-CHECK,
# never a default: a date typed in the wrong order is the quietest wrong answer there is.
LOCALE_DATE_PATTERN = {
    'en_US': '%m/%d/%Y',
    'en_GB': '%d/%m/%Y', 'en_AU': '%d/%m/%Y', 'en_IE': '%d/%m/%Y', 'en_NZ': '%d/%m/%Y',
    'en_IN': '%d/%m/%Y', 'en_CA': '%Y-%m-%d', 'en_ZA': '%Y/%m/%d',
    'fr_FR': '%d/%m/%Y', 'fr_CA': '%Y-%m-%d', 'es_ES': '%d/%m/%Y', 'es_MX': '%d/%m/%Y',
    'it_IT': '%d/%m/%Y', 'pt_BR': '%d/%m/%Y', 'pt_PT': '%d/%m/%Y',
    'de_DE': '%d.%m.%Y', 'de_AT': '%d.%m.%Y', 'de_CH': '%d.%m.%Y',
    'nl_NL': '%d-%m-%Y', 'da_DK': '%d-%m-%Y', 'sv_SE': '%Y-%m-%d', 'nb_NO': '%d.%m.%Y',
    'fi_FI': '%d.%m.%Y', 'pl_PL': '%d.%m.%Y', 'ru_RU': '%d.%m.%Y',
    'ja_JP': '%Y/%m/%d', 'zh_CN': '%Y/%m/%d', 'zh_TW': '%Y/%m/%d', 'ko_KR': '%Y.%m.%d',
}
ISO_PATTERN = '%Y-%m-%d'


def date_pattern(locale, iso=False) -> tuple:
    """(the strftime pattern, why) for a date the composed line will TYPE, or (None, why).

    `iso` is the receiving keyword's own documented input (`Omni Date` takes `YYYY-MM-DD`) and
    outranks the locale. Otherwise `locale` is `{'LocaleSidKey': ..., 'source': ...}` as
    `build_override.py --locale` embeds it (the org user's User record, never the org map -- the
    map carries field types, not the running user's locale). No locale is COULD-NOT-CHECK."""
    if iso:
        return ISO_PATTERN, "the receiving keyword's own input is YYYY-MM-DD"
    if isinstance(locale, str):
        locale = {'LocaleSidKey': locale, 'source': 'given as a string'}
    key = str((locale or {}).get('LocaleSidKey') or '').strip()
    if not key:
        return None, ('COULD-NOT-CHECK: the org user\'s locale is unknown, so the date format a '
                      'date input accepts is unknown -- build with --locale <LocaleSidKey> '
                      '(SELECT LocaleSidKey FROM User WHERE Id = <the running user>) and the date '
                      'is typed in that locale')
    fmt = LOCALE_DATE_PATTERN.get(key)
    if not fmt:
        return None, ('COULD-NOT-CHECK: locale %r is not in LOCALE_DATE_PATTERN, so its date '
                      'format is not known here -- add it with a measured read-back, never a guess'
                      % key)
    return fmt, 'typed in locale %s (%s: %s)' % (key, (locale or {}).get('source') or 'source not stated', fmt)


# The ORG MAP's field type is what routes the keyword (CLAUDE.md: "Metadata routes the keyword, DOM
# is the backstop"). Read off `<alias>.json` -> objects.<Obj>.inventory.fields.value.<f>.type, the
# same projection `skeleton.py <alias>:<Object>` prints. A type with no row here has NO generator
# and says so: a lookup, a checkbox and a base64 blob are not things a generator can invent a
# correct value for, and inventing one is the quiet-wrong-answer failure.
SF_TYPE_GENERATOR = {
    'email': 'email', 'phone': 'phone', 'url': 'url',
    'date': 'date', 'datetime': 'date',
    'picklist': 'pick', 'multipicklist': 'pick', 'combobox': 'pick',
    'int': 'number', 'double': 'number', 'percent': 'number', 'currency': 'number',
    'string': 'text', 'textarea': 'text', 'encryptedstring': 'text',
}
NUMBER_BOUNDS = {'int': (1, 100), 'double': (1, 1000), 'percent': (1, 100),
                 'currency': (1000, 99000), 'number': (1, 100)}
SF_TYPE_NO_GENERATOR = {
    'reference': 'a lookup: its value must name a record that EXISTS, which no generator knows',
    'boolean': 'a checkbox is clicked, never typed into',
    'address': 'a compound control (one DB value, several inputs) -- dedicated keywords, BACKLOG 80',
    'base64': 'a file blob, not a typed value',
    'id': 'a record id is not generated data',
    'time': 'NOT YET IMPLEMENTED: no time provider is routed',
    'anytype': 'the type is literally `anytype`: there is nothing to route on',
}

# The BACKSTOP, for a label the org map does not carry: the control's own input type, then its
# parser family. Always named in the `why`, so a reader can tell which door answered.
DOM_TYPE_GENERATOR = {
    'email': 'email', 'tel': 'phone', 'url': 'url', 'number': 'number',
    'date': 'date', 'datetime-local': 'date', 'text': 'text', 'search': 'text',
}
# F146-2: the describer's `familyOf()` returns exactly button / checkbox / dropdown / input_field /
# radio or a raw tag name -- never 'date', 'email', 'picklist' -- so this table carries only the
# one row the live path can reach (`test_family_generator_and_family_no_generator_are_fully_reachable_live`).
FAMILY_GENERATOR = {
    'input_field': 'text',
}
FAMILY_NO_GENERATOR = {
    'checkbox': 'a checkbox is clicked, never typed into',
    'radio': 'a radio is clicked, never typed into',
}


def field_meta(label, fields, name=None) -> tuple:
    """(the org-map field entry, why) for a rendered LABEL, or (None, why).

    `fields` is the table `build_override.py --fields <alias>:<Object>` embeds: one entry per
    field, keyed by its rendered label AND by its API name, each carrying `type`, `object`,
    `name`, `length` and `picklist_values`. A label the table does not carry is a plain
    could-not-check -- the descriptor door answers instead, and the `why` says so.

    `name` is the input's own `name=` HTML attribute (the descriptor's `name` field), tried ONLY
    after the label misses (F194's walk on fsc7f, error entry `47a40e6e97`): the frozen map labels
    `NumberOfEmployees` as `Employees` while the live form renders `No. of Employees`, so the label
    door misses even though `FIELDS` is keyed by API name too and the input itself carries
    `name="NumberOfEmployees"`. Rendered labels drift from the map far more than API names do, so
    the label is still tried FIRST and this is a fallback, not a replacement."""
    if not fields:
        return None, 'no org-map field table was embedded in this build'
    lab = omni_label(label)
    if lab:
        for key in (lab, lab.casefold()):
            hit = fields.get(key)
            if hit:
                return hit, 'org-map field %s.%s (type %r)' % (hit.get('object'), hit.get('name'),
                                                               hit.get('type'))
    if name:
        hit = fields.get(str(name))
        if hit:
            return hit, ('org-map field %s.%s (type %r), found by the input name= (the label %r '
                         'is not the map\'s label for it)'
                         % (hit.get('object'), hit.get('name'), hit.get('type'), lab))
    if not lab:
        return None, 'the control has no label and no name= to look up'
    return None, 'no org-map field is labelled %r (or named %r) in the embedded table' % (lab, name)


def _pick_cells(label, options) -> tuple:
    """(the `Gz Pick` cells, why) from a list of option values, or (None, why)."""
    vals = [re.sub(r'\s+', ' ', str(o)).strip() for o in (options or [])]
    vals = [v for v in vals if v and not omni_placeholder_option(v)]
    vals = list(dict.fromkeys(vals))
    if not vals:
        return None, ('COULD-NOT-CHECK: no usable option is known for this control (every option '
                      'was the listbox\'s own "nothing chosen" entry, or none reached here) -- an '
                      'option is never invented')
    kept, note = vals[:PICK_OPTION_CAP], ''
    if len(vals) > PICK_OPTION_CAP:
        note = (' -- %d of %d options are on the line (cap PICK_OPTION_CAP=%d); the full list is '
                'in the org map / the page\'s own listbox'
                % (len(kept), len(vals), PICK_OPTION_CAP))
    return ['Gz Pick', omni_label(label) or 'value'] + kept, 'a valid value from the options%s' % note


def _datetime_note(meta) -> str:
    """The disclosure a `datetime` field's metadata carries wherever a date is generated for it
    (F146-6): the DATE half only, on every door that composes one."""
    if meta and str(meta.get('type') or '').casefold() == 'datetime':
        return (' -- the DATE half only: the time half is not generated here (a datetime is a '
                'compound control; routing it is BACKLOG 80)')
    return ''


def _length_of(meta):
    try:
        n = int((meta or {}).get('length') or 0)
    except (TypeError, ValueError):
        n = 0
    return n if n > 0 else None


def label_meaning(label) -> tuple:
    """(meaning, why) from the rendered label alone, or (None, why)."""
    lab = omni_label(label)
    if not lab:
        return None, 'no label'
    excluded = bool(_NOT_A_MEANING_RX.search(lab))
    for rx, cls in LABEL_MEANING:
        if rx.search(lab):
            if excluded and cls in ('company', 'name', 'job', 'date'):
                return None, ('label %r names a number/key/id/code, not a %s' % (lab, cls))
            return cls, 'label %r reads as %s' % (lab, cls)
    return None, 'label %r has no provider meaning' % lab


def _lorem_cells(length) -> tuple:
    """A bounded lorem value for a text field nothing routes: `Word` when the field is 15-23 wide
    or its width is unknown, `Text max_nb_chars=<n>` (capped at 200) from 24 up, and an exact
    `Lexify` below 15 -- so the browser never truncates a generated value silently (F146-10)."""
    if length is None:
        return ['%s.Word' % FAKER_LIB], 'one Word (no length known)'
    if length >= 24:
        n = min(length, 200)
        return ['%s.Text' % FAKER_LIB, 'max_nb_chars=%d' % n], 'Text bounded to %d of %d' % (n, length)
    if length >= 15:
        return ['%s.Word' % FAKER_LIB], 'one Word (fits %d)' % length
    n = min(length, 8)
    return ['%s.Lexify' % FAKER_LIB, 'text=%s' % ('?' * n)], 'Lexify of %d letters (length %d)' % (n, length)


def faker_cells(cls, label=None, meta=None, iso=False, locale=None, meaning=None) -> tuple:
    """(the FakerLibrary cells, why) for one generator CLASS -- a provider meaning ('first',
    'company', ...), 'number', 'date', 'text', 'pick' -- or (None, why)."""
    t = str((meta or {}).get('type') or '').casefold()
    length = _length_of(meta)
    if cls == 'pick':
        cells, why = _pick_cells(label, (meta or {}).get('picklist_values'))
        return cells, why
    if cls == 'number':
        lo, hi = NUMBER_BOUNDS.get(t, NUMBER_BOUNDS['number'])
        # bounded by the field when the map knows its digits and the default would not fit
        if length and length < len(str(hi)):
            hi = 10 ** length - 1
        return (['%s.Random Int' % FAKER_LIB, 'min=%d' % lo, 'max=%d' % hi],
                'a whole number in [%d, %d]' % (lo, hi))
    if cls == 'date':
        fmt, why = date_pattern(locale, iso=iso)
        if not fmt:
            return None, why
        return ['%s.Date' % FAKER_LIB, 'pattern=%s' % fmt], 'a date %s%s' % (why, _datetime_note(meta))
    if cls == 'text':
        m, m_why = (meaning, 'meaning given') if meaning else label_meaning(label)
        if m and m in FAKER_PROVIDERS:
            kw, extra, width = FAKER_PROVIDERS[m]
            if m == 'date':
                return faker_cells('date', label, meta, iso, locale)
            if length and length < width:
                cells, lw = _lorem_cells(length)
                return cells, ('%s, but the org map says length %d and %s.%s is up to ~%d wide: %s'
                               % (m_why, length, FAKER_LIB, kw, width, lw))
            return ['%s.%s' % (FAKER_LIB, kw)] + list(extra), m_why
        cells, lw = _lorem_cells(length)
        return cells, '%s: %s' % (m_why, lw)
    if cls in FAKER_PROVIDERS:
        kw, extra, width = FAKER_PROVIDERS[cls]
        if cls == 'date':
            return faker_cells('date', label, meta, iso, locale)
        if length and length < width:
            cells, lw = _lorem_cells(length)
            return cells, ('%s.%s is up to ~%d wide and the org map says length %d: %s'
                           % (FAKER_LIB, kw, width, length, lw))
        return ['%s.%s' % (FAKER_LIB, kw)] + list(extra), '%s.%s' % (FAKER_LIB, kw)
    return None, 'no generator class %r' % cls


def provider_cells(keyword, label=None, meta=None, iso=False, locale=None) -> tuple:
    """(cells, why) for an EXPLICIT `@@<provider>` override. `Date` is typed in the locale (ISO
    for an ISO keyword); `Random Int` and `Text` take the same bounds the auto route would."""
    kw = provider_keyword(keyword)
    if kw == 'Date':
        return faker_cells('date', label, meta, iso, locale)
    if kw == 'Random Int':
        return faker_cells('number', label, meta, iso, locale)
    if kw == 'Text':
        n = min(_length_of(meta) or 200, 200)
        return ['%s.Text' % FAKER_LIB, 'max_nb_chars=%d' % n], 'Text bounded to %d' % n
    return ['%s.%s' % (FAKER_LIB, kw)], '%s.%s' % (FAKER_LIB, kw)


def generator_door(kind, receiving, lab, desc=None, options=None, meta=None, locale=None) -> tuple:
    """(cells, why) when the RECEIVING KEYWORD or a descriptor HOST fact names the generator before
    metadata or the DOM type get a vote, or (None, None) to let the caller fall through to
    `generator_call`'s meaning / metadata / DOM-type / family ladder (F146-1, the root defect).

    `Omni Date` / `Omni Select` are OmniStudio's own compound keywords, and a date-picker or
    combobox HOST -- named by the element's own xpath, `_OMNI_DATE_PICKER` / `_OMNI_COMBOBOX` --
    answers even before the line has been routed to one of those keywords (the omniKey/host walk
    already knows the widget). Both outrank a bare `type="text"`, which Lightning and OmniStudio
    render for a date picker, a combobox and a lookup alike.

    `(None, None)` means neither the keyword nor the host has an opinion. `(None, why)` means the
    door DOES apply but has nothing usable (e.g. `Omni Select` with no known options) -- that IS
    the answer, a disclosed COULD-NOT-CHECK, never a fallthrough to a worse guess."""
    if kind != 'auto':
        return None, None
    d = desc or {}
    blob = ' '.join(str(d.get(k) or '') for k in ('xpath', 'alt_xpath'))
    if receiving == 'Omni Date' or _OMNI_DATE_PICKER in blob:
        src = ("the receiving keyword 'Omni Date'" if receiving == 'Omni Date'
               else "the descriptor's own element path is inside a %r host" % _OMNI_DATE_PICKER)
        cells, why = faker_cells('date', lab, meta, iso=True, locale=locale)
        return cells, '%s: names a date -- %s' % (src, why)
    if receiving == 'Omni Select' or _OMNI_COMBOBOX in blob:
        src = ("the receiving keyword 'Omni Select'" if receiving == 'Omni Select'
               else "the descriptor's own element path is inside a %r host" % _OMNI_COMBOBOX)
        cells, why = _pick_cells(lab, options or d.get('options'))
        return cells, '%s: names a pick -- %s' % (src, why)
    return None, None


def generator_call(kind, args, label, meta=None, desc=None, options=None, iso=False,
                   receiving='', locale=None) -> tuple:
    """(the generator call as Robot CELLS, why) for one sentinel, or (None, why).

    `iso=True` asks for `YYYY-MM-DD`, which is what `Omni Date` takes. `receiving` is the keyword
    that will actually run with this value (`Omni Date`, `Omni Select`, a plain `TypeText`, ...)
    -- see `generator_door`, which this consults FIRST. `locale` is the org user's locale as the
    build embeds it (`build_override.py --locale`), the only thing that can say how a date is
    typed."""
    lab = omni_label(label)
    args = list(args or [])
    _override_note = ''
    if kind not in ('auto', None) and meta and meta.get('type'):
        _t = str(meta.get('type')).casefold()
        if _t in SF_TYPE_NO_GENERATOR:
            _override_note = ('; the metadata type %r has no generator -- %s -- overridden by the '
                              'explicit sentinel' % (_t, SF_TYPE_NO_GENERATOR[_t]))
        else:
            _override_note = ('; the metadata type %r was not consulted: the explicit sentinel '
                              'names the provider' % _t)

    if kind == 'provider':
        cells, why = provider_cells(args[0] if args else '', lab, meta, iso=iso, locale=locale)
        return cells, ('the sentinel names the provider: %s' % why) + _override_note
    if kind == 'pick':
        opts = options or (meta or {}).get('picklist_values')
        cells, why = _pick_cells(lab, opts)
        # F146-5: "no usable option is known" reads the same whether the listbox was simply
        # closed or the field is not a picklist AT ALL -- the org map knows which; join the facts.
        if not cells and meta and meta.get('type'):
            t = str(meta.get('type')).casefold()
            if t not in ('picklist', 'multipicklist', 'combobox'):
                why += ' -- %s.%s is type %r, not a picklist: no option was ever going to exist' \
                    % (meta.get('object'), meta.get('name'), t)
        return cells, why + _override_note
    if kind != 'auto':
        return None, 'unknown sentinel kind %r' % kind

    # THE RECEIVING KEYWORD / HOST DOOR ANSWERS FIRST (F146-1), before metadata or the DOM type get
    # a vote: it is the one door a generic `type="text"` cannot fool.
    door_cells, door_why = generator_door(kind, receiving, lab, desc=desc, options=options,
                                          meta=meta, locale=locale)
    if door_why is not None:
        return door_cells, door_why

    # `asdf`: the METADATA type routes it -- a picklist, a number and a date by type; a text-ish
    # type by the label's MEANING, then a bounded lorem value -- and the descriptor is the backstop.
    if meta and meta.get('type'):
        t = str(meta.get('type')).casefold()
        where = 'metadata type %r on %s.%s' % (t, meta.get('object'), meta.get('name'))
        if t in ('picklist', 'multipicklist', 'combobox'):
            cells, why = _pick_cells(lab, options or meta.get('picklist_values'))
            return cells, '%s: %s' % (where, why)
        cls = SF_TYPE_GENERATOR.get(t)
        if cls is None:
            return None, ('COULD-NOT-CHECK: %s has no generator -- %s'
                          % (where, SF_TYPE_NO_GENERATOR.get(t, 'no rule in SF_TYPE_GENERATOR names it')))
        cells, why = faker_cells(cls, lab, meta, iso=iso, locale=locale)
        return cells, '%s: %s' % (where, why)

    d = desc or {}
    fam = str(d.get('family') or '').casefold()
    if fam in FAMILY_NO_GENERATOR:
        return None, ('COULD-NOT-CHECK: no org-map field for %r, and the control\'s family %r has '
                      'no generator -- %s' % (lab, fam, FAMILY_NO_GENERATOR[fam]))
    etype = str(d.get('type') or d.get('etype') or '').casefold()
    if etype in DOM_TYPE_GENERATOR:
        cells, why = faker_cells(DOM_TYPE_GENERATOR[etype], lab, None, iso=iso, locale=locale)
        return cells, ('no org-map field for %r: the descriptor\'s input type %r -- %s'
                       % (lab, etype, why))
    if fam in ('picklist', 'combobox'):
        cells, why = _pick_cells(lab, options)
        return cells, ('no org-map field for %r: the descriptor\'s family %r -- %s'
                       % (lab, fam, why))
    if fam in FAMILY_GENERATOR:
        cells, why = faker_cells(FAMILY_GENERATOR[fam], lab, None, iso=iso, locale=locale)
        return cells, ('no org-map field for %r: the descriptor\'s family %r -- %s'
                       % (lab, fam, why))
    return None, ('COULD-NOT-CHECK: no org-map field for %r and neither the input type %r nor the '
                  'family %r names a generator' % (lab, etype, fam))

# ----------------------------------------------------------------------------- the variable line
def variable_name(label, taken=None, prefix=None) -> str:
    """The Robot variable name for a field's generated value, derived from its LABEL and unique
    within the pane. `*Last Name` -> `last_name`; with the object as prefix, `lead_last_name`.
    `taken` is the set of names already emitted in this pane, and it is UPDATED in place."""
    base = re.sub(r'[^a-z0-9]+', '_', omni_label(label).casefold()).strip('_') or 'value'
    if base[0].isdigit():
        base = 'f_' + base
    p = re.sub(r'[^a-z0-9]+', '_', str(prefix or '').casefold()).strip('_')
    if p and not base.startswith(p + '_'):
        base = '%s_%s' % (p, base)
    taken = taken if taken is not None else set()
    name, n = base, 1
    while name in taken:
        n += 1
        name = '%s_%d' % (base, n)
    taken.add(name)
    return name


# the keywords whose THIRD cell is the value a sentinel can occupy
VALUE_CELL_KEYWORDS = ('TypeText', 'TypeSecret', 'Omni Type', 'Omni Select', 'Omni Date',
                       'DropDown', 'PickList', 'ComboBox')
_VALUE_CELL = 2


def value_cell(line) -> str | None:
    """The VALUE a composed line types or picks, or None when the line has no value cell."""
    cells = _cells(line or '')
    if len(cells) <= _VALUE_CELL or cells[0] not in VALUE_CELL_KEYWORDS:
        return None
    return cells[_VALUE_CELL]


def replace_value_cell(line, new_value) -> str:
    """The same composed line with its VALUE cell replaced -- indentation and every trailing cell
    (anchor=, partial_match=, a family argument, the unverified marker) kept exactly."""
    cells = _cells(line or '')
    if len(cells) <= _VALUE_CELL:
        return line
    indent = line[: len(line) - len(line.lstrip())]
    cells = list(cells)
    cells[_VALUE_CELL] = new_value
    return indent + '    '.join(cells)


def variable_line(var, cells, indent='    ') -> str:
    """`    ${lead_last_name}=    FakerLibrary.Last Name`"""
    return '%s${%s}=    %s' % (indent, var, '    '.join(str(c) for c in cells))


def dormant_generate_lines(var, cells, action_line, indent='    ') -> list:
    """The two DORMANT lines that sit under a plain (gesture-free) pick or date, so a recording
    made with no Alt-click can still be switched to generated data by deleting two cells in the
    editor -- exactly like a backup line.

    The form is `#   generate:    <the line>`, which `_dormant_form` renders as
    `Comment    generate:    <the line>`: `generate:` is its own CELL, so deleting `Comment` and
    `generate:` leaves the live step and nothing else."""
    if not var or not cells or not (action_line or '').strip():
        return []
    body = replace_value_cell(action_line, '${%s}' % var).strip()
    # the unverified marker is the LIVE line's own trailing comment; inside a dormant
    # `Comment    generate:` step a second `#` reads as noise, so it is dropped here and the live
    # line above keeps it
    body = body.split(UNVERIFIED)[0].rstrip()
    return ['%s#   generate:    ${%s}=    %s' % (indent, var, '    '.join(str(c) for c in cells)),
            '%s#   generate:    %s' % (indent, body)]


def dormant_generate_pair(var_line, action_line, indent='    ') -> list:
    """`dormant_generate_lines` for a pair that has ALREADY been composed -- the form
    `generated_pick_lines` / `generated_date_lines` return. This is what sits under a plain,
    gesture-free pick or date: the recording is literal and runs as recorded, and switching it to
    generated data is two cell deletions per line, with nothing to retype."""
    if not (var_line or '').strip() or not (action_line or '').strip():
        return []
    body = action_line.split(UNVERIFIED)[0].rstrip().strip()
    return ['%s#   generate:    %s' % (indent, var_line.strip()),
            '%s#   generate:    %s' % (indent, body)]


def generated_data_lines(composed, label=None, fields=None, desc=None, options=None,
                         taken=None, indent='    ', prefix=None, locale=None) -> tuple:
    """(the variable line, the rewritten fill line, why) for a composed line whose VALUE is a
    SENTINEL, or ('', composed, why) when it is not one or no generator fits.

    This runs LAST, after the OmniStudio routing, so an `asdf` typed into an OmniStudio masked
    input becomes `Omni Type    <key>    ${phone_number}` and not a TypeText the widget ignores.
    `locale` is the org user's locale the build embeds (`build_override.py --locale`); a date
    with none is a disclosed COULD-NOT-CHECK, never a default format."""
    if not isinstance(composed, str) or not composed.strip():
        return '', composed, 'nothing composed'
    value = value_cell(composed)
    if value is None:
        return '', composed, 'the composed line has no value cell'
    kind, args, why = sentinel_spec(value)
    if kind is None:
        return '', composed, why
    cells0 = _cells(composed)
    lab = omni_label(label or (cells0[1] if len(cells0) > 1 else ''))
    dname = desc.get('name') if isinstance(desc, dict) else None
    meta, meta_why = field_meta(lab, fields, name=dname)
    # THE DATE FORMAT IS DECIDED BY THE KEYWORD THAT WILL RECEIVE IT, then by the org user's
    # LOCALE. `Omni Date` documents `YYYY-MM-DD`, so it gets ISO. A plain `TypeText` into a
    # rendered date input gets the locale's own pattern (D19: a date is TYPED in the org user's
    # locale) -- read from the build's `--locale`, never from the org map, which carries field
    # types and not the running user's locale; no locale is COULD-NOT-CHECK, never a US default.
    receiving = cells0[0] if cells0 else ''
    iso = receiving == 'Omni Date'
    cells, gen_why = generator_call(kind, args, lab, meta=meta, desc=desc, options=options,
                                    iso=iso, receiving=receiving, locale=locale)
    if not cells:
        full_why = '%s, but %s (%s)' % (why, gen_why, meta_why)
        marked = composed
        # F146-5 (F146-5): a `@@pick`/`asdf` this door could not resolve to a real option used to
        # ship UNMARKED -- the disclosure lived only in `why`, a surface the PANE never shows, while
        # the six characters `@@pick` (or `asdf`) reached the recorded line exactly as if nobody had
        # noticed. That is precisely what `Gz Sentinel Verdict` calls a landed sentinel when it
        # reads the value back. The line itself now carries the mark.
        if 'no usable option is known' in (gen_why or ''):
            marked = (composed.split(UNVERIFIED)[0].rstrip()
                     + '    # COULD-NOT-CHECK: no option known; a literal sentinel would land')
        return '', marked, full_why
    var = variable_name(lab, taken, prefix=prefix or (meta or {}).get('object'))
    return (variable_line(var, cells, indent),
            replace_value_cell(composed, '${%s}' % var),
            '%s; %s; %s' % (why, gen_why, meta_why))


def retarget_verify_backup(backup, new_value) -> str:
    """A dormant `#   verify: Verify Input Value    <label>    <value>` line whose VALUE is now a
    variable. Without this the read-back line still quotes the SENTINEL, which would assert that
    `asdf` landed -- the exact thing the sentinel-landed verdict exists to catch."""
    if not isinstance(backup, str) or '#   verify:' not in backup:
        return backup
    # SPLIT KEEPING THE SEPARATORS, and replace only the last cell. Going through `_cells` and
    # rejoining with four spaces rewrites the line's own punctuation: the dormant marker is
    # `#   verify:` with THREE spaces, which `_cells` reads as a separator, and the rejoin came
    # back `#    verify:` -- a mark no reader and no `_dormant_form` branch recognises.
    parts = re.split(r'( {2,}|\t)', backup)
    if len(parts) < 3:
        return backup
    parts[-1] = new_value
    return ''.join(parts)


# --------------------------------------------- the Alt-click markers on a click-recorded control
def generated_pick_lines(label, option, options, taken=None, indent='    ', prefix=None) -> tuple:
    """(the variable line, the `Omni Select` line, the dormant literal backup, why) for an
    ALT-CLICKED combobox option, or ('', '', '', why).

    The descriptor carries the OPEN listbox's own options at event time, so this needs no metadata
    at all: the options a person could have picked are the options the page was offering."""
    lab = omni_label(label)
    if not lab:
        return '', '', '', 'no label on the combobox: a keyword whose first argument is blank is a guess'
    cells, why = _pick_cells(lab, options)
    if not cells:
        return '', '', '', why
    var = variable_name(lab, taken, prefix=prefix)
    literal = RT._rf('Omni Select', lab, (option or '').strip()).strip()
    return (variable_line(var, cells, indent),
            '%s%s    %s' % (indent, RT._rf('Omni Select', lab, '${%s}' % var).strip(), UNVERIFIED),
            '%s#   backup: %s   (the literal pick that was recorded, unverified)' % (indent, literal),
            'Alt-click on the option: any valid value here -- %s' % why)


def generated_date_lines(label, omni_key, iso, taken=None, indent='    ', prefix=None) -> tuple:
    """(the variable line, the `Omni Date` line, the dormant literal backup, why) for an
    ALT-CLICKED calendar day, or ('', '', '', why).

    Build n10: the value is `FakerLibrary.Date    pattern=%Y-%m-%d` -- `Omni Date`'s own documented
    input -- and the literal day that was clicked survives as the dormant backup. The offset
    grammar (`+N` days from today) left with `@@date+N` (the user, 2026-09-20)."""
    key = str(omni_key or '').strip()
    if not key:
        return '', '', '', 'the element carries no data-omni-key: Omni Date has nothing to resolve'
    if not _ISO_RX.match(str(iso or '')):
        return '', '', '', 'not an ISO date: %r' % iso
    lab = omni_label(label) or key
    var = variable_name(lab, taken, prefix=prefix)
    literal = RT._rf('Omni Date', key, iso).strip()
    cells, why = faker_cells('date', lab, None, iso=True)
    return (variable_line(var, cells, indent),
            '%s%s    %s' % (indent, RT._rf('Omni Date', key, '${%s}' % var).strip(), UNVERIFIED),
            '%s#   backup: %s   (the literal date that was recorded, unverified)' % (indent, literal),
            'Alt-click on the day: any valid date here -- %s' % why)
def xpath_form(row: dict, body: str) -> str | None:
    """The same step in xpath form, from the ladder's xpath (review_table's own convention: a
    click of any flavour becomes ClickElement; TypeText and DropDown keep their keyword)."""
    xp = _xp_of(row)
    cells = _cells(body or '')
    if not xp or not cells:
        return None
    if 'xpath\\=' in body:
        return body.strip()
    kw = cells[0]
    arg = RT._xp_arg(xp)
    if kw in ('TypeText', 'TypeSecret', 'DropDown') and len(cells) >= 3:
        return RT._rf(kw, arg, cells[2])
    if kw in ('ClickText', 'ClickItem', 'ClickElement', 'ClickCheckbox'):
        return RT._rf('ClickElement', arg)
    return None


def _compose_body(row: dict, rendered: str) -> tuple:
    """(body, xp_body, disambiguation, entry_used) for ONE matched row -- the pure half shared by
    the offline and the driver layers. `body` is None (let the recorder's line stand), '' (record
    nothing) or the proposed keyword-form step; `xp_body` its xpath form; `disambiguation` the
    parser's DESCRIPTION of the control's repeats, with no call argument derived from it.
    `entry_used` (CH-B B1.d) is the library entry `body` actually came through, or None when it is
    a plain parser proposal -- the caller's cue to stamp `# recipe: <name>` instead of
    `# unverified: parser proposal`."""
    entry = None
    try:
        entry = RT._pattern_entry(row)     # a library entry whose recipe is one to RUN
    except Exception:
        entry = None
    used: list = []
    body = _body(row, rendered, entry, used)
    n_stripped = None
    if body:
        body, n_stripped = strip_numeric_anchor(body)
    xp_body = xpath_form(row, body) if body else None
    dis = {'index': _described_index(row) or n_stripped, 'group_size': row.get('group_size'),
           'anchor_candidates': list(row.get('anchor_candidates') or []),
           'decision': 'described-only', 'anchor': None, 'live_count': None, 'scope': None,
           'why': 'the parser index is a capture count; no anchor is derived from it (F189)'}
    return body, xp_body, dis, (used[0] if used else None)


def _render_row(row: dict, rendered: str, form: str, body, xp_body, dis: dict,
                dormant_label: str | None = None, entry_used: dict | None = None) -> dict:
    if body is None:
        return {'line': None, 'xpath_line': xp_body, 'why': 'no proposal for this action on this control',
                'disambiguation': dis}
    if body == '':
        return {'line': '', 'xpath_line': None, 'why': 'recorder noise on an input (focus click / tab-out); nothing recorded',
                'disambiguation': dis}
    ind = _indent(rendered)
    chosen = body
    if form == 'xpath' and xp_body:
        chosen = xp_body
    elif form == 'both' and xp_body and xp_body != body:
        chosen = body + '    # xpath form: ' + xp_body
    note = _recipe_note(entry_used)
    why = ('recipe %s for row %s' % (entry_used.get('id'), row.get('n')) if entry_used
           else 'parser proposal for row %s' % row.get('n'))
    decision = dis.get('decision')
    if decision in ('text-anchor', 'xpath-live') or 'COULD-NOT' in (dis.get('why') or ''):
        why += '; live disambiguation: %s' % dis.get('why')
    return {'line': _stamp(ind + chosen.strip(), note),
            'xpath_line': _stamp(ind + xp_body.strip(), note) if xp_body else None,
            'dormant_label_line': ('%s%s' % (ind, dormant_label.strip())) if dormant_label else None,
            'why': why, 'disambiguation': dis}


def compose_for_row(row: dict, rendered: str, form: str = 'keyword') -> dict:
    """The line for ONE matched row, offline: no driver, so no live census -- the label form is
    bare and `disambiguation` says what the capture counted."""
    body, xp_body, dis, entry_used = _compose_body(row, rendered)
    return _render_row(row, rendered, form, body, xp_body, dis, entry_used=entry_used)


# ----------------------------------------------------------------------------- live disambiguation (F189)
# The census the DRIVER layer takes before a label-form line is recorded. One execute_script, run
# against the page the person is on, scoped to the open modal when the element they touched sits
# in one (what QForce's `UseModal On` scopes to), else the whole page. It answers:
#   count         visible, enabled controls (fill kind) or deepest text matches (text kind) whose
#                 label/text equals the composed label, in that scope
#   target_index  which of them is (or contains, or is inside) the element the person touched
#   anchors       for each ladder candidate: how many times its text occurs live in the scope,
#                 and whether the target is the NEAREST label match to it (centre Manhattan
#                 distance -- a PROXY for QWeb's overlap-then-distance scorer, disclosed as such)
# Everything walks the real DOM through document.evaluate (xpath pierces Lightning's synthetic
# shadow; querySelectorAll and textContent do not -- CLAUDE.md) and climbs shadow hosts by hand,
# because `parentElement`/`closest` stop at the synthetic boundary (measured 2026-09-19, the walk
# shim). A native CLOSED shadow root is unreachable and reads as count 0 -> COULD-NOT-CHECK.
_CENSUS_JS = r"""
/* __gzCensus (F189) */
var tgt = arguments[0], label = arguments[1], kind = arguments[2], cands = arguments[3] || [];
function norm(s){ return String(s == null ? '' : s).replace(/\s+/g, ' ').replace(/^\*\s*/, '').replace(/\s*\*$/, '').trim(); }
function up(el){
  var p = el.parentNode;
  if (p && p.nodeType === 1) return p;
  if (p && p.host) return p.host;
  var r = el.getRootNode && el.getRootNode();
  return (r && r.host) ? r.host : null;
}
function xp(expr, ctx){
  var out = [];
  try { var r = document.evaluate(expr, ctx, null, 7, null); for (var i = 0; i < r.snapshotLength; i++) out.push(r.snapshotItem(i)); } catch (e) {}
  return out;
}
function sval(el){ try { return document.evaluate('normalize-space(.)', el, null, 2, null).stringValue; } catch (e) { return String(el.textContent || ''); } }
function lit(s){
  if (s.indexOf('"') < 0) return '"' + s + '"';
  if (s.indexOf("'") < 0) return "'" + s + "'";
  return 'concat("' + s.split('"').join('", \'"\', "') + '")';
}
function visible(el){
  try {
    if (el.hidden) return false;
    var r = el.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0)) return false;
    var cs = window.getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') return false;
    return true;
  } catch (e) { return true; }
}
function enabled(el){ return !el.disabled && el.getAttribute('aria-disabled') !== 'true'; }
function scopeOf(el){
  var cur = el, g = 0;
  while (cur && cur.nodeType === 1 && g++ < 300) {
    var role = cur.getAttribute('role'), cls = cur.getAttribute('class') || '';
    if (role === 'dialog' || role === 'alertdialog' || /(^|\s)slds-modal(\s|$)/.test(cls) || /(^|\s)uiModal(\s|$)/.test(cls)) return {node: cur, kind: 'modal'};
    cur = up(cur);
  }
  return {node: document, kind: 'page'};
}
function byId(id){ var e = xp('//*[@id=' + lit(id) + ']', document); return e.length ? e[0] : null; }
function labelsOf(el){
  var out = [];
  var id = el.getAttribute('id');
  if (id) xp('//label[@for=' + lit(id) + ']', document).forEach(function (l) { out.push(sval(l)); });
  var al = el.getAttribute('aria-label'); if (al) out.push(al);
  var lb = el.getAttribute('aria-labelledby');
  if (lb) lb.split(/\s+/).forEach(function (i) { var e = byId(i); if (e) out.push(sval(e)); });
  var ph = el.getAttribute('placeholder'); if (ph) out.push(ph);
  var cur = up(el), g = 0;
  while (cur && cur.nodeType === 1 && g++ < 4) { if (cur.tagName.toLowerCase() === 'label') { out.push(sval(cur)); break; } cur = up(cur); }
  return out.map(norm);
}
var L = norm(label);
var sc = scopeOf(tgt), ctx = sc.node;
var matches = [];
if (kind === 'fill') {
  xp('.//input[not(@type="hidden")] | .//textarea | .//select | .//*[@role="combobox"] | .//*[@role="textbox"] | .//*[@contenteditable="true"]', ctx)
    .forEach(function (c) { if (visible(c) && enabled(c) && labelsOf(c).indexOf(L) >= 0) matches.push(c); });
} else {
  xp('.//text()[normalize-space(.)=' + lit(L) + ']/..', ctx).forEach(function (e) { if (visible(e) && matches.indexOf(e) < 0) matches.push(e); });
}
function isTgt(m){ return m === tgt || (m.contains && m.contains(tgt)) || (tgt.contains && tgt.contains(m)); }
var ti = -1;
for (var i = 0; i < matches.length; i++) { if (isTgt(matches[i])) { ti = i; break; } }
function center(el){ var r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }
var anchors = [];
if (matches.length > 1 && ti >= 0) {
  for (var k = 0; k < cands.length && k < 6; k++) {
    var T = norm(cands[k]); if (!T || T === L) continue;
    var found = xp('.//text()[normalize-space(.)=' + lit(T) + ']/..', ctx).filter(visible);
    var rec = {text: T, occurrences: found.length, nearest_is_target: false};
    if (found.length === 1) {
      var a = center(found[0]), best = -1, bd = Infinity;
      for (var j = 0; j < matches.length; j++) { var c = center(matches[j]); var d = Math.abs(c[0] - a[0]) + Math.abs(c[1] - a[1]); if (d < bd) { bd = d; best = j; } }
      rec.nearest_is_target = (best === ti); rec.distance = Math.round(bd);
    }
    anchors.push(rec);
  }
}
return JSON.stringify({count: matches.length, target_index: ti, scope: sc.kind, anchors: anchors, label: L});
"""

_LABEL_KEYWORDS = {'TypeText': 'fill', 'TypeSecret': 'fill', 'DropDown': 'fill',
                   'ClickCheckbox': 'fill', 'ClickText': 'text'}
_KWARG_CELL = re.compile(r'^[a-z_]+=')


def _label_form(body: str) -> tuple | None:
    """(keyword, label, census kind) when `body` locates by a LABEL a census can count; None for
    an xpath locator, a ClickItem (an attribute value, not a label) or anything else."""
    cells = _cells(body or '')
    if len(cells) < 2 or cells[0] not in _LABEL_KEYWORDS:
        return None
    loc = cells[1]
    if loc.startswith(('xpath\\=', 'xpath=')) or not loc.strip():
        return None
    return cells[0], loc, _LABEL_KEYWORDS[cells[0]]


def live_disambiguation(drv, target_element, label: str, kind: str, candidates=None) -> dict:
    """The census dict, or {'error': ...} when the page could not answer (never raises)."""
    try:
        raw = drv.execute_script(_CENSUS_JS, target_element, label, kind, list(candidates or [])[:6])
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        if not isinstance(data, dict) or 'count' not in data:
            return {'error': 'the census answered %r' % (str(raw)[:80],)}
        return data
    except Exception as exc:
        return {'error': 'the census raised: %s: %s' % (type(exc).__name__, exc)}


def _with_text_anchor(body: str, text: str) -> str:
    cells = _cells(body)
    pos = next((i for i, c in enumerate(cells) if i > 0 and _KWARG_CELL.match(c)), len(cells))
    return '    '.join(cells[:pos] + ['anchor=%s' % re.sub(r'\s+', ' ', text).strip()] + cells[pos:])


def apply_live_disambiguation(body: str, xp_body: str | None, census: dict | None, row: dict) -> tuple:
    """(live body, dormant label body or None, disambiguation) -- the F189 policy over a census:

      * one visible, enabled match in scope and it is the target  -> the bare label
      * the label repeats live: a ladder candidate that occurs ONCE live and to which the target
        is the nearest match                                       -> `anchor=<that text>`
      * the label repeats live and nothing verifies                 -> the xpath is the live line,
        the label form goes dormant (a bare label would resolve a neighbour and read green)
      * a ClickText whose target is DOM-order match #1              -> the bare label (that is the
        element an unanchored ClickText picks -- measured, crt-qforce-qweb)
      * the one live match is NOT the target                        -> the xpath (fails closed)
      * count 0, no census, an error                                -> the bare label, COULD-NOT-CHECK
    A number never comes out of here."""
    dis = {'index': _described_index(row), 'group_size': row.get('group_size'),
           'anchor_candidates': list(row.get('anchor_candidates') or []),
           'anchor': None, 'live_count': None, 'scope': None}
    lf = _label_form(body)
    if not lf:
        dis.update({'decision': 'not-applicable', 'why': 'the line does not locate by a label'})
        return body, None, dis
    kw, label, kind = lf
    if not census or census.get('error') or 'count' not in census:
        dis.update({'decision': 'bare-label',
                    'why': 'COULD-NOT-CHECK: no live census (%s); the bare label stands unverified'
                           % ((census or {}).get('error') or 'none taken')})
        return body, None, dis
    count, ti = int(census.get('count') or 0), int(census.get('target_index', -1))
    dis.update({'live_count': count, 'scope': census.get('scope')})
    if count == 0:
        dis.update({'decision': 'bare-label',
                    'why': 'COULD-NOT-CHECK: the census found no %s labelled %r in the %s; the bare label stands unverified'
                           % ('control' if kind == 'fill' else 'text', label, census.get('scope'))})
        return body, None, dis
    if count == 1 and ti == 0:
        dis.update({'decision': 'bare-label', 'why': 'unique live in the %s' % census.get('scope')})
        return body, None, dis
    if ti < 0:
        dis.update({'decision': 'xpath-live' if xp_body else 'bare-label',
                    'why': '%s live match%s labelled %r and the target is not among them (the one QWeb would pick is not the target); %s'
                           % (count, '' if count == 1 else 'es', label,
                              'the xpath names the element touched' if xp_body
                              else 'COULD-NOT-DISAMBIGUATE: no xpath form either')})
        return (xp_body, body, dis) if xp_body else (body, None, dis)
    if kind == 'text' and ti == 0:
        dis.update({'decision': 'bare-label',
                    'why': 'repeats %d live; the target is DOM-order match #1, which an unanchored ClickText picks' % count})
        return body, None, dis
    for a in census.get('anchors') or []:
        if a.get('occurrences') == 1 and a.get('nearest_is_target') and a.get('text'):
            dis.update({'decision': 'text-anchor', 'anchor': a['text'],
                        'why': 'repeats %d live; anchor %r occurs once and the target is its nearest match (%s px)'
                               % (count, a['text'], a.get('distance', '?'))})
            return _with_text_anchor(body, a['text']), None, dis
    tried = ', '.join('%r x%s' % (a.get('text'), a.get('occurrences')) for a in (census.get('anchors') or [])) or 'none offered'
    if xp_body:
        dis.update({'decision': 'xpath-live',
                    'why': 'repeats %d live (target is match #%d); no ladder anchor verified (%s); the xpath is the live line and the label form is dormant'
                           % (count, ti + 1, tried)})
        return xp_body, body, dis
    dis.update({'decision': 'bare-label',
                'why': 'COULD-NOT-DISAMBIGUATE: repeats %d live (target is match #%d), no ladder anchor verified (%s) and no xpath form'
                       % (count, ti + 1, tried)})
    return body, None, dis


def compose_for_row_live(drv, target_element, row: dict, rendered: str, form: str = 'keyword') -> dict:
    """The line for ONE matched row with the element in hand: the pure composition, then the live
    census on a label-form line, then the F189 policy."""
    body, xp_body, dis, entry_used = _compose_body(row, rendered)
    dormant = None
    if body:
        lf = _label_form(body)
        if lf:
            census = live_disambiguation(drv, target_element, lf[1], lf[2], row.get('anchor_candidates'))
            body, dormant, dis = apply_live_disambiguation(body, xp_body, census, row)
        else:
            dis.update({'decision': 'not-applicable', 'why': 'the line does not locate by a label'})
    return _render_row(row, rendered, form, body, xp_body, dis, dormant_label=dormant, entry_used=entry_used)


def _row_summary(row: dict) -> dict:
    c0 = (row.get('calls') or [{}])[0] or {}
    return {'n': row.get('n'), 'label': row.get('label'), 'family': row.get('element_type'),
            'tag': row.get('tag'), 'keyword': c0.get('keyword'), 'locator': c0.get('locator'),
            'index': row.get('index'), 'group_size': row.get('group_size'),
            'pattern': row.get('pattern'), 'bucket': row.get('bucket'),
            'xpath': _xp_of(row), 'identity_xpath': row.get('identity_xpath'),
            'confidence': row.get('confidence')}


def _recipe_step_for(parsed: Parsed, target_path: str,
                     rendered: str = '') -> tuple[dict | None, str | None, str | None]:
    """(row, live_step, dormant_step) -- a verified recipe's own step (ClickElement or otherwise)
    whose xpath resolves, in this capture, to exactly this element. The dual-listbox move arrow is
    a STEP of the dual-listbox row's recipe, never a row of its own -- the same fallback
    `build_override._recipe_step_for` runs live. Exactly one of `live_step`/`dormant_step` is set
    when a match is found; both None when nothing resolves.

    D19/F246 (CH-B B1.c): the match is found by rendering every candidate with
    `RT.probe_value(row)` -- a SYNTHETIC review literal, never a real one -- purely to see which
    line's own xpath resolves to `target_path`. The WINNING line then has that literal swapped for
    the event's own recorded value (an extra cell on `rendered`) when it carries one, and goes
    DORMANT instead of live when it does not: a probe literal is never shipped as a recorded step."""
    real_value = _recipe_step_value(rendered)
    for row in parsed.rows:
        try:
            entry = RT._pattern_entry(row)
        except Exception:
            entry = None
        if not entry:
            continue
        probe = RT.probe_value(row)
        try:
            kw_lines, xp_lines = PL.recipe(entry, row, probe)
        except Exception:
            continue
        for step in list(kw_lines) + list(xp_lines):
            xp = _unescape_xpath_step(step)
            if not xp:
                continue
            els = parsed.resolve(xp)
            if len(els) == 1 and parsed.path_of(els[0]) == target_path:
                live, dormant = _recipe_live_step(step.strip(), probe, real_value)
                return row, live, dormant
    return None, None, None


def _roster_form(form: str, org: str | None, url: str | None) -> str:
    """LOOP 3 / A4 (2026-09-20): when GZ_ROSTER_BY_PLATFORM=1 and the caller left `form` at its
    default 'keyword', consult the measured per-platform roster order
    (docs/recorder/patterns/library.json['roster_order'], docs/audit/roster-order-2026-09-20.md)
    and use its top tier's group instead. Default OFF -- with the flag unset this is a no-op and
    every existing caller is byte-identical to before this function existed. An explicit
    form='xpath'/'both' from the caller is NEVER overridden (that is the caller's own choice, same
    doctrine as D14: a hint describes, it never overrides silently)."""
    if form != 'keyword' or os.environ.get('GZ_ROSTER_BY_PLATFORM') != '1':
        return form
    platform = PL.platform_of(org, url)
    return PL.roster_form_for_platform(platform, default=form)


# ------------------------------------------------------- phase 1: consult the store (F227)
# The parity plan's diagnosis: "Three things resolve a control today and they do not agree. ...
# the recorder is the only resolver that starts from zero on a known page." interop has consulted
# the store before driving since 2026-09-15 (phase 0). This is the composer's half.
#
# The rule itself lives in `pom/consult.py` and is shared, because the plan said to write it once.
# Nothing here re-implements the tri-state: this function decides only what a composed PANE does
# with the answer.
#
# WHAT IT DOES NOT DO. It does not change composition. `compose_for_row` still produces exactly the
# line it produced before, and that line survives as a dormant backup whenever the store speaks --
# a person reading the pane is owed the alternative the recorder would have proposed, and the
# store's rung was verified on SOME PAST RUN, on a page that may have changed since. That is the
# same rule F224 applies to a gesture's absorbed stock lines.

_STORE_CACHE: dict = {}

# ------------------------------------------------------------------ the CONTAINER's store (F247)
# THE GAP finding 5 named (docs/audit/challenge-opus-2026-09-22, decision 4): phase 1 wired
# `consult_row` into `compose_from_capture` and `compose_batch`, and BOTH are capture-side. The
# CRT container calls `compose_live_element` (`build_override.py`'s generated library, its
# `_propose`), whose composing returns never consulted -- so the one recorder that runs where a
# customer runs it started from zero on a page the store already knew 116 verified rungs for.
#
# And the second half of the finding, which is why this is not a one-line call: the store lives at
# `~/.claude/state` on THIS machine. A CRT container has no home directory of ours and no store.
# So the container reads a PACK -- a store-shaped tree shipped beside the library
# (`page_pack.py export`) -- and the root of it is this env var.
#
#   GZ_POM_DIR set        -> `Store(state_root=<that>)`; a dir that does not exist answers
#                            unknown-page, which is the tri-state's third answer and not a crash.
#   GZ_POM_DIR unset, and this module is running FROM A BUNDLE (the bundle root carries the
#                            `MANIFEST.json` `build_parser_bundle.py` writes)
#                         -> `<bundle>/../garzai_pom`, i.e. the sibling of `garzai_parser` in the
#                            generated library's own directory. The generated library also sets
#                            the env var itself from `__file__`; this is the backstop for a bundle
#                            imported by anything else.
#   GZ_POM_DIR unset, running from the REPO
#                         -> None. Not `~/.claude/state`: the container path must never silently
#                            read the developer's own store, or "byte-identical with no pack dir"
#                            would be a claim that holds on no machine but this one, and the
#                            replay goldens (which pass no pack dir) would move for a reason that
#                            is not in the sources.
PACK_DIR_ENV = 'GZ_POM_DIR'
_DEFAULT_STORE = object()          # the sentinel for "the caller wants the machine's own store"


def container_pack_dir() -> str | None:
    """The store root a CONTAINER-side compose reads, or None when there is no pack. Never raises."""
    try:
        env = os.environ.get(PACK_DIR_ENV)
        if env is not None:
            return env.strip() or None
        here = os.path.dirname(os.path.abspath(__file__))
        # <bundle>/tools/recorder/crt_override -> <bundle>; the same three levels
        # `build_parser_bundle.ROOT` counts, and the MANIFEST.json is what says it IS a bundle.
        bundle = os.path.abspath(os.path.join(here, '..', '..', '..'))
        if os.path.isfile(os.path.join(bundle, 'MANIFEST.json')):
            return os.path.abspath(os.path.join(bundle, '..', 'garzai_pom'))
    except Exception:
        return None
    return None


#: the PACK cache is its own dict, keyed on (page_key, org, root). `_STORE_CACHE` keeps the exact
#: (page_key, org) key it has always had -- a test that seeds it to freeze a record is relying on
#: that shape (`test_consult_merged_call_2026_09_22._consult_row`), and widening the key silently
#: turned every one of those into an `unknown-page` while the tests still looked like they were
#: exercising the store. Two dicts, two contracts, neither guessing.
_PACK_CACHE: dict = {}


def _store_record(page_key: str | None, org: str | None, state_root: str | None = None):
    """The store record for one page key, loaded at most once per process. Never raises: a
    recording in progress must not die because the store is missing, stale or unreadable.

    `state_root` None is the machine's own store (`~/.claude/state`), which is what the two
    capture-side callers have always read. The container passes its pack dir."""
    if not page_key:
        return None
    cache = _STORE_CACHE if state_root is None else _PACK_CACHE
    ck = (page_key, org) if state_root is None else (page_key, org, state_root)
    if ck in cache:
        return cache[ck]
    rec = None
    try:
        import sys as _sys
        import os as _os
        _pom = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "pom")
        if _pom not in _sys.path:
            _sys.path.insert(0, _pom)
        from store import Store                      # noqa: F401
        rec = Store(state_root=state_root).get(page_key, org) if state_root else Store().get(page_key, org)
    except Exception:
        rec = None
    cache[ck] = rec
    return rec


def consult_row(out: dict, row: dict, page_key: str | None, org: str | None,
                indent: str = '    ', store_root=_DEFAULT_STORE) -> dict:
    """Fold a store answer into a composed result, IN PLACE, and always say what happened.

    `out['consult']` is written on every call -- verified, known-unverified, unknown-control,
    unknown-page or a skip reason -- because a pane that silently did not consult is
    indistinguishable from one whose store had nothing, and the whole point of this phase is to be
    able to tell those apart.

    `store_root` is the ONE thing the container changes (F247). Left at its sentinel it is the
    machine's own store, which is what the two capture-side callers have always read. `None` means
    "there is no pack here": the answer is `unknown-page` and the derived line stands, byte for
    byte -- never a silent fall back to `~/.claude/state`, which a container does not have and a
    replay must not read.
    """
    out.setdefault('consult', None)
    if not out.get('line'):
        out['consult'] = {'verdict': 'skipped', 'why': 'nothing was composed for this row'}
        return out
    label = (row or {}).get('label')
    family = (row or {}).get('element_type')
    try:
        import sys as _sys
        import os as _os
        _pom = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "pom")
        if _pom not in _sys.path:
            _sys.path.insert(0, _pom)
        import consult as _consult
        if store_root is _DEFAULT_STORE:
            record = _store_record(page_key, org)
        elif store_root:
            record = _store_record(page_key, org, str(store_root))
        else:
            record = None            # no pack dir: consult() answers unknown-page and says why
        answer = _consult.consult(record, label, family, page_key=page_key)
        if store_root is not _DEFAULT_STORE and not store_root:
            answer = dict(answer, why=(
                'no page-object pack is shipped with this build (%s is unset and no '
                '<library>/garzai_pom is on disk) -- deriving, exactly as before this build'
                % PACK_DIR_ENV))
    except Exception as exc:
        out['consult'] = {'verdict': 'COULD-NOT-CHECK',
                          'why': '%s while consulting the store (%s)' % (type(exc).__name__, exc)}
        return out
    out['consult'] = {'verdict': answer['verdict'], 'why': answer['why'],
                      'element_id': answer.get('element_id')}
    if answer['verdict'] != _consult.VERIFIED or not answer.get('rung'):
        return out                                   # derive, exactly as before
    rung = answer['rung']
    derived = (out.get('line') or '').strip()
    d_kw, d_args, d_kwargs = split_step_body(derived)
    n_pass = int(rung.get('n_verified') or 0)
    # F246 (challenge swarm C1): the rung supplies the LOCATOR, the recorded step supplies the
    # DATA. Rebuilding the line from `rung['args']` alone dropped the typed value on 5 rows of the
    # Zoo capture, `tag=` on every ClickItem and `index` on 37 of 73 -- each stamped with the
    # strongest note the pane can carry. `pom/consult.merged_call` is the ONE rule, shared with
    # the Dock, because the two recorders had drifted onto different answers for the same control.
    call = _consult.merged_call(rung, {'kw': d_kw, 'args': d_args, 'kwargs': d_kwargs},
                                {'tag': (row or {}).get('tag'),
                                 'index': (out.get('disambiguation') or {}).get('index')})
    out['consult']['merge'] = call['why']
    rung_line = RT._rf(rung.get('kw'),
                       *[str(a) for a in (rung.get('args') or [])],
                       **DA.to_call_kwargs(dict(rung.get('kwargs') or {}))).strip()
    if not call['from_store']:
        # The store knows the CONTROL and not this ACTION (a verified ClickElement under a step
        # that types). The derived line stays LIVE and the rung becomes a dormant backup -- never
        # the other way round: a rung that cannot carry the step composes a call that silently
        # does nothing, which is this codebase's signature failure.
        if rung_line:
            backups = list(out.get('backups') or [])
            backups.insert(0, '%s#   backup: %s' % (
                indent, annotate(rung_line, 'AI POM store rung, %d live pass(es) -- a different '
                                            'action on this control' % n_pass)))
            out['backups'] = backups
        out['why'] = '%s; %s' % (out.get('why') or 'parser proposal', call['why'])
        return out
    body = RT._rf(call['kw'], *call['args'], **DA.to_call_kwargs(call['kwargs'])).strip()
    if not body:
        out['consult']['why'] = 'the store rung carried no keyword -- kept the derived line'
        return out
    # PROVENANCE. This line did NOT come from the parser, and must not carry the parser's note.
    # `UNVERIFIED` reads "unverified: parser proposal" -- on a rung a live run resolved and read
    # back, that is two false claims in one cell. Same error class as F224's composed rungs
    # claiming to be stock recorder lines: a reader acts on the note. And it does not claim more
    # than it has either: when a VALUE was folded in, the value is this recording's and was never
    # verified by anything, so the note says LOCATOR rather than rung (F246).
    note = ('# verified: AI POM store rung, %d live pass(es)' % n_pass
            if len(call['args']) < 2 else
            "# verified: AI POM store locator, %d live pass(es); the value is this recording's"
            % n_pass)
    out['line'] = '%s%s    %s' % (indent, body, note)
    backups = list(out.get('backups') or [])
    if derived:
        backups.insert(0, '%s#   backup: %s' % (
            indent, annotate(derived, 'the line this recorder would have derived')))
    out['backups'] = backups
    out['why'] = 'store rung (%s)' % answer['why']
    return out

def compose_from_capture(html: str, url: str, org: str, target_identity_xpath: str,
                         rendered: str, form: str = 'keyword', descriptor: dict | None = None) -> dict:
    """html in, line out -- no driver, no network, no org contact.

    `target_identity_xpath` names the recorded element inside this capture (live, the caller holds
    the element itself and `compose_live_element` does the `===`). Returns
    {'line', 'xpath_line', 'row', 'why', ...}: `line` is the step to record, '' means record
    nothing, None means let the recorder's own line stand.
    """
    form = _roster_form(form, org, url)
    t0 = time.time()
    parsed = parse_capture(html, url, org)
    out = {'line': None, 'xpath_line': None, 'row': None, 'why': None,
           'page_key': parsed.page_key, 'parse_ms': parsed.parse_ms, 'rows': len(parsed.rows)}
    els = parsed.resolve(target_identity_xpath) if target_identity_xpath else []
    if len(els) != 1:
        # no identity, or one that names no single node: the page's own description still can
        if descriptor:
            row, why = DESC.find_row(parsed.rows, descriptor, get=DESC.parsed_get)
            if row is not None:
                out.update(compose_for_row(row, rendered, form))
                consult_row(out, row, parsed.page_key, org, _indent(rendered))
                out.update({'row': _row_summary(row), 'matched_by': 'descriptor', 'descriptor_why': why,
                            'compose_ms': round((time.time() - t0) * 1000, 1)})
                return out
            out['descriptor_why'] = why
        out['why'] = 'COULD-NOT-CHECK: the target xpath matched %d elements in the capture%s' % (
            len(els), ('; and the descriptor named no row: %s' % out['descriptor_why']) if descriptor else '')
        out['compose_ms'] = round((time.time() - t0) * 1000, 1)
        return out
    target_path = parsed.path_of(els[0])
    row = None
    for r in parsed.rows:
        ix = r.get('identity_xpath')
        if not ix:
            continue
        cands = parsed.resolve(ix)
        if len(cands) == 1 and parsed.path_of(cands[0]) == target_path:
            row = r
            break
    if row is None:
        row, step, dormant = _recipe_step_for(parsed, target_path, rendered)
        if step:
            entry = None
            try:
                entry = RT._pattern_entry(row)
            except Exception:
                entry = None
            out.update({'line': _stamp(_indent(rendered) + step, _recipe_note(entry)),
                        'row': _row_summary(row), 'why': 'recipe step of row %s (%s)' % (row.get('n'), row.get('pattern'))})
            # F258 (2026-09-23): this branch never called consult_row at all, while
            # compose_live_element's OWN recipe branch (below, CH-B B1.a) does -- with the SAME
            # neutered target row (label/element_type stripped to None, only `tag` kept), because
            # `row` here is the recipe's OWNER (e.g. the dual-listbox row), not the element this
            # STEP resolves to, and a target identity with no label never resolves past
            # unknown-control in pom/consult.consult -- the same reason `compose_live_element`
            # gives at its call site. Both branches produce the same LINE either way (a target
            # with no label cannot land `# verified`), but before this fix the offline decision
            # record carried no `consult` key at all while the live one carried
            # {'verdict': 'unknown-control', ...} -- CLAUDE.md's standing rule for this pair
            # ("the per-event AND the batch path -- they must stay byte-identical") held for the
            # rendered pane and not for the decision record behind it (V-B section 3c).
            target_row = {'label': None, 'element_type': None, 'tag': row.get('tag')}
            consult_row(out, target_row, parsed.page_key, org, _indent(rendered))
        elif dormant:
            # D19/F246 (CH-B B1.c): the winning step needed a value this event did not record
            # (e.g. a probe-only match on a fill line, never the dual-listbox arrow's own click,
            # which carries no {value} slot) -- kept dormant, never shipped as a live literal.
            out.update({'line': None, 'row': _row_summary(row),
                        'backups': [_recipe_dormant(_indent(rendered), dormant,
                                    'recipe step of row %s (%s), needs a value this event did '
                                    'not record' % (row.get('n'), row.get('pattern')))],
                        'why': ('recipe step of row %s (%s) needed a value this event did not '
                                'record -- kept dormant (D19)' % (row.get('n'), row.get('pattern')))})
        else:
            out['why'] = 'no parsed row resolves to this element'
        out['compose_ms'] = round((time.time() - t0) * 1000, 1)
        return out
    out.update(compose_for_row(row, rendered, form))
    consult_row(out, row, parsed.page_key, org, _indent(rendered))
    out['row'] = _row_summary(row)
    out['matched_by'] = 'identity'
    out['compose_ms'] = round((time.time() - t0) * 1000, 1)
    return out


# ----------------------------------------------------------------------------- the batch layer
def _owner_index(parsed: Parsed) -> tuple[dict, dict]:
    """ONE resolve pass over the capture: every row's identity xpath evaluated exactly once.

    Returns (path_by_n, owner_by_path).  `owner_by_path` is the row `compose_from_capture` would
    have picked for an element at that tree path -- the FIRST row, in row order, whose identity
    xpath resolves to exactly one node there.  That first-wins rule is not an optimisation, it is
    the per-event path's own behaviour (its `for r in parsed.rows: ... break`), so two rows that
    share one element compose the same line here as they do there.

    Why it exists (ledger F51, 2026-09-18): `compose_from_capture` re-ran that inner loop for EVERY
    control, so a page of n controls paid O(n^2) xpath evaluations -- 901 controls on
    docs/dom-captures/web-ant-design/3-transfer-idle.html were ~405,000 evaluations and 41.9 s of
    the 199.3 s a snapshot of that one capture cost.  The per-event path is unchanged: a recorder
    event answers about ONE element and must not pay for the whole page.
    """
    path_by_n: dict = {}
    owner_by_path: dict = {}
    for r in parsed.rows:
        ix = r.get('identity_xpath')
        if not ix:
            continue
        cands = parsed.resolve(ix)
        if len(cands) != 1:
            path_by_n[r.get('n')] = None
            continue
        p = parsed.path_of(cands[0])
        path_by_n[r.get('n')] = p
        owner_by_path.setdefault(p, r)
    return path_by_n, owner_by_path


def compose_batch(html: str, url: str | None, org: str | None, form: str = 'keyword',
                  rendered_for=None) -> dict:
    """Every control of ONE capture, composed in one pass: parse once, resolve each row's identity
    once, compose all controls.  The answer for a row is byte-identical to
    `compose_from_capture(html, url, org, row['identity_xpath'], rendered_for(row), form)` --
    proven row by row in tools/recorder/tests/test_compose_live.py.

    `rendered_for(row) -> str` supplies the recorded action line per row (there is no recorder
    event in a corpus pass; `retest_set.synthetic_rendered` is the caller that builds one from the
    row's own family).  Returns
    {'rows': <every parsed row>, 'composed': [(row, result), ...], 'page_key', 'parse_ms',
     'batch_ms'} -- one `composed` entry per row that carries an identity xpath.
    """
    form = _roster_form(form, org, url)
    t0 = time.time()
    parsed = parse_capture(html, url, org)
    path_by_n, owner_by_path = _owner_index(parsed)
    composed: list = []
    for row in parsed.rows:
        ix = row.get('identity_xpath')
        if not ix:
            continue
        rendered = rendered_for(row) if rendered_for else ''
        out = {'line': None, 'xpath_line': None, 'row': None, 'why': None,
               'page_key': parsed.page_key, 'parse_ms': parsed.parse_ms, 'rows': len(parsed.rows)}
        target_path = path_by_n.get(row.get('n'))
        if target_path is None:
            # the same tri-state the per-event path prints: an identity that names no single node
            # is COULD-NOT-CHECK with its own count, never a silent skip and never a pass.
            n_match = len(parsed.resolve(ix))
            out['why'] = 'COULD-NOT-CHECK: the target xpath matched %d elements in the capture' % n_match
            out['compose_ms'] = 0.0
            composed.append((row, out))
            continue
        owner = owner_by_path.get(target_path)
        if owner is None:                     # unreachable while this row resolved; kept honest
            out['why'] = 'no parsed row resolves to this element'
            out['compose_ms'] = 0.0
            composed.append((row, out))
            continue
        t1 = time.time()
        out.update(compose_for_row(owner, rendered, form))
        # F227: the batch pass consults too, or it stops being byte-identical to the per-event
        # path -- which `test_the_batch_pass_composes_every_control_exactly_as_the_per_event_path`
        # exists to catch, and did, the moment only one side consulted.
        consult_row(out, owner, parsed.page_key, org, _indent(rendered))
        out['row'] = _row_summary(owner)
        out['matched_by'] = 'identity'
        out['compose_ms'] = round((time.time() - t1) * 1000, 1)
        composed.append((row, out))
    return {'rows': parsed.rows, 'composed': composed, 'page_key': parsed.page_key,
            'parse_ms': parsed.parse_ms, 'batch_ms': round((time.time() - t0) * 1000, 1)}


# ----------------------------------------------------------------------------- the live layer
def serializer_js(max_depth: int = 120) -> str:
    """The SAME in-page serializer `up.py --op capture` ships (tools/dom-miner/cdp_capture.py):
    it pierces open shadow roots (synthetic and native) and emits them as <template>, drops
    display:none subtrees and scrubs secrets. Never write a second serializer."""
    import cdp_capture                                  # stdlib-only import, kept lazy
    return cdp_capture.build_serializer(max_depth)


_MATCH_JS = """
var xps = arguments[0], tgt = arguments[1];
for (var i = 0; i < xps.length; i++) {
  var r;
  try { r = document.evaluate(xps[i], document, null, 7, null); } catch (e) { continue; }
  if (r.snapshotLength === 1 && r.snapshotItem(0) === tgt) { return i; }
}
return -1;
"""


def live_capture(drv, org: str | None = None, max_depth: int = 120) -> dict:
    """ONE round trip: the serializer runs in the page and hands back {html, stats, path, host}."""
    t0 = time.time()
    # `return (` must open on the SAME line: the serializer text begins with a newline, and
    # `return\n(function(){...})()` is `return;` under JavaScript's automatic semicolon insertion
    # -- measured 2026-09-18, the call came back None in 4 ms and lxml then said
    # "ParserError: Document is empty" on an empty capture.
    raw = drv.execute_script('return (' + serializer_js(max_depth) + ');')
    data = json.loads(raw) if isinstance(raw, str) else (raw or {})
    ms = round((time.time() - t0) * 1000, 1)
    host, path = data.get('host') or '', data.get('path') or ''
    url = ('https://%s%s' % (host, path)) if host else (drv.current_url or '')
    html = capture_header(url, org, path_hint=path, stats=data.get('stats')) + (data.get('html') or '')
    return {'html': html, 'url': url, 'stats': data.get('stats') or {}, 'capture_ms': ms,
            'title': data.get('title')}


# The page's own answer to "is this still the same page?". A NODE COUNT alone said yes to a page
# that re-rendered in place with the same number of nodes -- a record page switching to inline edit,
# a datatable swapping a row, a wizard step replacing its fields -- so the stale parse answered with
# a label that is no longer on the page (challenge D10 finding 8, 2026-09-19). The count still
# travels, and the CONTENT of the controls travels with it: tag plus the first of
# aria-label / name / placeholder / text, for the controls and their labels, capped and hashed.
# One execute_script, the same round trip the count cost.
_FINGERPRINT_JS = r"""
/* __gzFingerprint */
var n = document.getElementsByTagName('*').length;
var els = document.querySelectorAll('input,select,textarea,button,a,label,legend,[role],[contenteditable="true"]');
var out = [String(n), String(els.length)];
var cap = els.length < 400 ? els.length : 400;
for (var i = 0; i < cap; i++) {
  var e = els[i], t = '';
  try { t = e.getAttribute('aria-label') || e.getAttribute('name') || e.getAttribute('placeholder') || e.textContent || ''; } catch (err) { t = ''; }
  out.push(e.tagName + '=' + String(t).replace(/\s+/g, ' ').trim().slice(0, 40));
}
return out.join('|');
"""


def _fingerprint(drv) -> str:
    """A content-sensitive page fingerprint, or `'-1'` when the page could not answer.

    Never a bare node count: two different pages, and one page before and after an in-place
    re-render, routinely carry the same count."""
    try:
        raw = drv.execute_script(_FINGERPRINT_JS)
    except Exception:
        return '-1'
    return hashlib.sha1(str(raw).encode('utf-8', 'replace')).hexdigest()[:16]


CAPTURE_MIN_INTERVAL_S = 5.0     # a capture runs on the page's main thread; on a large Setup page it
                                 # is the stall the user saw when every click recaptured (2026-09-18)
# STRICTLY BELOW the page's own `ASK_MS` (6000 ms in the generated library's injected JS). The two
# were inverted -- the page gave up at 6 s and pushed the recorder's line while the driver worked on
# to 8 s -- so an abandoned request kept driving the browser while the page had already started the
# next event's ask(): two handlers on one selenium driver (challenge D10 finding 7, 2026-09-19).
# Whoever changes either number changes both: 4 < 6 is the invariant, asserted in the challenge file.
SCRIPT_TIMEOUT_S = 4
PAGE_ASK_MS = 6000               # what the injected JS waits; this module must finish inside it


def capture_allowed(cache: dict, now: float | None = None) -> tuple[bool, float]:
    """(allowed, seconds since the last capture). At most one capture per CAPTURE_MIN_INTERVAL_S per
    composer: a page that changes faster than that is answered COULD-NOT-CHECK, never re-walked."""
    now = time.time() if now is None else now
    last = float(cache.get('last_capture_t') or 0.0)
    since = now - last
    return (last == 0.0 or since >= CAPTURE_MIN_INTERVAL_S), since


def compose_live_element(drv, target_element, rendered: str, org: str | None = None,
                         cache: dict | None = None, url: str | None = None,
                         form: str = 'keyword', descriptor: dict | None = None) -> dict:
    """The driver layer: one capture per page (cached on url + node count), one execute_script to
    find the recorded element among the parsed rows by DOM identity (`===`), then the SAME pure
    composition. Recaptures once when the target is not among the cached rows -- the page moved.

    `descriptor` is what the PAGE said about the element (tools/recorder/crt_override/descriptor.py).
    It is the second way in, and on a native-shadow control it is the only one: the serializer puts
    that control in the capture and the parser gives it a row, but `document.evaluate` from the
    driver cannot reach into a native shadow root, so every identity xpath answers zero and the
    `===` match above finds nothing (ledger F40, Lightning Setup, 2026-09-18). Label + family
    through the SAME rule `pom/match.py` states then names the row, and the answer says which way
    it got there -- `matched_by: identity | descriptor`.

    IT CONSULTS THE STORE (F247). Every one of the three composing returns below goes through the
    SAME `consult_row` the two capture-side entry points use -- there is no third copy of the rule
    -- against a store rooted at `container_pack_dir()`. No pack dir is `unknown-page`: the derived
    line stands byte for byte, which is what the committed replay goldens (which ship no pack) pin.
    """
    cache = cache if cache is not None else {}
    pack_dir = container_pack_dir()
    url = url or (drv.current_url or '')
    fp = _fingerprint(drv)
    out_extra = {'recaptured': False, 'capture_ms': cache.get('capture_ms', 0.0)}
    try:
        drv.set_script_timeout(SCRIPT_TIMEOUT_S)   # a navigation mid-capture must not hold the driver 30 s
    except Exception:
        pass
    for attempt in (1, 2):
        if cache.get('url') != url or cache.get('fingerprint') != fp or 'parsed' not in cache:
            ok, since = capture_allowed(cache)
            if not ok:
                return {'line': None, 'xpath_line': None, 'row': None,
                        'why': 'COULD-NOT-CHECK: capture budget: the page changed %.1f s after the last capture (minimum %.0f s)' % (since, CAPTURE_MIN_INTERVAL_S), **out_extra}
            # A capture that RAISES is the third state, not an exception thrown at the caller:
            # every other failure here returns a COULD-NOT-CHECK dict, and a page unloading
            # mid-serialize (or an empty document -- measured 2026-09-18, `ParserError: Document is
            # empty`) must read the same way (challenge D10 finding 9, 2026-09-19).
            try:
                shot = live_capture(drv, org)
                fresh = parse_capture(shot['html'], shot['url'], org)
            except Exception as exc:
                return {'line': None, 'xpath_line': None, 'row': None,
                        'why': 'COULD-NOT-CHECK: the capture failed: %s: %s' % (type(exc).__name__, exc),
                        **out_extra}
            # the budget is spent by a capture that PARSED, never by one that failed: stamping it
            # first blinded the composer for the following 5 s every time a capture went wrong
            cache['last_capture_t'] = time.time()
            # the cache key is the DRIVER's url, never the serializer's rendering of it: when the two
            # differed in form every event re-captured, which is the Setup stall (2026-09-18)
            cache.update({'url': url, 'shot_url': shot['url'], 'fingerprint': fp, 'capture_ms': shot['capture_ms'],
                          'parsed': fresh})
            cache['xpaths'] = [r.get('identity_xpath') or '' for r in cache['parsed'].rows]
            out_extra['capture_ms'] = shot['capture_ms']
            out_extra['recaptured'] = attempt > 1 or out_extra['recaptured']
        parsed: Parsed = cache['parsed']
        t0 = time.time()
        try:
            i = int(drv.execute_script(_MATCH_JS, cache['xpaths'], target_element))
        except Exception as exc:
            return {'line': None, 'xpath_line': None, 'row': None,
                    'why': 'COULD-NOT-CHECK: identity match failed live: %s' % exc, **out_extra}
        match_ms = round((time.time() - t0) * 1000, 1)
        if i >= 0:
            res = compose_for_row_live(drv, target_element, parsed.rows[i], rendered, form)
            consult_row(res, parsed.rows[i], parsed.page_key, org, _indent(rendered),
                        store_root=pack_dir)
            res.update({'row': _row_summary(parsed.rows[i]), 'page_key': parsed.page_key,
                        'match_ms': match_ms, 'rows': len(parsed.rows), 'matched_by': 'identity',
                        **out_extra})
            return res
        # no identity: what the PAGE said about the element still names a row (F40)
        if descriptor:
            row, why = DESC.find_row(parsed.rows, descriptor, get=DESC.parsed_get)
            if row is not None:
                res = compose_for_row_live(drv, target_element, row, rendered, form)
                consult_row(res, row, parsed.page_key, org, _indent(rendered),
                            store_root=pack_dir)
                res.update({'row': _row_summary(row), 'page_key': parsed.page_key,
                            'match_ms': match_ms, 'rows': len(parsed.rows),
                            'matched_by': 'descriptor', 'descriptor_why': why, **out_extra})
                if res.get('why'):
                    res['why'] = '%s (by descriptor: %s)' % (res['why'], why)
                return res
            out_extra['descriptor_why'] = why
        # no row: a recipe STEP may name it (the dual-listbox move arrow). Each candidate is
        # rendered with a PROBE value purely to find which one's xpath resolves live -- the same
        # D19/F246 rule `_recipe_step_for` applies offline (CH-B B1.c).
        real_value = _recipe_step_value(rendered)
        steps, owners = [], []
        for row in parsed.rows:
            try:
                entry = RT._pattern_entry(row)
                if not entry:
                    continue
                probe = RT.probe_value(row)
                kw_lines, xp_lines = PL.recipe(entry, row, probe)
            except Exception:
                continue
            for step in list(kw_lines) + list(xp_lines):
                xp = _unescape_xpath_step(step)
                if xp:
                    steps.append(xp)
                    owners.append((row, step.strip(), entry, probe))
        if steps:
            try:
                j = int(drv.execute_script(_MATCH_JS, steps, target_element))
            except Exception:
                j = -1
            if j >= 0:
                row, step, entry, probe = owners[j]
                live, dormant = _recipe_live_step(step, probe, real_value)
                if live:
                    res = {'line': _stamp(_indent(rendered) + live, _recipe_note(entry)),
                           'xpath_line': None,
                           'why': 'recipe step of row %s (%s)' % (row.get('n'), row.get('pattern'))}
                    # CH-B B1.a: this STEP is a different element than `row` itself -- `row` is
                    # merely the recipe's OWNER (e.g. the dual-listbox row; the arrow the person
                    # actually acted on has no row of its own). Consulting with the OWNER's
                    # identity let its verified rung (arity-0 against a ClickElement derived call,
                    # same as this step) silently replace the arrow's step with the LISTBOX's own
                    # call -- the store-led call's own arity check cannot tell "same control" from
                    # "different control", only "compatible action shape". A target identity with
                    # no label never resolves past `unknown-control` in `pom/consult.consult`, so
                    # `# verified` can only land here when the store genuinely answers for THIS
                    # step, never for the row that happens to carry its recipe.
                    target_row = {'label': None, 'element_type': None, 'tag': row.get('tag')}
                    consult_row(res, target_row, parsed.page_key, org, _indent(rendered),
                                store_root=pack_dir)
                else:
                    res = {'line': None, 'xpath_line': None,
                           'backups': [_recipe_dormant(_indent(rendered), dormant,
                                       'recipe step of row %s (%s), needs a value this event did '
                                       'not record' % (row.get('n'), row.get('pattern')))],
                           'why': ('recipe step of row %s (%s) needed a value this event did not '
                                   'record -- kept dormant (D19)' % (row.get('n'), row.get('pattern'))),
                           'consult': {'verdict': 'skipped', 'why': 'nothing was composed for this row'}}
                res.update({'row': _row_summary(row), 'page_key': parsed.page_key,
                            'match_ms': match_ms, 'rows': len(parsed.rows), **out_extra})
                return res
        if attempt == 1 and _fingerprint(drv) != cache.get('fingerprint'):
            # the page moved under us: ONE recapture, and only when the DOM actually changed -- a
            # second walk of the same DOM yields the same rows and was the Setup stall (2026-09-18)
            cache.pop('parsed', None)
            out_extra['recaptured'] = True
            fp = _fingerprint(drv)
            continue
        return {'line': None, 'xpath_line': None, 'row': None, 'page_key': parsed.page_key,
                'why': 'no parsed row and no recipe step resolves to this element',
                'match_ms': match_ms, 'rows': len(parsed.rows), **out_extra}


# ----------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--capture', required=True, help='a capture html file (ours, never the recorder\'s snapshot)')
    ap.add_argument('--org', default=None)
    ap.add_argument('--url', default=None, help='the page url (the partition comes from it)')
    ap.add_argument('--target', required=True, help='identity xpath of the recorded element')
    ap.add_argument('--rendered', default='', help="the recorder's own line for the event")
    ap.add_argument('--form', default='keyword', choices=('keyword', 'xpath', 'both'))
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    html = open(a.capture, errors='replace').read()
    res = compose_from_capture(html, a.url, a.org, a.target, a.rendered, a.form)
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        print('why      :', res['why'])
        print('row      :', json.dumps(res.get('row')) if res.get('row') else '-')
        print('line     :', repr(res['line']))
        print('xpath    :', repr(res['xpath_line']))
        print('page key :', res.get('page_key'), '| rows', res.get('rows'),
              '| parse %sms compose %sms' % (res.get('parse_ms'), res.get('compose_ms')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
