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


def _host_prefix(host: str, *xpaths) -> str | None:
    """The element path up to and INCLUDING its `<host>[n]` segment, or None when no such host is
    on the path. Two controls of the same kind on one page differ EARLIER than that segment
    (`omniscript-select[2]` vs `omniscript-select[5]`), so the prefix names the instance."""
    for xp in xpaths:
        s = str(xp or '')
        i = s.rfind('/' + host)
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
    return '%s#   backup: %s   (stock recorder line, unverified)' % (indent, (text or '').strip())


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
    backups = []
    if raw_open and open_line.strip() != raw_open:
        backups.append(_dormant(indent, raw_open))
    if open_line.strip():
        backups.append(_dormant(indent, open_line))
    if (stock_filter or '').strip():
        backups.append(_dormant(indent, stock_filter))
    if (stock_option or '').strip():
        backups.append(_dormant(indent, stock_option))
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


# ============================================================ generated data from a typed sentinel
# "Every value is hard-coded, so the second run fails on duplication rules." (user, 2026-09-19 --
# docs/PLAN-OFFLINE-REPLAY-2026-09-19.md, "Backlog: generated data from a typed sentinel").
#
# The typed value is the HOTKEY. A recorded fill whose value is a SENTINEL composes a VARIABLE line
# above the fill, set by the shipped `resources/garzai_data.robot` (stdlib only -- the CRT container
# has no faker), and the fill uses the variable -- so a later verify or cleanup line can reuse the
# same value, and every generated value carries the run stamp a teardown step deletes by.
#
# THE SENTINEL TABLE IS DELIBERATELY SMALL. Only `asdf` and the explicit `@@` grammar. `asdfasdf`,
# `test`, `qwer` are NOT sentinels: a person types those as real data, and a false positive would
# silently replace a value they meant with a generated one -- the same class of quiet wrong answer
# as `get_field_value("Stage") -> "Stage"`. A malformed `@@...` is not a sentinel either, but it is
# DISCLOSED in the `why` rather than passed through as if nobody had noticed.
#
# Click-recorded controls (a picklist option, a calendar day) cannot carry a typed sentinel, so they
# get two markers instead: an ALT-CLICK on the option or the day ("any valid value here"), and -- on
# every pick and every date, gesture or not -- a dormant `Comment    generate:` pair a person
# promotes by deleting two cells, exactly like a backup line.
SENTINEL_BARE = 'asdf'

# Values that LOOK like a sentinel and are NOT. Named so the table is a table, not a regex nobody
# can argue with; the test file asserts every one of them stays a literal.
SENTINEL_NEAR_MISSES = ('asdfasdf', 'test', 'qwer', 'asdfg', 'asd', 'aaaa', 'x', 'ASDF1')

# A picklist's option list is ELIDED on the composed line when it is long -- and the `why` always
# says how many were dropped and where the whole list lives (an instrument may elide; it may never
# elide SILENTLY -- CLAUDE.md, tools/guards/no_silent_truncation.py).
PICK_OPTION_CAP = 12


def sentinel_spec(value) -> tuple:
    """(kind, args, why) for a typed value that is a SENTINEL, or (None, None, why).

    kinds: `auto` (the bare `asdf`: the generator comes from the field's own type), `email`,
    `phone`, `unique`, `date`, `int`, `text`, `pick`.

    The grammar, in full -- there is nothing else:
        asdf                  (case-insensitive, surrounding whitespace ignored)
        @@email   @@phone   @@pick
        @@unique <base>       (bare `@@unique` takes the field's label as the base)
        @@date+N  @@date-N    (N days from today)
        @@int <min> <max>
        @@text <len>
    """
    v = re.sub(r'\s+', ' ', str(value if value is not None else '')).strip()
    if not v:
        return None, None, 'no value to read'
    if v.casefold() == SENTINEL_BARE:
        return 'auto', [], ("the bare sentinel %r: the generator is chosen by the field's own type"
                            % v)
    if not v.startswith('@@'):
        return None, None, 'not a sentinel: %r is a literal value' % v[:60]
    body = v[2:].strip()
    m = re.match(r'^(email|phone|pick)$', body, re.I)
    if m:
        return m.group(1).lower(), [], 'the explicit sentinel %r' % v
    m = re.match(r'^unique(?:\s+(.+))?$', body, re.I)
    if m:
        base = (m.group(1) or '').strip()
        return 'unique', [base], ('the explicit sentinel %r%s'
                                  % (v, '' if base else " (no base given: the field's label is used)"))
    m = re.match(r'^date\s*([+-])\s*(\d+)$', body, re.I)
    if m:
        return 'date', ['%s%s' % (m.group(1), m.group(2))], 'the explicit sentinel %r' % v
    m = re.match(r'^int\s+(-?\d+)\s+(-?\d+)$', body, re.I)
    if m:
        return 'int', [m.group(1), m.group(2)], 'the explicit sentinel %r' % v
    m = re.match(r'^text\s+(\d+)$', body, re.I)
    if m:
        return 'text', [m.group(1)], 'the explicit sentinel %r' % v
    return None, None, ('MALFORMED SENTINEL %r: it starts with @@ but matches no rule in the '
                        'grammar (@@email, @@phone, @@pick, @@unique <base>, @@date+N, @@date-N, '
                        '@@int <min> <max>, @@text <len>), so it is typed as the literal text it '
                        'is -- said out loud rather than silently generated' % v)


