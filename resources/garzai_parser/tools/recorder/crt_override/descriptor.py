"""descriptor -- identity by what the page can SAY about the element it just recorded.

Usage (library):
    from descriptor import describe_js, RESOLVE_JS, NONCE_ATTR, find_row
    js   = describe_js(spec)          # the page-side `window.__gzDescribe`, spec = the template's
                                      # formElementLabel block (no fork: the data comes from there)
    el   = drv.execute_script(RESOLVE_JS, nonce)     # the stamped element, open shadow roots too
    row, why = find_row(rows, descriptor)            # which reviewed/parsed row it is

Why this module exists (2026-09-18, ledger F40/F42/F44):

  * F44 -- the composer matched a recorded element to a review row by an identity XPATH that is
    POSITIONAL over the whole page: `(//input[@type="text"])[3]`. One extra text input in the DOM
    (an App Launcher search box left after use, an Add Line row) shifts every index, so none of the
    seven Nightmare inputs matched its row and both Save clicks missed row 67.
  * F42 -- the same positional xpaths resolve to exactly ONE element on ANY page, so on a Lead form
    `Last Name` matched the Zoo page's `Renewal Notice (days)` with a confident backup line.
  * F40 -- Lightning Setup controls sit in native shadow roots; xpath from the driver reaches none
    of them, so no identity of any kind could be established and no proposal was possible.

So identity stops being an xpath the composer re-evaluates. The page stamps the element it recorded
with a one-shot attribute (`data-gz-ev="<nonce>"`, removed after 10 s) and sends a DESCRIPTOR of it.
The composer finds the element by the nonce with ONE shadow-piercing walk -- never by xpath -- and
names the row by LABEL + FAMILY, which is what a person reads and what neither an extra input nor a
different page can quietly change.

The match rule is `tools/recorder/pom/match.py` -- the ONE rule for "does the store already know
this control?" -- applied to a list of rows instead of a POM record: the same label normalisation
(whitespace collapsed, case folded, a trailing live count dropped, a prefix NEVER a match) and the
same family compatibility (button/link/menuitem/tab are one click family; input/textarea/combobox
one type family). It is imported when the POM package is importable and reproduced here when it is
not (the generated CRT library ships alone, without the parser bundle); `test_descriptor_match.py`
fails if the two ever disagree.

Nothing here decides a LINE. It answers which row, and says how it knows -- `label`, `attribute` or
`positional` -- so a decision can be read and argued with.
"""
from __future__ import annotations

import json
import re

NONCE_ATTR = 'data-gz-ev'
NONCE_TTL_MS = 10000

# ----------------------------------------------------------------------------- the match rule
try:                                                     # the ONE rule, when it can be imported
    from pom.match import norm_label, families_compatible, CLICK_FAMILIES, TYPE_FAMILIES
except Exception:                                        # ... and its stated twin when it cannot
    CLICK_FAMILIES = {'button', 'link', 'menuitem', 'tab', 'click', 'a'}
    TYPE_FAMILIES = {'input', 'input_field', 'textarea', 'combobox', 'text', 'type', 'search'}
    _COUNT_SUFFIX = re.compile(r'\s*\(\d+\)\s*$')

    def norm_label(s):
        s = re.sub(r'\s+', ' ', (s or '')).strip().strip('*').strip()
        s = _COUNT_SUFFIX.sub('', s)
        return s.casefold()

    def families_compatible(want, have):
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


_COUNT_SUFFIX_RX = re.compile(r'\s*\(\d+\)\s*$')


def norm_label_exact(s) -> str:
    """`norm_label` WITHOUT the trailing-count strip.

    The two differ only for a label that ENDS in `(n)`, and that difference is a measured wrong
    answer: a control the page calls `Amount (2)` matched a row called `Amount` and was reported as
    a plain label match (challenge D10 finding 10, 2026-09-19). The strip exists for live counts on
    related-list buttons (`Dependency Analysis (2)`), so it stays -- but a match that NEEDED it is
    said out loud in the `why`, never passed off as an exact agreement."""
    return re.sub(r'\s+', ' ', (s or '')).strip().strip('*').strip().casefold()


