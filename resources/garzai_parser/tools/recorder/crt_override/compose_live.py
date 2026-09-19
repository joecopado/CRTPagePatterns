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
(the JSON parser + the xpath ladder + the identity xpath), `pattern_library` (buckets + the
verified recipes) and `disambiguation_args.to_call_kwargs` (the ONE place index becomes QWeb's
numeric anchor) are consumed as they are. The review is still what turns `unverified` into
`verified`; this only stops a blank page from being worse than a reviewed one.

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
import pattern_library as PL       # noqa: E402  (buckets + the verified recipes)
import disambiguation_args as DA   # noqa: E402  (index -> QWeb's numeric anchor)
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


def _anchor_of(row: dict) -> str | None:
    """The member's position among same-label matches, as QWeb's numeric anchor -- via the ONE
    converter. A control that occurs once carries neither (D4, narrowed by stream 1C)."""
    idx = row.get('index_corrected') if 'index_corrected' in row else row.get('index')
    if not idx or (row.get('group_size') or 1) <= 1:
        return None
    return DA.to_call_kwargs({'index': idx}).get('anchor')


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
        return line.strip()
    return None


def _body(row: dict, rendered: str, entry: dict | None) -> str | None:
    """Our proposed line for this row and this recorded action, or '' to record nothing, or None
    to let the recorder's own line stand. The shape mirrors `build_override._our_line_body`, with
    one difference that is the whole point: there are no live verdicts here, so the LABEL form is
    what the parser proposes and the xpath is the backstop -- never a silent downgrade to xpath
    because a keyword was measured bad (that knowledge only exists in a review)."""
    cells = _cells(rendered)
    action = cells[0] if cells else ''
    value = cells[-1] if len(cells) >= 3 else None
    fam = row.get('family_corrected') or row.get('element_type')
    label = _label_of(row)
    anchor = _anchor_of(row)
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
        return _recipe_first_action(entry, row, value)
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
    return '%s#   backup: %s   (stock recorder line, unverified)' % (indent, (text or '').strip())


def omni_pair_lines(label: str | None, option: str, stock_open: str, stock_option: str,
                    indent: str = '    ') -> tuple[str, list]:
    """(the one composed line, the dormant backup lines) for one combobox pick.

    Returns ('', []) when there is no label to name the control with -- a keyword whose first
    argument would be blank is not a proposal, it is a guess, and the stock lines stand instead.

    Returns ('', [two backups]) for a PLACEHOLDER pick: nothing is composed AND the held open
    click is dropped too, but both stock lines are kept as dormant backups. The empty line with a
    NON-empty backup list is what tells the caller apart from the no-label case."""
    lab = omni_label(label)
    opt = (option or '').strip()
    if not lab or not opt:
        return '', []
    open_line, _ = omni_open_click_line(label, stock_open)
    backups = [_dormant(indent, s) for s in (open_line, stock_option) if (s or '').strip()]
    if omni_placeholder_option(opt):
        return '', backups
    line = '%s%s    %s' % (indent, RT._rf('Omni Select', lab, opt).strip(), UNVERIFIED)
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
        return '', '', ('an OmniStudio %s, but the element carries no data-omni-key: the stock '
                        'TypeText line stands' % tag.rsplit('-', 1)[-1])
    value, mask_why = omni_mask_value(value)
    if not value:
        return '', '', mask_why
    if tag == _OMNI_DATE_PICKER:
        iso = omni_iso_date(value)
        if not iso:
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


def compose_for_row(row: dict, rendered: str, form: str = 'keyword') -> dict:
    """The line for ONE matched row. Split out so the pure and the live layers compose identically."""
    entry = None
    try:
        entry = RT._pattern_entry(row)     # a library entry whose recipe is one to RUN
    except Exception:
        entry = None
    body = _body(row, rendered, entry)
    xp_body = xpath_form(row, body) if body else None
    if body is None:
        return {'line': None, 'xpath_line': xp_body, 'why': 'no proposal for this action on this control'}
    if body == '':
        return {'line': '', 'xpath_line': None, 'why': 'recorder noise on an input (focus click / tab-out); nothing recorded'}
    ind = _indent(rendered)
    chosen = body
    if form == 'xpath' and xp_body:
        chosen = xp_body
    elif form == 'both' and xp_body and xp_body != body:
        chosen = body + '    # xpath form: ' + xp_body
    return {'line': '%s%s    %s' % (ind, chosen.strip(), UNVERIFIED),
            'xpath_line': ('%s%s    %s' % (ind, xp_body.strip(), UNVERIFIED)) if xp_body else None,
            'why': 'parser proposal for row %s' % row.get('n')}