def sentinel_landed(value) -> bool:
    """True when a value READ BACK OFF THE PAGE is itself a sentinel -- the verdict
    `CAUGHT-BUG: sentinel landed`, never a quiet pass. Mirrored by `Gz Is Sentinel` in
    resources/garzai_data.robot, which is the copy that runs in the container."""
    kind, _args, _why = sentinel_spec(value)
    return kind is not None


# ------------------------------------------------------------------ metadata type -> generator
# The ORG MAP's field type is what routes the keyword (CLAUDE.md: "Metadata routes the keyword, DOM
# is the backstop"). Read off `<alias>.json` -> objects.<Obj>.inventory.fields.value.<f>.type, the
# same projection `skeleton.py <alias>:<Object>` prints. A type with no row here has NO generator
# and says so: a URL, a lookup reference, a checkbox and a base64 blob are not things a text
# generator can invent a correct value for, and inventing one is the quiet-wrong-answer failure.
SF_TYPE_GENERATOR = {
    'email':           ('Gz Email', []),
    'phone':           ('Gz Phone', []),
    'date':            ('Gz Date', ['+30']),
    'datetime':        ('Gz Date', ['+30']),
    'picklist':        ('Gz Pick', []),
    'multipicklist':   ('Gz Pick', []),
    'combobox':        ('Gz Pick', []),
    'int':             ('Gz Number', ['1', '100']),
    'double':          ('Gz Number', ['1', '1000']),
    'percent':         ('Gz Number', ['1', '100']),
    'currency':        ('Gz Number', ['1000', '99000']),
    'string':          ('Gz Unique Text', []),
    'textarea':        ('Gz Unique Text', []),
    'encryptedstring': ('Gz Unique Text', []),
}
SF_TYPE_NO_GENERATOR = {
    'url': 'a URL field: no generator invents a URL that resolves',
    'reference': 'a lookup: its value must name a record that EXISTS, which no generator knows',
    'boolean': 'a checkbox is clicked, never typed into',
    'address': 'a compound control (one DB value, several inputs) -- dedicated keywords, BACKLOG 80',
    'base64': 'a file blob, not a typed value',
    'id': 'a record id is not generated data',
    'time': 'NOT YET IMPLEMENTED: there is no Gz Time keyword in resources/garzai_data.robot',
    'anytype': 'the type is literally `anytype`: there is nothing to route on',
}

# The BACKSTOP, for a label the org map does not carry: the control's own input type, then its
# parser family. Always named in the `why`, so a reader can tell which door answered.
DOM_TYPE_GENERATOR = {
    'email': ('Gz Email', []),
    'tel': ('Gz Phone', []),
    'number': ('Gz Number', ['1', '100']),
    'date': ('Gz Date', ['+30']),
    'datetime-local': ('Gz Date', ['+30']),
    'text': ('Gz Unique Text', []),
    'search': ('Gz Unique Text', []),
}
# F146-2 (F146-1/-2): the describer's `familyOf()` (descriptor.py) NEVER returns 'picklist',
# 'combobox', 'date', 'datetime', 'number', 'email', 'textarea' or 'search' -- it collapses every
# <input> (including <textarea> and a `role=searchbox`) to 'input_field', and everything OmniStudio
# renders as a custom element falls to its own `return tag` fallback (the RAW tag name, e.g.
# `runtime_omnistudio_common-combobox`, never the word 'combobox'). Those eight rows were therefore
# dead on the live path -- a reachability audit (`test_probe1_CAUGHT_BUG_eight_of_nine_...`, now
# flipped to require it) greps this table's keys against `familyOf`'s own literal `return '...'`
# strings and the raw-tag families a live capture actually carries, and fails on any key neither
# names. Rather than guess at more literals `familyOf` might one day emit, the dead rows are
# DELETED: the receiving-keyword/host door (`generator_door`) and the DOM `type` attribute
# (`DOM_TYPE_GENERATOR`) already cover date/combobox/email/number, so nothing here regresses.
FAMILY_GENERATOR = {
    'input_field': ('Gz Unique Text', []),
}
FAMILY_NO_GENERATOR = {
    'checkbox': 'a checkbox is clicked, never typed into',
    'radio': 'a radio is clicked, never typed into',
}