# D5 -- "this value changes per render", the ONE judgement, never a second opinion.
# `review_table.is_generated` reads the TEMPLATE's own `dynamicValuePatterns`; it is imported when
# the parser is importable, and when it is not (the generated CRT library ships alone inside a CRT
# container) the generator hands the SAME template block to `set_generated_rules` at import time.
# The literals below are only the floor for a library built before either of those existed.
try:
    from review_table import is_generated as _rt_is_generated
except Exception:
    _rt_is_generated = None

_GEN_PREFIXES = ('j_id', 'temp-', 'input-', 'lgt-', 'vfFrameId_')
_GEN_PATTERNS = [re.compile(p) for p in (
    r'^\d+:\d+;[a-z]$',                  # aria-controls="119:639;a"
    r'(^|:)j_id\d+(:|$)',                 # a Visualforce view-state id
    r'^[a-z][a-z0-9]*(-[a-z0-9]+)*-\d+$',  # lgt-datatable-1-options-1, input-123
    r'^[0-9a-f]{32}$',                    # a 32-hex token
    r'^[0-9a-f]{8}-[0-9a-f]{4}-',         # a uuid
    r'^[A-Za-z][A-Za-z0-9]*_\d{10,}$',    # vfFrameId_1788626362477
)]


def set_generated_rules(prefixes, patterns) -> int:
    """Adopt the TEMPLATE's own dynamicValuePatterns (the generated library calls this once).

    Returns how many patterns were adopted; anything unreadable leaves the floor in place, because
    a rule that cannot be read is not a reason to stop refusing generated values."""
    global _GEN_PREFIXES, _GEN_PATTERNS
    try:
        pats = [re.compile(p) for p in (patterns or [])]
    except Exception:
        return 0
    if not pats:
        return 0
    _GEN_PREFIXES = tuple(prefixes or ())
    _GEN_PATTERNS = pats
    return len(pats)


def is_generated(value) -> bool:
    """True when this attribute VALUE changes per render, so it can never be an identity (D5)."""
    if _rt_is_generated is not None:
        return bool(_rt_is_generated(value))
    v = str(value or '')
    if not v:
        return False
    if any(v.startswith(pre) for pre in _GEN_PREFIXES):
        return True
    return any(rx.search(v) for rx in _GEN_PATTERNS)


# The rungs a descriptor offers as "the label a person reads", in order. The first four are the
# locator doctrine's own order (visible text, aria-label, title only for icon-only controls); the
# association comes first because a form control's own text is empty.
LABEL_RUNGS = ('label', 'text', 'aria_label', 'title', 'placeholder')


def label_candidates(desc: dict) -> list:
    """[(text, rung)] for this descriptor, best first. `title` and `placeholder` are last: the
    locator doctrine allows a tooltip only for an icon-only control with no visible text."""
    out = []
    for rung in LABEL_RUNGS:
        v = (desc or {}).get(rung)
        if v and str(v).strip():
            out.append((str(v).strip(), rung))
    return out


def _default_get(row: dict) -> tuple:
    """(label, family, index, group_size) for a row of the GENERATED library's embedded table."""
    return (row.get('label'), row.get('type'), row.get('index'), row.get('group_size'))


def parsed_get(row: dict) -> tuple:
    """(label, family, index, group_size) for a row of `review_table.build_rows`."""
    return (row.get('label_corrected') or row.get('label'),
            row.get('family_corrected') or row.get('element_type'),
            row.get('index_corrected') if 'index_corrected' in row else row.get('index'),
            row.get('group_size'))