def _row_summary(row: dict) -> dict:
    c0 = (row.get('calls') or [{}])[0] or {}
    return {'n': row.get('n'), 'label': row.get('label'), 'family': row.get('element_type'),
            'tag': row.get('tag'), 'keyword': c0.get('keyword'), 'locator': c0.get('locator'),
            'index': row.get('index'), 'group_size': row.get('group_size'),
            'pattern': row.get('pattern'), 'bucket': row.get('bucket'),
            'xpath': _xp_of(row), 'identity_xpath': row.get('identity_xpath'),
            'confidence': row.get('confidence')}


def _recipe_step_for(parsed: Parsed, target_path: str) -> tuple[dict | None, str | None]:
    """A verified recipe's own ClickElement step whose xpath resolves, in this capture, to exactly
    this element. The dual-listbox move arrow is a STEP of the dual-listbox row's recipe, never a
    row of its own -- the same fallback `build_override._recipe_step_for` runs live."""
    for row in parsed.rows:
        try:
            entry = RT._pattern_entry(row)
        except Exception:
            entry = None
        if not entry:
            continue
        try:
            kw_lines, xp_lines = PL.recipe(entry, row, RT.probe_value(row))
        except Exception:
            continue
        for step in list(kw_lines) + list(xp_lines):
            xp = _unescape_xpath_step(step)
            if not xp:
                continue
            els = parsed.resolve(xp)
            if len(els) == 1 and parsed.path_of(els[0]) == target_path:
                return row, step.strip()
    return None, None


def compose_from_capture(html: str, url: str, org: str, target_identity_xpath: str,
                         rendered: str, form: str = 'keyword', descriptor: dict | None = None) -> dict:
    """html in, line out -- no driver, no network, no org contact.

    `target_identity_xpath` names the recorded element inside this capture (live, the caller holds
    the element itself and `compose_live_element` does the `===`). Returns
    {'line', 'xpath_line', 'row', 'why', ...}: `line` is the step to record, '' means record
    nothing, None means let the recorder's own line stand.
    """
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
        row, step = _recipe_step_for(parsed, target_path)
        if step:
            out.update({'line': '%s%s    %s' % (_indent(rendered), step, UNVERIFIED),
                        'row': _row_summary(row), 'why': 'recipe step of row %s (%s)' % (row.get('n'), row.get('pattern'))})
        else:
            out['why'] = 'no parsed row resolves to this element'
        out['compose_ms'] = round((time.time() - t0) * 1000, 1)
        return out
    out.update(compose_for_row(row, rendered, form))
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
    """
    cache = cache if cache is not None else {}
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
            res = compose_for_row(parsed.rows[i], rendered, form)
            res.update({'row': _row_summary(parsed.rows[i]), 'page_key': parsed.page_key,
                        'match_ms': match_ms, 'rows': len(parsed.rows), 'matched_by': 'identity',
                        **out_extra})
            return res
        # no identity: what the PAGE said about the element still names a row (F40)
        if descriptor:
            row, why = DESC.find_row(parsed.rows, descriptor, get=DESC.parsed_get)
            if row is not None:
                res = compose_for_row(row, rendered, form)
                res.update({'row': _row_summary(row), 'page_key': parsed.page_key,
                            'match_ms': match_ms, 'rows': len(parsed.rows),
                            'matched_by': 'descriptor', 'descriptor_why': why, **out_extra})
                if res.get('why'):
                    res['why'] = '%s (by descriptor: %s)' % (res['why'], why)
                return res
            out_extra['descriptor_why'] = why
        # no row: a recipe STEP may name it (the dual-listbox move arrow)
        steps, owners = [], []
        for row in parsed.rows:
            try:
                entry = RT._pattern_entry(row)
                if not entry:
                    continue
                kw_lines, xp_lines = PL.recipe(entry, row, RT.probe_value(row))
            except Exception:
                continue
            for step in list(kw_lines) + list(xp_lines):
                xp = _unescape_xpath_step(step)
                if xp:
                    steps.append(xp)
                    owners.append((row, step.strip()))
        if steps:
            try:
                j = int(drv.execute_script(_MATCH_JS, steps, target_element))
            except Exception:
                j = -1
            if j >= 0:
                row, step = owners[j]
                return {'line': '%s%s    %s' % (_indent(rendered), step, UNVERIFIED),
                        'xpath_line': None, 'row': _row_summary(row), 'page_key': parsed.page_key,
                        'why': 'recipe step of row %s (%s)' % (row.get('n'), row.get('pattern')),
                        'match_ms': match_ms, 'rows': len(parsed.rows), **out_extra}
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