def field_meta(label, fields) -> tuple:
    """(the org-map field entry, why) for a rendered LABEL, or (None, why).

    `fields` is the table `build_override.py --fields <alias>:<Object>` embeds: one entry per
    field, keyed by its rendered label AND by its API name, each carrying `type`, `object`,
    `name`, `length` and `picklist_values`. A label the table does not carry is a plain
    could-not-check -- the descriptor door answers instead, and the `why` says so."""
    if not fields:
        return None, 'no org-map field table was embedded in this build'
    lab = omni_label(label)
    if not lab:
        return None, 'the control has no label to look up'
    for key in (lab, lab.casefold()):
        hit = fields.get(key)
        if hit:
            return hit, 'org-map field %s.%s (type %r)' % (hit.get('object'), hit.get('name'),
                                                           hit.get('type'))
    return None, 'no org-map field is labelled %r in the embedded table' % lab


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
    """The disclosure a `datetime` field's metadata carries wherever `Gz Date` is chosen for it --
    F146-6 (F146-6): it used to appear only on the `asdf` (auto/metadata) path and vanish on the
    explicit `@@date+N` and receiving-keyword/host doors, which compose the byte-identical value
    with no sign only half the field is generated."""
    if meta and str(meta.get('type') or '').casefold() == 'datetime':
        return (' -- the DATE half only: the time half is not generated here (a datetime is a '
                'compound control; routing it is BACKLOG 80)')
    return ''


def generator_door(kind, receiving, lab, desc=None, options=None, meta=None) -> tuple:
    """(cells, why) when the RECEIVING KEYWORD or a descriptor HOST fact names the generator before
    metadata or the DOM type get a vote, or (None, None) to let the caller fall through to
    `generator_call`'s metadata / DOM-type / family ladder (F146-1, the root defect).

    `Omni Date` / `Omni Select` are OmniStudio's own compound keywords, and a date-picker or
    combobox HOST -- named by the element's own xpath, `_OMNI_DATE_PICKER` / `_OMNI_COMBOBOX` --
    answers even before the line has been routed to one of those keywords (the omniKey/host walk
    already knows the widget). Both outrank a bare `type="text"`, which Lightning and OmniStudio
    render for a date picker, a combobox and a lookup alike.

    `(None, None)` means neither the keyword nor the host has an opinion -- the caller falls
    through to metadata, then the DOM type, then the family. `(None, why)` means the door DOES
    apply but has nothing usable (e.g. `Omni Select` with no known options) -- that IS the answer,
    a disclosed COULD-NOT-CHECK, never a fallthrough to a worse guess."""
    if kind != 'auto':
        return None, None
    d = desc or {}
    blob = ' '.join(str(d.get(k) or '') for k in ('xpath', 'alt_xpath'))
    if receiving == 'Omni Date' or _OMNI_DATE_PICKER in blob:
        src = ("the receiving keyword 'Omni Date'" if receiving == 'Omni Date'
               else "the descriptor's own element path is inside a %r host" % _OMNI_DATE_PICKER)
        return ['Gz Date', '+30', '--iso'], '%s: names a date%s' % (src, _datetime_note(meta))
    if receiving == 'Omni Select' or _OMNI_COMBOBOX in blob:
        src = ("the receiving keyword 'Omni Select'" if receiving == 'Omni Select'
               else "the descriptor's own element path is inside a %r host" % _OMNI_COMBOBOX)
        cells, why = _pick_cells(lab, options or d.get('options'))
        return cells, '%s: names a pick -- %s' % (src, why)
    return None, None