# ----------------------------------------------------------------------------- the class rule
# `families_compatible` folds button / link / menuitem / tab / option into ONE click family, which
# is right for "can this row be clicked" and wrong for "is this the SAME control". Measured
# 2026-09-19 on fsc7f: the user picked `Home` in the OmniScript's Phone Type combobox (an `li`
# option, descriptor family `button`) and the descriptor branch claimed parser row 11 -- the app
# navigation's `Home` link (family `link`, tag `a`, region `chrome`; measured on the committed
# capture docs/dom-captures/fsc7f-omnistudio/01-applicationform-record-omniscript.html, row 11,
# group_size 2) -- so a correct stock line `ClickText    Home` was DEGRADED into
# `ClickText    Home    anchor=1    partial_match=False`, which at run time clicks the nav link and
# leaves the form untouched. The F42 class (a confident wrong answer) arriving through the label door.
#
# So a label match must also agree on the CONTROL CLASS, one step finer than the family: an option
# in a listbox is never a tab and never a navigation link.
_OPTION_ROLES = {'option', 'treeitem'}
_OPTION_TAGS = {'li', 'option'}
_NAV_ROLES = {'tab', 'menuitem', 'link', 'treeitem'}


def control_class(tag, role, family=None) -> str:
    """`option` / `nav` / `button` / `other` -- one step finer than the family, from whatever the
    side in hand can say. `other` is the unknown and agrees with everything."""
    t, r = str(tag or '').casefold(), str(role or '').casefold()
    f = str(family or '').casefold()
    if r in _OPTION_ROLES or t in _OPTION_TAGS:
        return 'option'
    if r in _NAV_ROLES or t == 'a' or f in ('link', 'tab', 'menuitem'):
        return 'nav'
    if t in ('button', 'input') or f == 'button':
        return 'button'
    return 'other'


def classes_agree(a: str, b: str) -> bool:
    """Two control classes name the same kind of control. `other` agrees with everything;
    `option` agrees only with `option`."""
    if a == 'other' or b == 'other':
        return True
    return a == b


def row_class(row: dict) -> str:
    attrs = (row.get('attrs') or {}) if isinstance(row, dict) else {}
    return control_class(row.get('tag_corrected') or row.get('tag'), attrs.get('role'),
                         row.get('family_corrected') or row.get('element_type') or row.get('type'))


def desc_class(desc: dict) -> str:
    return control_class(desc.get('tag'), desc.get('role'), desc.get('family'))


# The app chrome is the nav bar, the global header, the utility bar and the search box -- the
# parser already says so per row (`region`, from the template's own `chromeContainers`). A chrome
# row may only answer for an element that is ITSELF in the chrome, and the element's own path is
# the evidence: when the descriptor carries no path the rule does not fire, because an unknown is
# COULD-NOT-CHECK, never a refusal.
_CHROME_PATH_FRAGMENTS = ('one-appnav', 'one-app-nav-bar', 'onesearch', 'one-search',
                          'oneutilitybar', 'one-utility', 'globalheader', 'global-header',
                          'navigationmenuitem', 'one-tab-bar')


def _in_chrome_path(path: str) -> bool:
    p = str(path or '').casefold()
    return any(frag in p for frag in _CHROME_PATH_FRAGMENTS)


def row_may_claim(row: dict, desc: dict):
    """(True, None) when this row may answer for this descriptor's element, or (False, why not).

    Two refusals, both measured (fsc7f 2026-09-19, ledger F42's class):
      * the control classes disagree -- a listbox option is not a tab and not a nav link;
      * the row lives in the app chrome while the element's own path does not.
    """
    rc, dc = row_class(row), desc_class(desc)
    if not classes_agree(rc, dc):
        return False, 'the row is a %s and the element is a %s' % (rc, dc)
    path = desc.get('xpath') or desc.get('alt_xpath') or ''
    if str(row.get('region') or '').casefold() == 'chrome' and path and not _in_chrome_path(path):
        return False, 'the row is in the app chrome and the element is not (...%s)' % str(path)[-50:]
    return True, None