def generator_call(kind, args, label, meta=None, desc=None, options=None, iso=False,
                   receiving='') -> tuple:
    """(the generator call as Robot CELLS, why) for one sentinel, or (None, why).

    `iso=True` asks `Gz Date` for `YYYY-MM-DD`, which is what `Omni Date` takes. `receiving` is the
    keyword that will actually run with this value (`Omni Date`, `Omni Select`, a plain `TypeText`,
    ...) -- see `generator_door`, which this consults FIRST, ahead of metadata."""
    lab = omni_label(label)
    args = list(args or [])
    # F146-7 (F146-7): the EXPLICIT `@@` grammar overriding the metadata type is deliberate and
    # tested (`@@text 40` in an email field) -- but it used to override `SF_TYPE_NO_GENERATOR` too,
    # the table whose entire purpose is to say a type has NO honest generator, silently: `@@unique`
    # in a lookup composed a run-stamped string with no sign the type had ever been consulted. The
    # override still wins (the person asked explicitly), but the refusal reason is now quoted.
    _override_note = ''
    if kind not in ('auto', None) and meta and meta.get('type'):
        _t = str(meta.get('type')).casefold()
        if _t in SF_TYPE_NO_GENERATOR:
            _override_note = ('; the metadata type %r has no generator -- %s -- overridden by the '
                              'explicit sentinel' % (_t, SF_TYPE_NO_GENERATOR[_t]))

    def _explicit(cells, why):
        return cells, why + _override_note

    if kind == 'email':
        return _explicit(['Gz Email'], 'the sentinel names the generator')
    if kind == 'phone':
        return _explicit(['Gz Phone'], 'the sentinel names the generator')
    if kind == 'unique':
        return _explicit(['Gz Unique Text', (args[0] if args and args[0] else lab) or 'GZ'],
                         'the sentinel names the generator')
    if kind == 'text':
        return _explicit(['Gz Text', args[0]], 'the sentinel names the generator')
    if kind == 'int':
        return _explicit(['Gz Number', args[0], args[1]], 'the sentinel names the generator')
    if kind == 'date':
        cells = ['Gz Date', args[0] if args else '+30'] + (['--iso'] if iso else [])
        return _explicit(cells, 'the sentinel names the generator' + _datetime_note(meta))
    if kind == 'pick':
        opts = options or (meta or {}).get('picklist_values')
        cells, why = _pick_cells(lab, opts)
        # F143-5b (F146-5): "no usable option is known" reads the same whether the listbox was
        # simply closed or the field is not a picklist AT ALL -- the org map already knows which,
        # and used to quote the type without ever joining the two facts.
        if not cells and meta and meta.get('type'):
            t = str(meta.get('type')).casefold()
            if t not in ('picklist', 'multipicklist', 'combobox'):
                why += ' -- %s.%s is type %r, not a picklist: no option was ever going to exist' \
                    % (meta.get('object'), meta.get('name'), t)
        return _explicit(cells, why)
    if kind != 'auto':
        return None, 'unknown sentinel kind %r' % kind

    # THE RECEIVING KEYWORD / HOST DOOR ANSWERS FIRST (F146-1), before metadata or the DOM type get
    # a vote: it is the one door a generic `type="text"` cannot fool.
    door_cells, door_why = generator_door(kind, receiving, lab, desc=desc, options=options, meta=meta)
    if door_why is not None:
        return door_cells, door_why

    # `asdf`: the METADATA type routes it, the descriptor is the backstop.
    if meta and meta.get('type'):
        t = str(meta.get('type')).casefold()
        if t in ('picklist', 'multipicklist', 'combobox'):
            cells, why = _pick_cells(lab, options or meta.get('picklist_values'))
            return cells, ('metadata type %r on %s.%s: %s'
                           % (t, meta.get('object'), meta.get('name'), why))
        if t in SF_TYPE_GENERATOR:
            kw, a = SF_TYPE_GENERATOR[t]
            cells = ['Gz Unique Text', lab or 'GZ'] if kw == 'Gz Unique Text' else [kw] + list(a)
            if kw == 'Gz Date' and iso:
                cells = cells + ['--iso']
            length_why = ''
            # F146-10: the org map's `length` sits on every embedded field entry and used to be
            # dropped on the floor -- a `string` field of length 10 composed the identical call as
            # one of length 80, so a short Salesforce text field truncates the value (and the run
            # stamp inside it) BY THE BROWSER, with no console line at all. `Gz Unique Text` takes
            # `max_length` as its own second argument; compose it whenever the map knows the length.
            if kw == 'Gz Unique Text' and meta.get('length'):
                try:
                    n = int(meta['length'])
                except (TypeError, ValueError):
                    n = 0
                if n > 0:
                    cells = cells + [str(n)]
                    length_why = ' (max_length %d from the org map)' % n
            why = 'metadata type %r on %s.%s%s' % (t, meta.get('object'), meta.get('name'), length_why)
            if t == 'datetime':
                why += (' -- the DATE half only: the time half is not generated here (a datetime '
                        'is a compound control; routing it is BACKLOG 80)')
            return cells, why
        return None, ('COULD-NOT-CHECK: metadata type %r on %s.%s has no generator -- %s'
                      % (t, meta.get('object'), meta.get('name'),
                         SF_TYPE_NO_GENERATOR.get(t, 'no rule in SF_TYPE_GENERATOR names it')))

    d = desc or {}
    fam = str(d.get('family') or '').casefold()
    if fam in FAMILY_NO_GENERATOR:
        return None, ('COULD-NOT-CHECK: no org-map field for %r, and the control\'s family %r has '
                      'no generator -- %s' % (lab, fam, FAMILY_NO_GENERATOR[fam]))
    etype = str(d.get('type') or d.get('etype') or '').casefold()
    if etype in DOM_TYPE_GENERATOR:
        kw, a = DOM_TYPE_GENERATOR[etype]
        cells = ['Gz Unique Text', lab or 'GZ'] if kw == 'Gz Unique Text' else [kw] + list(a)
        if kw == 'Gz Date' and iso:
            cells = cells + ['--iso']
        return cells, 'no org-map field for %r: the descriptor\'s input type %r' % (lab, etype)
    if fam in ('picklist', 'combobox'):
        cells, why = _pick_cells(lab, options)
        return cells, ('no org-map field for %r: the descriptor\'s family %r -- %s'
                       % (lab, fam, why))
    if fam in FAMILY_GENERATOR:
        kw, a = FAMILY_GENERATOR[fam]
        cells = ['Gz Unique Text', lab or 'GZ'] if kw == 'Gz Unique Text' else [kw] + list(a)
        if kw == 'Gz Date' and iso:
            cells = cells + ['--iso']
        return cells, 'no org-map field for %r: the descriptor\'s family %r' % (lab, fam)
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
    """`    ${lead_last_name}=    Gz Unique Text    Last Name`"""
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
                         taken=None, indent='    ', prefix=None) -> tuple:
    """(the variable line, the rewritten fill line, why) for a composed line whose VALUE is a
    SENTINEL, or ('', composed, why) when it is not one or no generator fits.

    This runs LAST, after the OmniStudio routing, so an `asdf` typed into an OmniStudio masked
    input becomes `Omni Type    <key>    ${phone_number}` and not a TypeText the widget ignores."""
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
    meta, meta_why = field_meta(lab, fields)
    # THE DATE FORMAT IS DECIDED BY THE KEYWORD THAT WILL RECEIVE IT, and by nothing else.
    # `Omni Date` documents `YYYY-MM-DD`, so it gets `--iso`. A plain `TypeText` into a rendered
    # date input gets `Gz Date`'s default `MM/DD/YYYY`, which is what a Salesforce date input
    # renders in a US locale -- and that is a DEFAULT, not a fact read from the org map: the map
    # carries field types, not the running user's locale, so a non-US org needs `--iso` or its own
    # format on the line. Said here rather than implied.
    receiving = cells0[0] if cells0 else ''
    iso = receiving == 'Omni Date'
    cells, gen_why = generator_call(kind, args, lab, meta=meta, desc=desc, options=options,
                                    iso=iso, receiving=receiving)
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


def date_offset_days(iso, today=None) -> tuple:
    """(the offset from TODAY in `+N`/`-N` form, why) for an ISO date, or (None, why).

    Computed at COMPOSE time, which is the only moment `today` and the picked day are both known:
    the pane then keeps the OFFSET, so the same recording picks a date the same distance away on
    every later run instead of one that has drifted into the past."""
    m = _ISO_RX.match(str(iso or ''))
    if not m:
        return None, 'not an ISO date: %r' % iso
    import datetime as _dt
    picked = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    base = today or _dt.date.today()
    n = (picked - base).days
    return ('%+d' % n), ('%s is %+d days from %s (computed at compose time)' % (iso, n, base))


def generated_date_lines(label, omni_key, iso, today=None, taken=None, indent='    ',
                         prefix=None) -> tuple:
    """(the variable line, the `Omni Date` line, the dormant literal backup, why) for an
    ALT-CLICKED calendar day, or ('', '', '', why)."""
    key = str(omni_key or '').strip()
    if not key:
        return '', '', '', 'the element carries no data-omni-key: Omni Date has nothing to resolve'
    off, why = date_offset_days(iso, today)
    if off is None:
        return '', '', '', why
    lab = omni_label(label) or key
    var = variable_name(lab, taken, prefix=prefix)
    literal = RT._rf('Omni Date', key, iso).strip()
    return (variable_line(var, ['Gz Date', off, '--iso'], indent),
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