def find_row(rows, desc: dict, get=_default_get):
    """(row, why) -- the row this descriptor names, by label + family, or (None, why not).

    A label that occurs once names its row outright. A label that repeats is settled by the
    descriptor's `label_index`: the element's 1-based position among the same-label, family-
    compatible controls in DOM order, counted BY THE PAGE, against the row's own `index` (the
    parser's position among the same-label matches). When the two disagree, or the page could not
    count, nothing is returned -- an ambiguous label is a COULD-NOT-DISAMBIGUATE, never a guess.

    A same-label row must ALSO pass `row_may_claim`: the control classes have to agree (a listbox
    option is not a tab and not a navigation link) and a row in the app chrome may not answer for
    an element outside it. Refusing leaves (None, why), which is the caller's signal to let the
    STOCK recorder line stand unchanged -- a plain `ClickText    Home` is a better answer than a
    confident wrong one (fsc7f 2026-09-19, ledger F42's class).
    """
    if not rows or not desc:
        return None, 'no descriptor'
    fam = desc.get('family')
    tried, refused = [], []
    for text, rung in label_candidates(desc):
        want = norm_label(text)
        if not want:
            continue
        cands = [r for r in rows
                 if norm_label(get(r)[0]) == want and families_compatible(fam, get(r)[1])]
        # ... and the class rule, one step finer than the family (F42's class, 2026-09-19)
        kept, refused_here = [], []
        for r in cands:
            ok, why_not = row_may_claim(r, desc)
            if ok:
                kept.append(r)
            else:
                refused_here.append(why_not)
        refused.extend(refused_here)
        cands = kept
        tried.append('%s=%r -> %d%s' % (rung, text[:40], len(cands),
                                        (' (%d refused: %s)' % (len(refused_here), refused_here[0]))
                                        if refused_here else ''))
        if not cands:
            continue

        def _rung(row, _rung_name=rung, _text=text):
            """The rung name, marked when the trailing-count strip is what made it agree."""
            if norm_label_exact(get(row)[0]) == norm_label_exact(_text):
                return _rung_name
            return '%s, count-normalised' % _rung_name

        if len(cands) == 1:
            return cands[0], 'label (%s) %r' % (_rung(cands[0]), text[:40])
        idx = desc.get('label_index')
        if idx:
            hits = [r for r in cands if (get(r)[2] or 1) == idx]
            if len(hits) == 1:
                return hits[0], 'label (%s) %r + page index %d of %s' % (
                    _rung(hits[0]), text[:40], idx, desc.get('label_group_size'))
        return None, ('COULD-NOT-DISAMBIGUATE: %d rows carry label %r and the page counted index %r'
                      % (len(cands), text[:40], idx))
    why = 'no row carries this descriptor label (%s)' % ('; '.join(tried) or 'none offered')
    if refused:
        # SAY WHY IT WAS REFUSED. A silent refusal reads exactly like "the page has no such row",
        # and the difference is the whole of F42: one is a control we could not name, the other is
        # a control we deliberately declined to mis-name.
        why += '; refused %d same-label row(s): %s' % (len(refused), '; '.join(refused[:3]))
    return None, why


def attribute_identity(desc, row, refused=None):
    """The stable attribute this descriptor and this row AGREE on, or None.

    NEVER a generated value, and that is now ENFORCED here rather than delegated. The docstring
    used to promise it and the function checked nothing: it trusted whatever the row carried, so a
    per-render `id="input-123"` or `name="j_id0:form:x"` that agreed on both sides became a
    confident `attribute` identity -- D5's forbidden locator as an identity (challenge D10
    finding 12, 2026-09-19). `is_generated` is now called on BOTH sides and a flagged pair is
    skipped.

    `refused` -- an optional list; the stated reason for each skipped pair is appended to it, so a
    caller can put "it agreed on a generated value" in its decision rather than reporting a silent
    miss."""
    attrs = (row.get('attrs') or {}) if isinstance(row, dict) else {}
    for key, dkey in (('name', 'name'), ('aria-label', 'aria_label'), ('data-testid', 'data_testid'),
                      ('title', 'title'), ('placeholder', 'placeholder'), ('id', 'id')):
        want, have = desc.get(dkey), attrs.get(key)
        if want and have and str(want) == str(have):
            if is_generated(str(want)) or is_generated(str(have)):
                if refused is not None:
                    refused.append("@%s=%r is a GENERATED value (changes per render): "
                                   "not an identity" % (key, want))
                continue
            return '@%s=%r' % (key, want)
    return None


# ----------------------------------------------------------------------------- the page side
RESOLVE_JS = """
var want = arguments[0];
function walk(root){
  var el = null;
  try { el = root.querySelector('[%s="' + want + '"]'); } catch (e) { el = null; }
  if (el) { return el; }
  var all = root.querySelectorAll('*');
  for (var i = 0; i < all.length; i++) {
    var sr = all[i].shadowRoot;
    if (sr) { var r = walk(sr); if (r) { return r; } }
  }
  return null;
}
return walk(document);
""" % NONCE_ATTR

# The page-side describer. `__GZ_FE_SPEC__` is the template's own `formElementLabel` block
# (docs/recorder/templates/*.json): the SLDS shape whose label is a cousin of its control, which is
# every labelled control on Zoo_Nightmare_Inputs and most of a Lightning record page. It is injected
# by the generator, never restated here -- a fork of the parser's label rungs is exactly what this
# module must not become.
DESCRIBE_JS_TEMPLATE = r"""
;(function(){
var FE = __GZ_FE_SPEC__;
var SCAN_SELECTOR = 'input,select,textarea,button,a,[role],[contenteditable="true"]';
var SCAN_CAP = 1200;
function cls(el){ try { return (el.getAttribute && el.getAttribute('class')) || ''; } catch(e){ return ''; } }
function hasFrag(el, frags){ var c = cls(el); for (var i=0;i<(frags||[]).length;i++){ if (c.indexOf(frags[i])>=0) return true; } return false; }
function isFormElement(el){ var c = cls(el); if (c.indexOf(FE.containerClassFragment)<0) return false;
  var ex = FE.excludeContainerClassFragments||[]; for (var i=0;i<ex.length;i++){ if (c.indexOf(ex[i])>=0) return false; } return true; }
function txt(el){ var t=''; try { t = el.innerText || el.textContent || ''; } catch(e){} return t.replace(/\s+/g,' ').trim(); }
/* Is this element actually RENDERED? The describer used to read `innerText || textContent` off any
   element a label rung pointed at, so a `display:none` <span> named by aria-labelledby still yielded
   its text -- while the serializer that takes OUR capture drops display:none subtrees, so the parser
   never saw that label and the row was unlabelled. The two halves read the same page and disagreed
   about what is on it (challenge D10 finding 11, 2026-09-19). offsetParent alone is not enough: it
   is null for a position:fixed element that IS on screen, hence the client-rect fallback. When the
   question cannot be asked at all the answer is YES -- a describer must not silently drop a label
   because a browser threw. */
function shown(el){ try { if (!el) return false; if (el.offsetParent !== null) return true; var r = el.getClientRects ? el.getClientRects() : null; if (r && r.length) return true; var d = el.ownerDocument; if (!d || !d.defaultView || !d.defaultView.getComputedStyle) return true; var cs = d.defaultView.getComputedStyle(el); if (!cs) return true; return !(cs.display === 'none' || cs.visibility === 'hidden'); } catch(e){ return true; } }
function vtxt(el){ return shown(el) ? txt(el) : ''; }
function up(el){ if (!el) return null; if (el.parentElement) return el.parentElement;
  var p = el.parentNode; return (p && p.host) ? p.host : null; }
function esc(s){ try { return (window.CSS && CSS.escape) ? CSS.escape(String(s)) : String(s).replace(/["\\]/g,'\\$&'); } catch(e){ return String(s); } }
function attr(el,k){ try { var v = el.getAttribute(k); return (v===null||v==='') ? null : v; } catch(e){ return null; } }
function formElementLabel(el){
  var tags = FE.targetTags || [], tag = el.tagName.toLowerCase();
  if (tags.length && tags.indexOf(tag) < 0){
    var wrapper = FE.wrapperMayBeTarget && tag.indexOf('-')>0 &&
                  el.querySelectorAll('input,select,textarea').length === 1;
    if (!wrapper) return '';
  }
  var p = up(el), hops = 0;
  while (p && hops < 4){ if (hasFrag(p, FE.targetInsideExcludedClassFragments)) return ''; p = up(p); hops++; }
  var cur = up(el), h = 0, max = FE.maxClimb || 8;
  while (cur && h < max){
    if (isFormElement(cur)){
      var all = cur.querySelectorAll('*');
      for (var i=0;i<all.length;i++){
        var c = all[i], toks = cls(c).split(/\s+/), hit = false, frs = FE.labelClassFragments || [];
        for (var j=0;j<frs.length;j++){ if (toks.indexOf(frs[j])>=0){ hit = true; break; } }
        if (hit && c !== el && !c.contains(el)){ var t = vtxt(c); if (t) return t; }
      }
    }
    cur = up(cur); h++;
  }
  return '';
}
function nearestLabel(el){
  var root = el.getRootNode ? el.getRootNode() : document;
  try { var id = attr(el,'id');
        if (id){ var l = root.querySelector('label[for="'+esc(id)+'"]'); if (l){ var t=vtxt(l); if (t) return [t,'label_for']; } } } catch(e){}
  try { var lb = attr(el,'aria-labelledby');
        if (lb){ var parts = lb.split(/\s+/), out = [];
          for (var i=0;i<parts.length;i++){ var n = null;
            try { n = root.getElementById ? root.getElementById(parts[i]) : root.querySelector('#'+esc(parts[i])); } catch(e){}
            if (n) out.push(vtxt(n)); }
          var t2 = out.join(' ').trim(); if (t2) return [t2,'aria_labelledby']; } } catch(e){}
  try { var a = el.closest ? el.closest('label') : null; if (a){ var t3 = vtxt(a); if (t3) return [t3,'wrapping_label']; } } catch(e){}
  var fe = formElementLabel(el); if (fe) return [fe,'form_element_label'];
  try { var s = el.previousElementSibling, g = 0;
        while (s && g < 3){ if (s.tagName === 'LABEL' || hasFrag(s, FE.labelClassFragments)){ var t4 = vtxt(s); if (t4) return [t4,'sibling_label']; } s = s.previousElementSibling; g++; } } catch(e){}
  return ['', null];
}
function familyOf(el){
  var tag = el.tagName.toLowerCase(), ty = (attr(el,'type')||'').toLowerCase(), role = (attr(el,'role')||'').toLowerCase();
  if (tag === 'select') return 'dropdown';
  if (tag === 'textarea') return 'input_field';
  if (tag === 'input'){ if (ty === 'checkbox') return 'checkbox'; if (ty === 'radio') return 'radio';
                        if (ty === 'button' || ty === 'submit' || ty === 'reset') return 'button'; return 'input_field'; }
  if (tag === 'button' || tag === 'a') return 'button';
  if (role === 'button' || role === 'tab' || role === 'menuitem' || role === 'option' || role === 'link') return 'button';
  if (role === 'combobox' || role === 'textbox' || role === 'searchbox') return 'input_field';
  if (role === 'checkbox' || role === 'switch') return 'checkbox';
  return tag;
}
var CLICKF = {button:1, link:1, menuitem:1, tab:1, click:1, a:1};
var TYPEF  = {input:1, input_field:1, textarea:1, combobox:1, text:1, type:1, search:1};
function compat(a,b){ if (!a || !b) return true; if (a === b) return true;
  if (CLICKF[a] && CLICKF[b]) return true; if (TYPEF[a] && TYPEF[b]) return true; return false; }
function norm(s){ return String(s||'').replace(/\s+/g,' ').trim().replace(/^\*|\*$/g,'').trim().replace(/\s*\(\d+\)\s*$/,'').toLowerCase(); }
function controls(){
  /* ONE depth-first walk, shadow content inlined right after its host, so the list is in the page's
     own reading order -- the order the parser sees in a capture (shadow roots serialise in place as
     <template>). Collecting a root's own matches first and descending afterwards counted a control
     at shadow depth 2 before one at depth 1 and the index disagreed with the review's. */
  var out = [], capped = false;
  function walk(root){
    if (capped) return;
    var all; try { all = root.querySelectorAll('*'); } catch(e){ all = []; }
    for (var i=0;i<all.length;i++){
      var e = all[i], hit = false;
      try { hit = e.matches && e.matches(SCAN_SELECTOR); } catch(err){ hit = false; }
      if (hit){ out.push(e); if (out.length >= SCAN_CAP){ capped = true; return; } }
      if (e.shadowRoot){ walk(e.shadowRoot); if (capped) return; }
    }
  }
  walk(document);
  return {list: out, capped: capped};
}
function labelIndex(el, label, fam){
  if (!label) return null;
  var want = norm(label), c = controls(), k = 0, found = null;
  for (var i=0;i<c.list.length;i++){
    var e = c.list[i];
    if (!compat(fam, familyOf(e))) continue;
    var L = nearestLabel(e)[0] || txt(e).slice(0,80);
    if (norm(L) !== want) continue;
    k++;
    if (e === el) found = k;
  }
  return {index: found, group_size: k, scanned: c.list.length, capped: c.capped};
}
/* The OmniStudio element's own metadata id. `data-omni-key` equals `OmniProcessElement.Name`. This
   walks UP -- through shadow hosts, via the same `up()` every label rung uses. It is what
   `keywords_omni.__host` resolves, which makes it the first argument of `Omni Type` / `Omni Date`;
   without it the composer leaves the stock TypeText line alone (measured 2026-09-19: TypeText's
   clear does not clear an OmniScript text input and the value APPENDS, so the keyword choice is not
   cosmetic).

   WHERE THE KEY ACTUALLY SITS, measured on the committed fsc7f captures (2026-09-19, build n2):
   in an OmniScript the attribute is on the `runtime_omnistudio_omniscript-omniscript-<type>`
   ELEMENT host -- every one of the 14 `data-omni-key` occurrences in
   docs/dom-captures/fsc7f-omnistudio/03-applicationform-omniscript-postintake.html is on such a
   host (`-omniscript-step`, `-omniscript-ip-action`, `-omniscript-text-block`, ...), NOT on the
   `runtime_omnistudio_common-*` control one level below it.

   WHY THE DATE PICKER MISSED IT (build n, run 5: `omniKey` returned null for Date of Birth and the
   fill fell back to the stock TypeText). It was the HOP CAP, not a missing attribute. The date
   input sits EIGHT div levels inside `runtime_omnistudio_common-date-picker`'s shadow root -- the
   live recording's own path tail is `.../-date-picker[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]
   /div[2]/input[1]`, and 02-home-flexcard-loancalculator.html shows the same nesting. So the input
   is 9 hops below the date-picker host, 10 below `runtime_omnistudio_common-input` and ~11 below
   the omniscript element that carries the key; the old `h < 8` cap stopped three hops short and
   returned null silently. The cap is raised to the measured depth plus headroom, and the walk stops
   AT the omniscript element boundary -- if that host has no key, there is none to find and climbing
   into the container would return a neighbouring element's key, which is worse than none. */
   TWO boundaries, because not every `data-omni-key` names a CONTROL. A container carries one too
   (`-omniscript-step` is keyed `ApplicationSummary`; `runtime_omnistudio-flexcard` is keyed
   `ApplicationSummaryFC`, both measured in capture 03), and handing a container's key to
   `Omni Type` would drive whatever input that container happens to hold first -- the six-times bug
   in a new costume. So a CONTAINER stops the walk WITHOUT reading, and only the OmniScript ELEMENT
   host stops it after reading. Reaching either with nothing is null, which the composer already
   says out loud and answers with the stock TypeText line. */
var OMNI_KEY_MAX_HOPS = 20;
var OMNI_KEY_CONTAINER_RX = /^(runtime_omnistudio-(flexcard|omniscript|generated-omniscript)|runtime_omnistudio_flexcards-|runtime_omnistudio_omniscript-omniscript-(container|step)$)/;
var OMNI_KEY_ELEMENT_RX = /^runtime_omnistudio_omniscript-omniscript-/;
function omniKey(el){ var cur = el, h = 0;
  while (cur && h < OMNI_KEY_MAX_HOPS){
    var t = cur.tagName ? cur.tagName.toLowerCase() : '';
    if (OMNI_KEY_CONTAINER_RX.test(t)) return null;   /* its key names the container, not this control */
    var k = attr(cur,'data-omni-key'); if (k) return k;
    if (OMNI_KEY_ELEMENT_RX.test(t)) return null;     /* the element host itself, keyless */
    cur = up(cur); h++; }
  return null; }
function hostChain(el){
  var out = [], r = el.getRootNode ? el.getRootNode() : document, g = 0;
  while (r && r !== document && r.host && g < 12){ out.push(r.host.tagName.toLowerCase()); r = r.host.getRootNode ? r.host.getRootNode() : document; g++; }
  return out;
}
window.__gzDescribe = function(el){
  var d = {};
  try {
    d.tag = el.tagName.toLowerCase();
    d.type = attr(el,'type');
    d.name = attr(el,'name');
    d.id = attr(el,'id');              /* raw: the composer only uses it when the ROW carries the
                                          same value, and the parser strips generated ones (D5) */
    d.aria_label = attr(el,'aria-label');
    d.placeholder = attr(el,'placeholder');
    d.title = attr(el,'title');
    d.role = attr(el,'role');
    d.data_testid = attr(el,'data-testid') || attr(el,'data-test-id');
    d.omni_key = omniKey(el);          /* OmniProcessElement.Name, off the element HOST */
    d.text = txt(el).slice(0,80);
    var nl = nearestLabel(el);
    d.label = nl[0] || null;
    d.label_source = nl[1];
    d.family = familyOf(el);
    var root = el.getRootNode ? el.getRootNode() : document;
    d.in_shadow = !!(root && root !== document && root.host);
    d.host_chain = hostChain(el);
    var li = labelIndex(el, d.label || d.text, d.family);
    d.label_index = li ? li.index : null;
    d.label_group_size = li ? li.group_size : null;
    d.scan_capped = li ? li.capped : null;
  } catch (e) { d.error = String(e); }
  return d;
};
var NONCE_N = 0;
window.__gzStamp = function(el){
  try {
    var n = 'gz' + (++NONCE_N) + '-' + Date.now().toString(36);
    el.setAttribute('%(attr)s', n);
    setTimeout(function(){ try { if (el.getAttribute('%(attr)s') === n) el.removeAttribute('%(attr)s'); } catch(e){} }, %(ttl)d);
    return n;
  } catch (e) { return null; }
};
})();
""" % {'attr': NONCE_ATTR, 'ttl': NONCE_TTL_MS}


def describe_js(fe_spec: dict) -> str:
    """The page-side describer with the template's formElementLabel block injected."""
    return DESCRIBE_JS_TEMPLATE.replace('__GZ_FE_SPEC__', json.dumps(fe_spec or {}))
